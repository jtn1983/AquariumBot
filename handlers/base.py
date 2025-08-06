# handlers/base.py

from telegram import Update
from telegram.ext import ContextTypes
from utils.keyboards import main_menu
from handlers import MENU

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Это бот для журналирования аквариума.",
        reply_markup=main_menu()
    )
    return MENU

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Главное меню.", reply_markup=main_menu())
    return MENU