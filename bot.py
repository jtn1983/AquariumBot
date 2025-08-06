# bot.py

from telegram.ext import (
    ApplicationBuilder, CommandHandler, ConversationHandler,
    MessageHandler, filters, CallbackQueryHandler
)

from handlers import (
    MENU, CHOOSE_AQUARIUM,
    ADD_AQUARIUM_NAME, ADD_AQUARIUM_TYPE, ADD_AQUARIUM_VOLUME,
    AQUARIUM_MENU, PARAM_CHOOSE, PARAM_VALUE,
    HISTORY_MENU, HISTORY_PERIOD, HISTORY_YEAR, HISTORY_MONTH, HISTORY_PAGINATE,
    CONFIRM_ADD_MEASUREMENT, CHART_PARAM, SETTINGS, EDIT_NAME, EDIT_VOLUME, EDIT_TYPE, CONFIRM_DELETE, SERVICE_MENU,
    ADD_SERVICE_STEP, DELETE_SERVICE_STEP, MARK_DONE_STEP,
    NOTES_MENU, NOTE_ADD, NOTE_EDIT, NOTE_DELETE_CONFIRM,
)

from config import TELEGRAM_TOKEN

from handlers.base import start, menu
from handlers.aquarium import (
    show_aquariums, choose_aquarium,
    add_aquarium_start, add_aquarium_name,
    add_aquarium_type, add_aquarium_volume
)
from handlers.measurement import aquarium_menu_handler, param_choose, param_value, confirm_add_measurement
from handlers.history import (
    history_menu_handler, history_period_handler,
    history_month_handler, history_paginate_handler, history_year_handler
)

from handlers.charts import show_chart_handler, chart_param_handler

from handlers.settings import (
    edit_name_handler, set_name_handler,
    edit_volume_handler, set_volume_handler,
    edit_type_handler, set_type_handler,
    delete_aquarium_handler, confirm_delete_handler,
    settings_back_handler, settings_cancel_action
)

from handlers.advice import advice_handler

from handlers.service import (
    service_menu_handler, add_service_handler, add_service_step,
    mark_done_handler, mark_done_step, delete_service_handler, delete_service_step,
    add_service_period_callback,
    snooze_callback,
    delete_service_callback, mark_done_callback, done_force_callback, done_cancel_callback, add_service_remind_time_callback
)

from handlers.notes import (
    notes_menu_handler,
    notes_prev_page, notes_next_page, open_note_by_number,
    back_to_aquarium_from_reply, back_to_list_from_reply,
    note_edit_from_reply, note_add_handler, note_edit_save,
    note_delete_request, note_delete_confirm,
    note_pin_toggle_from_reply,
)

from reminder import reminder_job

async def start_reminders(app):
    app.create_task(reminder_job(app.bot))

