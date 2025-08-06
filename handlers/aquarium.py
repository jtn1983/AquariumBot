# handlers/aquarium.py

from telegram import ReplyKeyboardMarkup, KeyboardButton, Update
from telegram.ext import ContextTypes
from db import Session, Aquarium
from utils.keyboards import main_menu, aquarium_menu, cancel_keyboard, param_keyboard
from handlers import (
    MENU, CHOOSE_AQUARIUM,
    ADD_AQUARIUM_NAME, ADD_AQUARIUM_TYPE, ADD_AQUARIUM_VOLUME,
    AQUARIUM_MENU,
)
from handlers.base import menu

async def show_aquariums(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    aquas = session.query(Aquarium).filter_by(user_id=update.effective_user.id).all()
    if not aquas:
        await update.message.reply_text("У вас нет аквариумов.", reply_markup=main_menu())
        return MENU

    buttons = [[KeyboardButton(f"{a.id}: {a.name}")] for a in aquas]
    buttons.append([KeyboardButton("Вернуться")])
    await update.message.reply_text(
        "Мои аквариумы:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return CHOOSE_AQUARIUM

async def choose_aquarium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Вернуться":
        return await menu(update, context)
    try:
        aq_id = int(text.split(":")[0])
    except:
        await update.message.reply_text("Пожалуйста, выберите аквариум кнопкой.")
        return CHOOSE_AQUARIUM

    session = Session()
    aq = session.get(Aquarium, aq_id)
    if not aq:
        await update.message.reply_text("Аквариум не найден.")
        return CHOOSE_AQUARIUM

    context.user_data["aquarium_id"] = aq.id
    context.user_data["aq_type"] = aq.type
    await update.message.reply_text(
        f"Аквариум: {aq.name} ({aq.type}, {aq.volume} л)",
        reply_markup=aquarium_menu()
    )
    return AQUARIUM_MENU

async def add_aquarium_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите название аквариума:", reply_markup=cancel_keyboard())
    return ADD_AQUARIUM_NAME

async def add_aquarium_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if txt.lower() == "отмена":
        return await menu(update, context)
    context.user_data["new_aq_name"] = txt
    await update.message.reply_text(
        "Выберите тип аквариума:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("Морской")], [KeyboardButton("Пресный")], [KeyboardButton("Отмена")]],
            resize_keyboard=True
        )
    )
    return ADD_AQUARIUM_TYPE

async def add_aquarium_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip().lower()
    if t == "отмена":
        return await menu(update, context)
    if t not in ("морской", "пресный"):
        await update.message.reply_text(
            "Пожалуйста, выберите тип аквариума:",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("Морской")], [KeyboardButton("Пресный")], [KeyboardButton("Отмена")]],
                resize_keyboard=True
            )
        )
        return ADD_AQUARIUM_TYPE
    context.user_data["new_aq_type"] = t
    await update.message.reply_text("Укажите объём в литрах:", reply_markup=cancel_keyboard())
    return ADD_AQUARIUM_VOLUME

async def add_aquarium_volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip().lower()
    if txt == "отмена":
        return await menu(update, context)
    try:
        vol = float(txt.replace(",", "."))
        if vol <= 0:
            raise ValueError
    except:
        await update.message.reply_text("Введите число > 0 или «Отмена».")
        return ADD_AQUARIUM_VOLUME

    session = Session()
    aq = Aquarium(
        user_id=update.effective_user.id,
        name=context.user_data["new_aq_name"],
        type=context.user_data["new_aq_type"],
        volume=vol
    )
    session.add(aq)
    session.commit()
    await update.message.reply_text(f"Аквариум «{aq.name}» добавлен.", reply_markup=main_menu())
    return MENU