import os
from google import genai as google_genai
from google.genai import types
import config

_client = google_genai.Client(api_key=config.GEMINI_API_KEY)

IMAGE_MODEL = "gemini-3.1-flash-image"


def generate_image(prompt: str, chat_id: int) -> str | None:
    """Генерирует картинку по тексту через Gemini image-модель. Возвращает путь к файлу."""
    try:
        resp = _client.models.generate_content(
            model=IMAGE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )

        for part in resp.parts:
            if part.inline_data:
                os.makedirs(config.TMP_DIR, exist_ok=True)
                path = os.path.join(config.TMP_DIR, f"img_{chat_id}.png")
                with open(path, "wb") as f:
                    f.write(part.inline_data.data)
                return path
        return None
    except Exception as e:
        print(f"Image generation failed: {e}")
        return None
