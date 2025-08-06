import asyncio
from datetime import datetime, timedelta
from db import Session, ServiceTask
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

async def reminder_job(bot: Bot):
    while True:
        session = Session()
        now = datetime.now()
        tasks = session.query(ServiceTask).filter_by(is_active=True).all()
        session.close()
        for t in tasks:
            # Use next_run if set, otherwise compute from last_done
            next_due = t.next_run or (t.last_done + timedelta(days=t.period_days))
            if next_due <= now:
                try:
                    await bot.send_message(
                        chat_id=t.user_id,
                        text=f"🔔 Напоминание: {t.name} для вашего аквариума! (пора выполнить)",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("✅ Выполнено", callback_data=f"done_{t.id}")],
                            [InlineKeyboardButton("Отложить на 1 час", callback_data=f"snooze_1_{t.id}")],
                            [InlineKeyboardButton("Отложить на 3 часа", callback_data=f"snooze_3_{t.id}")],
                            [InlineKeyboardButton("Отложить на 12 часов", callback_data=f"snooze_12_{t.id}")]
                        ])
                    )
                except Exception as e:
                    print(f"Ошибка при отправке напоминания: {e}")
        await asyncio.sleep(60)  # Проверять каждую минуту (тест)