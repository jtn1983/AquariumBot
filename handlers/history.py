# handlers/history.py

from telegram import ReplyKeyboardMarkup, KeyboardButton, Update
from telegram.ext import ContextTypes
from db import Session, Measurement
from parameters import PARAMETERS
from handlers.measurement import TYPE_MAP
from utils.helpers import get_last_months
from handlers import (
    AQUARIUM_MENU, HISTORY_MENU, HISTORY_PERIOD,
    HISTORY_MONTH, HISTORY_PAGINATE, HISTORY_YEAR
)
from utils.keyboards import aquarium_menu
from collections import defaultdict
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from handlers.measurement import aquarium_menu_handler
from sqlalchemy import func


history_menu_kb = ReplyKeyboardMarkup([
    [KeyboardButton("За сегодня"), KeyboardButton("За неделю")],
    [KeyboardButton("За месяц"), KeyboardButton("Выбрать месяц")],
    [KeyboardButton("Показать всё"), KeyboardButton("Назад")],
], resize_keyboard=True)

async def history_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выберите период истории:", reply_markup=history_menu_kb)
    return HISTORY_PERIOD

async def history_choose_year_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    aquarium_id = context.user_data["aquarium_id"]
    years = (
        session.query(func.extract('year', Measurement.created_at))
        .filter(Measurement.aquarium_id == aquarium_id)
        .group_by(func.extract('year', Measurement.created_at))
        .order_by(func.extract('year', Measurement.created_at).desc())
        .all()
    )
    if not years:
        await update.message.reply_text("Нет данных.", reply_markup=aquarium_menu())
        return HISTORY_MENU

    year_buttons = [[KeyboardButton(str(int(y[0])))] for y in years]
    year_buttons.append([KeyboardButton("Назад")])
    await update.message.reply_text(
        "Выберите год:",
        reply_markup=ReplyKeyboardMarkup(year_buttons, resize_keyboard=True)
    )
    return HISTORY_YEAR

async def history_period_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text
    now = datetime.now()
    if txt == "За сегодня":
        start, end = now.replace(hour=0,minute=0,second=0), now
    elif txt == "За неделю":
        start = (now - timedelta(days=now.weekday())).replace(hour=0,minute=0,second=0); end = now
    elif txt == "За месяц":
        start, end = now.replace(day=1,hour=0,minute=0,second=0), now
    elif txt == "Выбрать месяц":
        return await history_choose_year_handler(update, context)
    elif txt == "Показать всё":
        start, end = None, None
    elif txt == "Назад":
        return await aquarium_menu_handler(update, context)
    else:
        await update.message.reply_text("Пожалуйста, выберите.")
        return HISTORY_PERIOD

    context.user_data["history_range"] = (start, end)
    context.user_data["history_page"] = 0
    return await _send_history(update, context)

async def history_year_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Назад":
        return await history_menu_handler(update, context)

    selected_year = int(update.message.text)
    context.user_data["history_selected_year"] = selected_year

    session = Session()
    aquarium_id = context.user_data["aquarium_id"]
    months = (
        session.query(func.extract('month', Measurement.created_at))
        .filter(
            Measurement.aquarium_id == aquarium_id,
            func.extract('year', Measurement.created_at) == selected_year
        )
        .group_by(func.extract('month', Measurement.created_at))
        .order_by(func.extract('month', Measurement.created_at).desc())
        .all()
    )
    if not months:
        await update.message.reply_text("Нет данных за выбранный год.", reply_markup=aquarium_menu())
        return HISTORY_MENU

    month_buttons = [[KeyboardButton(f"{int(m[0]):02}.{selected_year}")] for m in months]
    month_buttons.append([KeyboardButton("Назад")])
    await update.message.reply_text(
        "Выберите месяц:",
        reply_markup=ReplyKeyboardMarkup(month_buttons, resize_keyboard=True)
    )
    return HISTORY_MONTH

async def history_month_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text
    if txt == "Назад":
        return await history_choose_year_handler(update, context)
    mo, yr = map(int, txt.split("."))
    start = datetime(yr,mo,1)
    end = (start + relativedelta(months=1)) - timedelta(seconds=1)
    context.user_data["history_range"] = (start, end)
    context.user_data["history_page"] = 0
    return await _send_history(update, context)

async def _send_history(update, context):
    start, end = context.user_data["history_range"]
    session = Session()
    aquarium_id = context.user_data["aquarium_id"]
    q = session.query(Measurement).filter(Measurement.aquarium_id == aquarium_id)
    if start and end:
        q = q.filter(Measurement.created_at.between(start, end))
    ms = q.order_by(Measurement.created_at.desc()).all()

    days = sorted({m.created_at.date() for m in ms}, reverse=True)
    chunks = [days[i:i+3] for i in range(0, len(days), 3)]
    page = context.user_data["history_page"]
    page = max(0, min(page, len(chunks) - 1))
    context.user_data["history_page"] = page

    sel = chunks[page] if chunks else []
    if not sel:
        await update.message.reply_text("Нет данных.", reply_markup=aquarium_menu())
        return HISTORY_PAGINATE

    text = ""
    aq_type_ru = context.user_data.get("aq_type", "морской")
    aq_type = TYPE_MAP.get(aq_type_ru, "marine")
    for d in sel:
        text += f"<b>📅 {d.strftime('%d.%m')}</b>\n"
        for p in PARAMETERS:
            vals = [m.value for m in ms if m.created_at.date() == d and m.param == p]
            if not vals:
                continue
            v = vals[0]
            n = PARAMETERS[p][aq_type]
            mark = ""
            if v < n["min"] or v > n["max"]:
                mark = " 🚨"
            val = f"{v:.1f}{mark}"
            text += f"— {p:14}: {val} (норма: {n['min']}–{n['max']} {n['unit']})\n"
        text += "\n"

    nav = []
    if page > 0: nav.append(KeyboardButton("◀️ Предыдущие"))
    if page < len(chunks) - 1: nav.append(KeyboardButton("Следующие ▶️"))
    nav.append(KeyboardButton("↩️ Меню"))

    await update.message.reply_text(
        text, parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup([nav], resize_keyboard=True)
    )
    return HISTORY_PAGINATE

async def history_paginate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text
    if txt=="◀️ Предыдущие":
        context.user_data["history_page"]-=1; return await _send_history(update, context)
    if txt=="Следующие ▶️":
        context.user_data["history_page"]+=1; return await _send_history(update, context)
    return await aquarium_menu_handler(update, context)