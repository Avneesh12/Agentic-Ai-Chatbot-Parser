from groq import AsyncGroq
import json

client = AsyncGroq()

PARSE_PROMPT = """
You are a document parser. Extract structured data from the OCR text below.

Identify the document type and extract all relevant fields.

Document types and their fields:
- sales_invoice: invoice_number, date, due_date, seller (name, address, gstin), 
  buyer (name, address, gstin), line_items (description, qty, unit_price, tax, total),
  subtotal, tax_total, grand_total, currency, payment_terms, notes
  
- purchase_invoice: same as sales_invoice but with vendor info
  
- receipt: receipt_number, date, merchant (name, address), 
  items (description, qty, price), subtotal, tax, total, payment_method
  
- bank_statement: account_number, bank_name, period (from, to),
  transactions (date, description, debit, credit, balance), opening_balance, closing_balance
  
- other: extract whatever structured fields you can find

Rules:
- Return ONLY valid JSON, no markdown, no explanation
- Use null for missing fields
- Amounts should be numbers (not strings)
- Dates in YYYY-MM-DD format if possible

OCR Text:
{text}

Return JSON:
{{
  "document_type": "sales_invoice | purchase_invoice | receipt | bank_statement | other",
  "confidence": 0.0-1.0,
  "data": {{ ...extracted fields... }}
}}
"""


async def parse_document(ocr_text: str) -> dict:
    """
    Uses Groq LLM to parse OCR text into structured JSON.
    """
    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": PARSE_PROMPT.format(text=ocr_text[:8000])  # stay within context
            }
        ],
        temperature=0.1,  # low temp for structured extraction
        max_tokens=2000,
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "document_type": "other",
            "confidence": 0.0,
            "data": {},
            "raw_response": raw,
            "error": "Failed to parse LLM response as JSON"
        }