import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import CommandStart, Command

import config
import ai_router
import excel_maker
import image_maker
import memory

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot")

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()


def clean_markdown(text: str) -> str:
    """Убирает markdown-звёздочки/решётки из ответа модели, чтобы Telegram не показывал их как есть."""
    import re
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)   # **жирный** -> жирный
    text = re.sub(r"\*(.+?)\*", r"\1", text)        # *курсив* -> курсив
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)  # ### заголовок -> заголовок
    text = text.replace("__", "")
    return text


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Привет! Я универсальный ИИ-ассистент 🤖\n\n"
        "— Пиши обычные вопросы — отвечу как чат-бот\n"
        "— Пришли голосовое — распознаю и отвечу\n"
        "— Попроси 'сделай таблицу про...' — пришлю Excel\n"
        "— Попроси 'нарисуй...' — сгенерирую картинку\n\n"
        "Я помню весь наш диалог, даже если отвечали разные модели.\n"
        "/reset — забыть историю и начать заново"
    )


@dp.message(Command("reset"))
async def reset(message: Message):
    memory.clear_history(message.chat.id)
    await message.answer("Память очищена, начинаем с чистого листа 🧹")


@dp.message(F.voice)
async def handle_voice(message: Message):
    await bot.send_chat_action(message.chat.id, "typing")
    os.makedirs(config.TMP_DIR, exist_ok=True)
    file_path = os.path.join(config.TMP_DIR, f"voice_{message.chat.id}.ogg")

    file = await bot.get_file(message.voice.file_id)
    await bot.download_file(file.file_path, destination=file_path)

    text = ai_router.transcribe_voice(file_path)
    if not text:
        await message.answer("Не удалось распознать голосовое 😔 Попробуй ещё раз.")
        return

    await message.answer(f"🎙 Распознал: {text}")
    await process_text(message, text)


@dp.message(F.text)
async def handle_text(message: Message):
    await process_text(message, message.text)


async def process_text(message: Message, user_text: str):
    chat_id = message.chat.id
    intent = ai_router.detect_intent(user_text)

    # Пишем запрос пользователя в ЕДИНУЮ память сразу — все режимы её используют
    memory.add_message(chat_id, "user", user_text)

    if intent == "excel":
        await message.answer("📊 Считаю и собираю таблицу...")
        try:
            context = memory.get_history(chat_id)
            path, summary = excel_maker.build_excel(user_text, chat_id, context)
            await message.answer_document(FSInputFile(path), caption=summary)
            memory.add_message(chat_id, "assistant", f"[Собрал таблицу] {summary}")
        except Exception as e:
            log.error(f"Excel error: {e}")
            await message.answer("Не получилось собрать таблицу, попробуй переформулировать запрос.")
        return

    if intent == "image":
        await message.answer("🎨 Генерирую картинку...")
        path = image_maker.generate_image(user_text, chat_id)
        if path:
            await message.answer_photo(FSInputFile(path))
            memory.add_message(chat_id, "assistant", f"[Сгенерировал картинку по запросу] {user_text}")
        else:
            await message.answer("Не получилось сгенерировать картинку, попробуй ещё раз.")
        return

    # обычный чат — подтягиваем всю историю (включая факты про таблицы/картинки выше)
    context = memory.get_history(chat_id)
    reply = ai_router.ask(context)
    memory.add_message(chat_id, "assistant", reply)

    await message.answer(clean_markdown(reply))


async def main():
    log.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
