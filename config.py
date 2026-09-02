import os

# === Telegram ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "ВСТАВЬ_ТОКЕН_БОТА")

# === API ключи моделей ===
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6JKB6lwYJaFVG2auJZu5a-SBwC0dHXIVMsuu6IkPqVzkg")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "baolEH7SRUO2xVSGkPhXruotDJ7XKx8u")
# GPT-OSS-120B обычно доступен через OpenRouter / Groq — укажи свой endpoint и ключ
GPTOSS_API_KEY = os.getenv("GPTOSS_API_KEY", "ВСТАВЬ_GPTOSS_KEY")
GPTOSS_BASE_URL = os.getenv("GPTOSS_BASE_URL", "https://openrouter.ai/api/v1")

# === Список моделей на провайдера — роутер пробует их по порядку, пока одна не ответит ===
# Меняй названия при необходимости (актуальные проверяй в доке провайдера)
GEMINI_MODELS = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
]
MISTRAL_MODELS = [
    "mistral-large-latest",
    "mistral-small-latest",
]
GPTOSS_MODEL = "openai/gpt-oss-120b"

# Папка для временных файлов (голосовые, excel)
TMP_DIR = "tmp"
