# handlers/measurement.py

import pytz

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from db import Session, Measurement
from parameters import PARAMETERS
from parameter_info import PARAMETER_INFO
from utils.keyboards import aquarium_menu, param_keyboard, cancel_keyboard
from handlers import AQUARIUM_MENU, PARAM_CHOOSE, PARAM_VALUE, CONFIRM_ADD_MEASUREMENT, SETTINGS
from handlers.notes import notes_menu_handler
from datetime import datetime
from types_map import TYPE_MAP

async def aquarium_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text
    if txt == "➕ Измерение":
        kb = param_keyboard(context.user_data["aq_type"])
        await update.message.reply_text("Выберите параметр:", reply_markup=kb)
        return PARAM_CHOOSE
    if txt == "Вернуться":
        from handlers.base import menu
        return await menu(update, context)
    if txt == "Настройка":
        from handlers.settings import settings_menu_handler
        await settings_menu_handler(update, context)
        return SETTINGS
    if txt == "📅 История":
        from handlers.history import history_menu_handler
        return await history_menu_handler(update, context)
    if txt == "🗒 Заметки":
        return await notes_menu_handler(update, context)
    await update.message.reply_text("Выберите действие.", reply_markup=aquarium_menu())
    return AQUARIUM_MENU

async def param_choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text
    if txt == "Отмена":
        return await aquarium_menu_handler(update, context)
    param = txt.split(" (")[0]
    if param not in PARAMETERS:
        await update.message.reply_text("Выберите параметр кнопкой.")
        return PARAM_CHOOSE
    context.user_data["param_name"] = param
    aq_type_ru = context.user_data.get("aq_type", "морской")
    aq_type = TYPE_MAP.get(aq_type_ru, "marine")
    norm = PARAMETERS[param][aq_type]
    await update.message.reply_text(
        f"Введите {param} ({norm['min']}–{norm['max']} {norm['unit']}), или «Отмена».",
        reply_markup=cancel_keyboard()
    )
    return PARAM_VALUE

async def param_value(update, context, forced_value=None):
    if forced_value is not None:
        txt = str(forced_value)
    else:
        txt = update.message.text
    if txt == "Отмена":
        from handlers.measurement import aquarium_menu_handler
        return await aquarium_menu_handler(update, context)
    try:
        val = float(txt.replace(",", "."))
    except:
        await update.message.reply_text("Введите число.")
        return PARAM_VALUE

    session = Session()
    aq_id = context.user_data["aquarium_id"]
    param_name = context.user_data["param_name"]
    tz = pytz.timezone("Europe/Moscow")  # или твой реальный часовой пояс
    today = datetime.now(tz).date()

    # Проверка — было ли уже сегодня такое измерение
    existing = session.query(Measurement).filter(
        Measurement.aquarium_id == aq_id,
        Measurement.param == param_name,
        Measurement.created_at >= datetime(today.year, today.month, today.day)
    ).first()

    if existing and not context.user_data.get("force_add_measurement"):
        context.user_data["pending_value"] = val
        await update.message.reply_text(
            f"Измерение параметра «{param_name}» уже добавлено сегодня.\n"
            "Продолжить (добавить новое) или отменить?",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("Продолжить"), KeyboardButton("Отмена")]],
                resize_keyboard=True
            )
        )
        return CONFIRM_ADD_MEASUREMENT

    # Добавление нового измерения
    m = Measurement(
        aquarium_id=aq_id,
        param=param_name,
        value=val,
        created_at=datetime.now(tz)
    )
    session.add(m)
    session.commit()

    context.user_data.pop("force_add_measurement", None)
    context.user_data.pop("pending_value", None)

    aq_type_ru = context.user_data.get("aq_type", "морской")
    aq_type = TYPE_MAP.get(aq_type_ru, "marine")
    norm = PARAMETERS[m.param][aq_type]
    mark = "🚨" if (val < norm["min"] or val > norm["max"]) else "✅"
    await update.message.reply_text(
        f"{m.param}: {m.value} {mark} (норма: {norm['min']}–{norm['max']} {norm['unit']})",
        reply_markup=aquarium_menu()
    )

    # Вывод полезной информации, если значение вне нормы
    if val < norm["min"] or val > norm["max"]:
        aq_type_ru = context.user_data.get("aq_type", "морской")
        aq_type = TYPE_MAP.get(aq_type_ru, "marine")
        info = PARAMETER_INFO.get(param_name)
        if info:
            about = info["about"].get(aq_type) or info["about"].get("common")
            if val < norm["min"]:
                danger = info["danger_low"].get(aq_type) or info["danger_low"].get("common")
                correction = info["correction_low"].get(aq_type) or info["correction_low"].get("common")
                msg = (
                    f"⚠️ <b>{param_name}</b> слишком низкое!\n"
                    f"{about}\n"
                    f"<b>Последствия:</b> {danger}\n"
                    f"<b>Как скорректировать:</b> {correction}"
                )
            else:
                danger = info["danger_high"].get(aq_type) or info["danger_high"].get("common")
                correction = info["correction_high"].get(aq_type) or info["correction_high"].get("common")
                msg = (
                    f"⚠️ <b>{param_name}</b> слишком высокое!\n"
                    f"{about}\n"
                    f"<b>Последствия:</b> {danger}\n"
                    f"<b>Как скорректировать:</b> {correction}"
                )
            await update.message.reply_text(msg, parse_mode="HTML")
    return AQUARIUM_MENU

async def confirm_add_measurement(update, context):
    txt = update.message.text
    if txt == "Продолжить":
        context.user_data["force_add_measurement"] = True
        # просто вызовем param_value с нужным значением напрямую
        val = context.user_data["pending_value"]
        return await param_value(update, context, forced_value=val)
    else:
        from handlers.measurement import aquarium_menu_handler
        await update.message.reply_text("Добавление измерения отменено.", reply_markup=aquarium_menu())
        return AQUARIUM_MENU