import os
import google.generativeai as genai
import config

genai.configure(api_key=config.GEMINI_API_KEY)


def generate_image(prompt: str, chat_id: int) -> str | None:
    """Генерирует картинку по тексту через Gemini image-модель. Возвращает путь к файлу."""
    try:
        model = genai.GenerativeModel("gemini-3.1-flash-image")
        resp = model.generate_content(prompt)

        for part in resp.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                os.makedirs(config.TMP_DIR, exist_ok=True)
                path = os.path.join(config.TMP_DIR, f"img_{chat_id}.png")
                with open(path, "wb") as f:
                    f.write(part.inline_data.data)
                return path
        return None
    except Exception as e:
        print(f"Image generation failed: {e}")
        return None