def get_app():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(start_reminders).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [
                MessageHandler(filters.Regex("^Мои аквариумы$"), show_aquariums),
                MessageHandler(filters.Regex("^Добавить аквариум$"), add_aquarium_start),
                MessageHandler(filters.TEXT, menu),
            ],
            SETTINGS: [
                MessageHandler(filters.Regex("(?i)^назад$"), settings_back_handler),
                MessageHandler(filters.Regex("(?i)^изменить название$"), edit_name_handler),
                MessageHandler(filters.Regex("(?i)^изменить литраж$"), edit_volume_handler),
                MessageHandler(filters.Regex("(?i)^изменить тип$"), edit_type_handler),
                MessageHandler(filters.Regex("(?i)^удалить аквариум$"), delete_aquarium_handler),
            ],
            EDIT_NAME: [
                MessageHandler(filters.Regex("(?i)^назад$"), settings_cancel_action),
                MessageHandler(filters.TEXT, set_name_handler)
            ],
            EDIT_VOLUME: [
                MessageHandler(filters.Regex("(?i)^назад$"), settings_cancel_action),
                MessageHandler(filters.TEXT, set_volume_handler)
            ],
            EDIT_TYPE: [
                MessageHandler(filters.Regex("(?i)^назад$"), settings_cancel_action),
                MessageHandler(filters.TEXT, set_type_handler)
            ],
            CONFIRM_DELETE: [
                MessageHandler(filters.Regex("(?i)^назад$"), settings_cancel_action),
                MessageHandler(filters.TEXT, confirm_delete_handler)
            ],
            
            CHOOSE_AQUARIUM: [MessageHandler(filters.TEXT, choose_aquarium)],
            ADD_AQUARIUM_NAME: [MessageHandler(filters.TEXT, add_aquarium_name)],
            ADD_AQUARIUM_TYPE: [MessageHandler(filters.TEXT, add_aquarium_type)],
            ADD_AQUARIUM_VOLUME: [MessageHandler(filters.TEXT, add_aquarium_volume)],
            AQUARIUM_MENU: [
                MessageHandler(filters.Regex("^Обслуживание$"), service_menu_handler),
                MessageHandler(filters.Regex("^График$"), show_chart_handler),
                MessageHandler(filters.Regex("^Советы$"), advice_handler),
                MessageHandler(filters.Regex("^🗒 Заметки$"), notes_menu_handler),
                MessageHandler(filters.TEXT, aquarium_menu_handler),
            ],
            SERVICE_MENU: [
                MessageHandler(filters.Regex("^Добавить напоминание$"), add_service_handler),
                MessageHandler(filters.Regex("^Отметить как выполнено$"), mark_done_handler),
                MessageHandler(filters.Regex("^Удалить напоминание$"), delete_service_handler),
                MessageHandler(filters.Regex(r"^\d+$"), mark_done_step),
                MessageHandler(filters.Regex(r"^\d+$"), delete_service_step),
                MessageHandler(filters.Regex("^Назад$"), aquarium_menu_handler),
            ],
            DELETE_SERVICE_STEP: [
                MessageHandler(filters.Regex("^Назад$"), service_menu_handler),
                MessageHandler(filters.Regex("^(Добавить напоминание|Удалить напоминание|Отметить как выполнено)$"), service_menu_handler),
                CallbackQueryHandler(delete_service_callback, pattern=r"^del_"),
            ],
            ADD_SERVICE_STEP: [
                CallbackQueryHandler(add_service_period_callback, pattern=r"^period_"),
                CallbackQueryHandler(add_service_remind_time_callback, pattern=r"^remind_"),
                MessageHandler(filters.TEXT, add_service_step),
            ],
            MARK_DONE_STEP: [
                MessageHandler(filters.Regex("^Назад$"), service_menu_handler),
                MessageHandler(filters.Regex("^(Добавить напоминание|Удалить напоминание|Отметить как выполнено)$"), service_menu_handler),
                CallbackQueryHandler(mark_done_callback, pattern=r"^done_"),
            ],
            NOTES_MENU: [
                # список заметок: добавить, навигация, открыть по номеру, выйти
                MessageHandler(filters.Regex("^➕ Добавить заметку$"), note_add_handler),
                MessageHandler(filters.Regex("^⬅️ Предыдущие$"), notes_prev_page),
                MessageHandler(filters.Regex("^➡️ Следующие$"), notes_next_page),
                MessageHandler(filters.Regex("^[1-5]$"), open_note_by_number),
                MessageHandler(filters.Regex("^↩️ Назад к аквариуму$"), back_to_aquarium_from_reply),

                # экран заметки: редактировать, удалить, закрепить, назад к списку
                MessageHandler(filters.Regex("^✏️ Редактировать$"), note_edit_from_reply),
                MessageHandler(filters.Regex("^🗑 Удалить$"), note_delete_request),
                MessageHandler(filters.Regex("^📌 (Закрепить|Открепить)$"), note_pin_toggle_from_reply),
                MessageHandler(filters.Regex("^↩️ К списку заметок$"), back_to_list_from_reply),
            ],

            # Ввод текста новой заметки
            NOTE_ADD: [
                MessageHandler(filters.PHOTO, note_add_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, note_add_handler),
            ],

            # Ввод текста при редактировании
            NOTE_EDIT: [
                MessageHandler(filters.Regex("^Отмена$"), notes_menu_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, note_edit_save),
            ],
            NOTE_DELETE_CONFIRM: [
                MessageHandler(
                    filters.Regex("^(✅ Да, удалить|↩️ Отмена удаления)$"),
                    note_delete_confirm
                ),
            ],
            PARAM_CHOOSE: [MessageHandler(filters.TEXT, param_choose)],
            PARAM_VALUE: [MessageHandler(filters.TEXT, param_value)],
            HISTORY_MENU: [MessageHandler(filters.Regex("^📅 История$"), history_menu_handler)],
            HISTORY_PERIOD: [MessageHandler(filters.TEXT, history_period_handler)],
            HISTORY_YEAR: [MessageHandler(filters.TEXT, history_year_handler)],
            HISTORY_MONTH: [MessageHandler(filters.TEXT, history_month_handler)],
            HISTORY_PAGINATE: [MessageHandler(filters.TEXT, history_paginate_handler)],
            CONFIRM_ADD_MEASUREMENT: [MessageHandler(filters.TEXT, confirm_add_measurement)],
            CHART_PARAM: [MessageHandler(filters.TEXT, chart_param_handler)],
            
        },
        fallbacks=[MessageHandler(filters.COMMAND, start)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(snooze_callback, pattern=r"^snooze_\d+_\d+$"))
    app.add_handler(CallbackQueryHandler(mark_done_callback, pattern=r"^done_\d+$"))
    app.add_handler(CallbackQueryHandler(done_force_callback, pattern=r"^doneforce_\d+$"))
    app.add_handler(CallbackQueryHandler(done_cancel_callback, pattern=r"^donecancel_\d+$"))
    return app