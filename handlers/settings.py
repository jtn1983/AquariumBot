from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from db import Session, Aquarium
from utils.keyboards import aquarium_menu, main_menu, setting_keyboard
from handlers import SETTINGS, EDIT_NAME, EDIT_VOLUME, EDIT_TYPE, CONFIRM_DELETE, MENU

async def settings_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Настройки аквариума:", reply_markup=setting_keyboard())
    return SETTINGS

async def edit_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите новое название:")
    return EDIT_NAME

async def set_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    aq_id = context.user_data.get("aquarium_id")
    if not aq_id:
        await update.message.reply_text("Ошибка: не выбран аквариум.")
        return SETTINGS
    new_name = update.message.text.strip()
    session = Session()
    aq = session.query(Aquarium).filter_by(id=aq_id).first()
    aq.name = new_name
    session.commit()
    await update.message.reply_text("Название изменено.", reply_markup=await settings_keyboard())
    return SETTINGS

async def edit_volume_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите новый литраж:")
    return EDIT_VOLUME

async def set_volume_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    aq_id = context.user_data.get("aquarium_id")
    if not aq_id:
        await update.message.reply_text("Ошибка: не выбран аквариум.")
        return SETTINGS
    try:
        vol = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Введите число.")
        return EDIT_VOLUME
    session = Session()
    aq = session.query(Aquarium).filter_by(id=aq_id).first()
    aq.volume = vol
    session.commit()
    await update.message.reply_text("Литраж изменён.", reply_markup=await settings_keyboard())
    return SETTINGS

async def edit_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите новый тип (морской/пресный):")
    return EDIT_TYPE

async def set_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    aq_id = context.user_data.get("aquarium_id")
    if not aq_id:
        await update.message.reply_text("Ошибка: не выбран аквариум.")
        return SETTINGS
    new_type = update.message.text.strip().lower()
    if new_type not in ["морской", "пресный"]:
        await update.message.reply_text("Введите «морской» или «пресный».")
        return EDIT_TYPE
    session = Session()
    aq = session.query(Aquarium).filter_by(id=aq_id).first()
    aq.type = new_type
    session.commit()
    await update.message.reply_text("Тип изменён.", reply_markup=await settings_keyboard())
    return SETTINGS

async def delete_aquarium_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Вы уверены? Напишите «Да» или «Нет».")
    return CONFIRM_DELETE

async def confirm_delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip().lower()
    if txt == "да":
        aq_id = context.user_data.get("aquarium_id")
        if not aq_id:
            await update.message.reply_text("Ошибка: не выбран аквариум.")
            return SETTINGS
        session = Session()
        aq = session.query(Aquarium).filter_by(id=aq_id).first()
        session.delete(aq)
        session.commit()
        await update.message.reply_text("Аквариум удалён.", reply_markup=main_menu())
        return MENU  # <--- возвращаемся в главное меню
    else:
        await update.message.reply_text("Удаление отменено.", reply_markup=await settings_keyboard())
        return SETTINGS

async def settings_cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено.")
    return await settings_menu_handler(update, context)

# Назад из меню настроек (уже возвращаемся в меню аквариума)
async def settings_back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.measurement import aquarium_menu_handler
    return await aquarium_menu_handler(update, context)

async def settings_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("Изменить название"), KeyboardButton("Изменить литраж")],
            [KeyboardButton("Изменить тип"), KeyboardButton("Удалить аквариум")],
            [KeyboardButton("Назад")]
        ],
        resize_keyboard=True
    )