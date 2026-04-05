import requests
from app.core.config import settings

MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # ✅ Reliable free model
API_URL = f"https://router.huggingface.co/hf-inference/models/{MODEL}/pipeline/feature-extraction"


def embed_text(texts):
    headers = {
        "Authorization": f"Bearer {settings.HF_API_KEY}",
        "Content-Type": "application/json"
    }

    vectors = []

    for text in texts:
        try:
            response = requests.post(
                API_URL,
                headers=headers,
                json={
                    "inputs": [text],  # ✅ Must be a list
                    "options": {"wait_for_model": True}
                },
                timeout=30
            )

            # Check HTTP status before parsing
            if response.status_code != 200:
                raise Exception(
                    f"HF API returned status {response.status_code}: {response.text}"
                )

            # Guard against empty response body
            if not response.text.strip():
                raise Exception("HF API returned an empty response")

            data = response.json()

            if isinstance(data, dict) and "error" in data:
                raise Exception(f"HF API error: {data['error']}")

            # Flatten if nested: [[...]] → [...]
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                data = data[0]

            vectors.append(data)

        except requests.exceptions.Timeout:
            raise Exception(f"HF API timed out for: '{text[:50]}'")

        except requests.exceptions.ConnectionError:
            raise Exception("Could not connect to HF API. Check your internet.")

        except requests.exceptions.JSONDecodeError:
            raise Exception(
                f"Non-JSON response. Status: {response.status_code}, Body: '{response.text[:200]}'"
            )

    return vectors