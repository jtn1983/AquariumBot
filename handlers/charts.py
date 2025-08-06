# handlers/charts.py

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from db import Session, Measurement
from parameters import PARAMETERS
from handlers.measurement import TYPE_MAP
from utils.keyboards import aquarium_menu
import matplotlib.pyplot as plt
import io
import matplotlib.dates as mdates
import collections

from handlers import AQUARIUM_MENU, CHART_PARAM
from handlers.measurement import aquarium_menu_handler

async def show_chart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    params = list(PARAMETERS.keys())
    kb = [[KeyboardButton(p)] for p in params] + [[KeyboardButton("Отмена")]]
    await update.message.reply_text("Выберите параметр для графика:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return CHART_PARAM

async def chart_param_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    param = update.message.text
    aq_type_ru = context.user_data.get("aq_type", "морской")
    aq_type = TYPE_MAP.get(aq_type_ru, "marine")
    if param == "Отмена":
        return await aquarium_menu_handler(update, context)

    session = Session()
    aquarium_id = context.user_data.get("aquarium_id")
    measurements = (
        session.query(Measurement)
        .filter_by(aquarium_id=aquarium_id, param=param)
        .order_by(Measurement.created_at)
        .all()
    )
    if not measurements:
        await update.message.reply_text("Нет данных для этого параметра.", reply_markup=aquarium_menu())
        return AQUARIUM_MENU

    uniq_dates = collections.OrderedDict()
    for m in measurements:
        d = m.created_at.date()
        uniq_dates[d] = m.value  # Если дубль - останется последнее

    dates = list(uniq_dates.keys())
    values = list(uniq_dates.values())

    plt.figure(figsize=(7,4))
    plt.plot(dates, values, marker='o')
    plt.title(f"Динамика: {param}")
    plt.xlabel("Дата")
    plt.ylabel(f"{param} ({PARAMETERS[param][aq_type]['unit']})")
    plt.grid(True)
    plt.tight_layout()

    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
    plt.xticks(rotation=45)

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    await update.message.reply_photo(
        photo=buf,
        caption=f"График {param} (норма: {PARAMETERS[param][aq_type]['min']}–{PARAMETERS[param][aq_type]['max']} {PARAMETERS[param][aq_type]['unit']})",
        reply_markup=aquarium_menu()
    )
    buf.close()
    return AQUARIUM_MENU