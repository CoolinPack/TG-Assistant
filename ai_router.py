"""
Роутер моделей с ротацией: сначала перебирает ВСЕ модели Gemini,
потом ВСЕ модели Mistral, потом GPT-OSS. Если всё упало — честно об этом говорит.
Единая память (memory.py) используется во всех режимах — чат/таблицы/картинки
пишут и читают из одной истории, поэтому любая модель видит общий контекст.

Использует новую библиотеку google-genai (актуальная, старая google-generativeai
не поддерживает свежие модели и снята с поддержки).
"""
import logging
from google import genai as google_genai
from mistralai import Mistral
from openai import OpenAI

import config

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ai_router")

_gemini_client = google_genai.Client(api_key=config.GEMINI_API_KEY)
_mistral_client = Mistral(api_key=config.MISTRAL_API_KEY)
_gptoss_client = OpenAI(api_key=config.GPTOSS_API_KEY, base_url=config.GPTOSS_BASE_URL)

SYSTEM_PROMPT = (
    "Ты — универсальный ИИ-ассистент в Telegram. Отвечай кратко и по делу, "
    "на русском языке, если пользователь не просит иначе. Учитывай контекст "
    "предыдущих сообщений в диалоге, даже если раньше отвечала другая модель."
)


def _try_gemini_model(model_name: str, messages: list[dict]) -> str | None:
    try:
        history_text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        resp = _gemini_client.models.generate_content(
            model=model_name,
            contents=f"{SYSTEM_PROMPT}\n\n{history_text}",
        )
        return resp.text
    except Exception as e:
        log.warning(f"Gemini[{model_name}] failed: {e}")
        return None


def _try_mistral_model(model_name: str, messages: list[dict]) -> str | None:
    try:
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        resp = _mistral_client.chat.complete(model=model_name, messages=full_messages)
        return resp.choices[0].message.content
    except Exception as e:
        log.warning(f"Mistral[{model_name}] failed: {e}")
        return None


def _try_gptoss(messages: list[dict]) -> str | None:
    try:
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        resp = _gptoss_client.chat.completions.create(model=config.GPTOSS_MODEL, messages=full_messages)
        return resp.choices[0].message.content
    except Exception as e:
        log.warning(f"GPT-OSS failed: {e}")
        return None


def ask(messages: list[dict]) -> str:
    """Перебирает все модели по очереди (все Gemini -> все Mistral -> GPT-OSS)."""
    for model_name in config.GEMINI_MODELS:
        result = _try_gemini_model(model_name, messages)
        if result:
            return result

    for model_name in config.MISTRAL_MODELS:
        result = _try_mistral_model(model_name, messages)
        if result:
            return result

    result = _try_gptoss(messages)
    if result:
        return result

    return "Извини, все модели сейчас недоступны, попробуй чуть позже 🙏"


def transcribe_voice(file_path: str) -> str:
    """Распознаёт голосовое через Gemini. Аудио передаётся напрямую байтами — без
    отдельной загрузки файла, это надёжнее для коротких голосовых из Telegram."""
    with open(file_path, "rb") as f:
        audio_bytes = f.read()

    for model_name in config.GEMINI_MODELS:
        try:
            resp = _gemini_client.models.generate_content(
                model=model_name,
                contents=[
                    "Расшифруй это аудио дословно, без комментариев.",
                    google_genai.types.Part.from_bytes(data=audio_bytes, mime_type="audio/ogg"),
                ],
            )
            if resp.text:
                return resp.text.strip()
        except Exception as e:
            log.warning(f"Voice transcription via {model_name} failed: {e}")
            continue
    return ""


def detect_intent(user_text: str) -> str:
    text = user_text.lower()
    excel_words = ["таблиц", "excel", "эксель", "xlsx", "посчитай", "расчёт", "расчет"]
    image_words = ["нарисуй", "сгенерируй картинку", "картинка", "изображение", "фото сделай"]

    if any(w in text for w in excel_words):
        return "excel"
    if any(w in text for w in image_words):
        return "image"
    return "chat"
