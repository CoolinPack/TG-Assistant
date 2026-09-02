"""
Роутер моделей с ротацией: сначала перебирает ВСЕ модели Gemini,
потом ВСЕ модели Mistral, потом GPT-OSS. Если всё упало — честно об этом говорит.
Единая память (memory.py) используется во всех режимах — чат/таблицы/картинки
пишут и читают из одной истории, поэтому любая модель видит общий контекст.
"""
import logging
import google.generativeai as genai
from mistralai import Mistral
from openai import OpenAI

import config

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ai_router")

genai.configure(api_key=config.GEMINI_API_KEY)
_mistral_client = Mistral(api_key=config.MISTRAL_API_KEY)
_gptoss_client = OpenAI(api_key=config.GPTOSS_API_KEY, base_url=config.GPTOSS_BASE_URL)

SYSTEM_PROMPT = (
    "Ты — универсальный ИИ-ассистент в Telegram. Отвечай кратко и по делу, "
    "на русском языке, если пользователь не просит иначе. Учитывай контекст "
    "предыдущих сообщений в диалоге, даже если раньше отвечала другая модель."
)


def _try_gemini_model(model_name: str, messages: list[dict]) -> str | None:
    try:
        model = genai.GenerativeModel(model_name)
        history_text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        resp = model.generate_content(f"{SYSTEM_PROMPT}\n\n{history_text}")
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
    """Распознаёт голосовое через Gemini (перебирает модели, если первая недоступна)."""
    import time

    try:
        audio_file = genai.upload_file(file_path, mime_type="audio/ogg")
        # ждём, пока Gemini обработает файл (обычно 1-5 секунд)
        for _ in range(15):
            audio_file = genai.get_file(audio_file.name)
            if audio_file.state.name == "ACTIVE":
                break
            time.sleep(1)
        else:
            log.warning("Файл аудио не стал ACTIVE вовремя")
            return ""
    except Exception as e:
        log.warning(f"Не удалось загрузить аудио в Gemini: {e}")
        return ""

    for model_name in config.GEMINI_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            resp = model.generate_content(
                ["Расшифруй это аудио дословно, без комментариев.", audio_file]
            )
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
