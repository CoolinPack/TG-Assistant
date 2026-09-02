"""
Просит модель вернуть данные в виде JSON-таблицы, затем собирает .xlsx
с автоподбором ширины колонок и жирным заголовком.
"""
import json
import os
import openpyxl
from openpyxl.styles import Font

import config
import ai_router

TABLE_PROMPT = (
    "Сформируй ответ СТРОГО в виде JSON без markdown-разметки и пояснений, формата:\n"
    '{"title": "Название таблицы", "columns": ["Кол1", "Кол2"], '
    '"rows": [["значение1", "значение2"], ...], "summary": "краткое текстовое описание результата"}\n\n'
    f"Запрос пользователя: "
)


def build_excel(user_text: str, chat_id: int, context: list[dict] | None = None) -> tuple[str, str]:
    """Возвращает (путь_к_файлу, текстовое_описание). context — история диалога для учёта предыдущих сообщений."""
    messages = list(context) if context else []
    messages.append({"role": "user", "content": TABLE_PROMPT + user_text})
    raw = ai_router.ask(messages)

    raw_clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(raw_clean)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = data.get("title", "Таблица")[:31]

    ws.append(data["columns"])
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for row in data["rows"]:
        ws.append(row)

    for col in ws.columns:
        max_len = max(len(str(c.value)) for c in col if c.value is not None) + 2
        ws.column_dimensions[col[0].column_letter].width = max_len

    os.makedirs(config.TMP_DIR, exist_ok=True)
    path = os.path.join(config.TMP_DIR, f"table_{chat_id}.xlsx")
    wb.save(path)

    return path, data.get("summary", "Готово!")
