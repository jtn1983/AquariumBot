from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from db import Session, ServiceTask
from datetime import datetime, timedelta
from handlers import ADD_SERVICE_STEP, SERVICE_MENU, DELETE_SERVICE_STEP, MARK_DONE_STEP

def compute_next_run(period_days: int, remind_time, base: datetime | None = None) -> datetime:
    last_done = base or datetime.now()
    if remind_time:
        run_date = last_done + timedelta(days=period_days)
        dt_candidate = datetime.combine(run_date.date(), remind_time)
        if last_done.time() > remind_time:
            dt_candidate += timedelta(days=1)
        return dt_candidate
    return last_done + timedelta(days=period_days)

# Главное меню обслуживания
async def service_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Redirect reply-button "Отметить как выполнено" to inline-mark handler
    if update.message and update.message.text == "Отметить как выполнено":
        return await mark_done_handler(update, context)
    aquarium_id = context.user_data["aquarium_id"]
    session = Session()
    tasks = session.query(ServiceTask).filter_by(aquarium_id=aquarium_id, is_active=True).all()
    session.close()
    if not tasks:
        msg = "Нет активных задач по обслуживанию.\n\nДобавить новую?"
    else:
        msg = "Активные задачи:\n"
        for i, t in enumerate(tasks, 1):
            next_due = t.next_run
            time_str = t.remind_time.strftime("%H:%M") if t.remind_time else "любой момент"
            msg += (
                f"{i}. {t.name} — раз в {t.period_days} дн., {time_str}\n"
                f"Следующее: {next_due.strftime('%d.%m.%Y %H:%M')}\n"
            )
    kb = [
        [KeyboardButton("Добавить напоминание")],
        [KeyboardButton("Отметить как выполнено")],
        [KeyboardButton("Удалить напоминание")],
        [KeyboardButton("Назад")]
    ]
    msg_obj = update.message if update.message else update.callback_query.message
    await msg_obj.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return SERVICE_MENU

# Добавление напоминания (MVP-диалог: спрашивает название и период)
async def add_service_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["add_service_step"] = 1
    await update.message.reply_text("Введите название напоминания (например, Подменить воду):")
    return ADD_SERVICE_STEP

async def add_service_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip().lower() == "назад":
        await service_menu_handler(update, context)
        return SERVICE_MENU
    step = context.user_data.get("add_service_step", 1)
    if step == 1:
        # Ввод названия
        context.user_data["service_name"] = update.message.text
        context.user_data["add_service_step"] = 2
        kb = [
            [InlineKeyboardButton("7 дней", callback_data="period_7")],
            [InlineKeyboardButton("14 дней", callback_data="period_14")],
            [InlineKeyboardButton("30 дней", callback_data="period_30")],
            [InlineKeyboardButton("Ввести свой вариант", callback_data="period_custom")]
        ]
        await update.message.reply_text(
            "Как часто напоминать?",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return ADD_SERVICE_STEP
    elif step == 3:
        try:
            period = int(update.message.text)
            context.user_data["chosen_period"] = period
            context.user_data["add_service_step"] = 4
            kb = [
                [InlineKeyboardButton("07:00", callback_data="remind_07:00"),
                 InlineKeyboardButton("09:00", callback_data="remind_09:00")],
                [InlineKeyboardButton("12:00", callback_data="remind_12:00"),
                 InlineKeyboardButton("18:00", callback_data="remind_18:00")],
                [InlineKeyboardButton("21:00", callback_data="remind_21:00")],
                [InlineKeyboardButton("Ввести другое", callback_data="remind_custom")]
            ]
            await update.message.reply_text(
                "В какое время присылать напоминание?",
                reply_markup=InlineKeyboardMarkup(kb)
            )
            return ADD_SERVICE_STEP
        except ValueError:
            await update.message.reply_text("Введите только число (например, 7):")
            return ADD_SERVICE_STEP
    elif step == 4:
        try:
            remind_time = datetime.strptime(update.message.text, "%H:%M").time()
            context.user_data["remind_time"] = remind_time
            await save_service(update, context, context.user_data["chosen_period"])
            return SERVICE_MENU
        except Exception:
            await update.message.reply_text("Введите время в формате ЧЧ:ММ, например, 08:45")
            return ADD_SERVICE_STEP
    else:
        kb = [
            [InlineKeyboardButton("7 дней", callback_data="period_7")],
            [InlineKeyboardButton("14 дней", callback_data="period_14")],
            [InlineKeyboardButton("30 дней", callback_data="period_30")],
            [InlineKeyboardButton("Ввести свой вариант", callback_data="period_custom")]
        ]
        await update.message.reply_text(
            "Пожалуйста, выберите вариант из списка кнопок ниже ⬇️",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return ADD_SERVICE_STEP

# Обработка выбора периода через инлайн-кнопки
async def add_service_period_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("period_"):
        if data == "period_custom":
            context.user_data["add_service_step"] = 3
            await query.message.reply_text("Введите период в днях (например, 10):")
            return ADD_SERVICE_STEP
        else:
            period = int(data.split("_")[1])
            kb = [
                [InlineKeyboardButton("07:00", callback_data="remind_07:00"), InlineKeyboardButton("09:00", callback_data="remind_09:00")],
                [InlineKeyboardButton("12:00", callback_data="remind_12:00"), InlineKeyboardButton("18:00", callback_data="remind_18:00")],
                [InlineKeyboardButton("21:00", callback_data="remind_21:00")],
                [InlineKeyboardButton("Ввести другое", callback_data="remind_custom")]
            ]
            await query.message.reply_text(
                "В какое время присылать напоминание?",
                reply_markup=InlineKeyboardMarkup(kb)
            )
            context.user_data["chosen_period"] = period
            return ADD_SERVICE_STEP
    else:
        await query.message.reply_text("Ошибка выбора периода.")
        return ADD_SERVICE_STEP

# Новый обработчик выбора времени напоминания
async def add_service_remind_time_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("remind_"):
        if data == "remind_custom":
            await query.message.reply_text("Введите время в формате ЧЧ:ММ, например, 08:45")
            context.user_data["add_service_step"] = 4
            return ADD_SERVICE_STEP
        else:
            remind_time_str = data.split("_")[1]
            try:
                remind_time = datetime.strptime(remind_time_str, "%H:%M").time()
                context.user_data["remind_time"] = remind_time
                await save_service(update, context, context.user_data["chosen_period"])
                return SERVICE_MENU
            except Exception:
                await query.message.reply_text("Неверный формат времени. Введите время в формате ЧЧ:ММ, например, 08:45")
                context.user_data["add_service_step"] = 4
                return ADD_SERVICE_STEP


# Сохранение напоминания
async def save_service(update, context, period):
    if not context.user_data.get("service_name"):
        await update.effective_message.reply_text(
            "Ошибка: название напоминания не найдено. Попробуйте добавить заново."
        )
        await service_menu_handler(update, context)
        return SERVICE_MENU
    session = Session()
    aquarium_id = context.user_data["aquarium_id"]
    user_id = update.effective_user.id
    service = ServiceTask(
        aquarium_id=aquarium_id,
        user_id=user_id,
        name=context.user_data["service_name"],
        period_days=period,
        last_done=datetime.now(),
        is_active=True,
        remind_time=context.user_data.get("remind_time"),
        next_run=compute_next_run(period, context.user_data.get("remind_time"), base=datetime.now())
    )
    session.add(service)
    session.commit()
    session.close()
    await update.effective_message.reply_text("Напоминание добавлено!")
    context.user_data.pop("add_service_step", None)
    context.user_data.pop("service_name", None)
    context.user_data.pop("chosen_period", None)
    context.user_data.pop("remind_time", None)
    await service_menu_handler(update, context)
    return SERVICE_MENU

async def mark_done_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    aquarium_id = context.user_data["aquarium_id"]
    session = Session()
    tasks = session.query(ServiceTask).filter_by(aquarium_id=aquarium_id, is_active=True).all()
    session.close()
    if not tasks:
        await update.message.reply_text("Нет активных напоминаний.")
        return

    # Формируем inline-кнопки для каждой задачи
    kb = [
        [InlineKeyboardButton(t.name, callback_data=f"done_{t.id}")]
        for t in tasks
    ]
    await update.message.reply_text(
        "Выберите, что отметить как выполненное:",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return MARK_DONE_STEP

# Шаг 2: обработать выбор
async def mark_done_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip().lower() == "назад":
        await service_menu_handler(update, context)
        return SERVICE_MENU
    key = update.message.text.strip()
    task_id = context.user_data.get("mark_done_list", {}).get(key)
    if not task_id:
        await update.message.reply_text("Выберите номер из списка.")
        return
    session = Session()
    task = session.query(ServiceTask).get(task_id)
    if not task:
        await update.message.reply_text("Задача не найдена.")
        session.close()
        return
    now = datetime.now()
    due = task.next_run or compute_next_run(task.period_days, task.remind_time, base=task.last_done)
    if now < due:
        session.close()
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Да, выполнить раньше", callback_data=f"doneforce_{task.id}")],
            [InlineKeyboardButton("Отмена", callback_data=f"donecancel_{task.id}")]
        ])
        await update.message.reply_text(
            f"Срок ещё не подошёл (по плану {due.strftime('%d.%m.%Y %H:%M')}). Выполнить раньше?",
            reply_markup=kb
        )
        return SERVICE_MENU
    task_name = task.name
    task.last_done = now
    proposed = compute_next_run(task.period_days, task.remind_time, base=now)
    if task.next_run and proposed <= task.next_run:
        task.next_run = compute_next_run(task.period_days, task.remind_time, base=task.next_run)
    else:
        task.next_run = proposed
    session.commit()
    session.close()
    await update.message.reply_text(f"Задача «{task_name}» отмечена как выполненная!")
    context.user_data.pop("mark_done_list", None)
    await service_menu_handler(update, context)
    return SERVICE_MENU

# Обработка отметки задачи как выполненной через инлайн-кнопки
async def mark_done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("done_"):
        task_id = int(data.split("_")[1])
        session = Session()
        task = session.query(ServiceTask).get(task_id)
        if not task:
            await query.message.reply_text("Задача не найдена.")
            session.close()
            return

        now = datetime.now()
        due = task.next_run or compute_next_run(task.period_days, task.remind_time, base=task.last_done)
        if now < due:
            session.close()
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Да, выполнить раньше", callback_data=f"doneforce_{task.id}")],
                [InlineKeyboardButton("Отмена", callback_data=f"donecancel_{task.id}")]
            ])
            await query.message.reply_text(
                f"Внимание: срок ещё не подошёл (по плану {due.strftime('%d.%m.%Y %H:%M')}). Выполнить раньше?",
                reply_markup=kb
            )
            return

        task_name = task.name
        task.last_done = now
        proposed = compute_next_run(task.period_days, task.remind_time, base=now)
        if task.next_run and proposed <= task.next_run:
            task.next_run = compute_next_run(task.period_days, task.remind_time, base=task.next_run)
        else:
            task.next_run = proposed
        session.commit()
        session.close()
        await query.message.reply_text(f"Задача «{task_name}» отмечена как выполненная!")
        await service_menu_handler(update, context)
        return SERVICE_MENU

async def delete_service_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    aquarium_id = context.user_data["aquarium_id"]
    session = Session()
    tasks = session.query(ServiceTask).filter_by(aquarium_id=aquarium_id, is_active=True).all()
    session.close()
    if not tasks:
        await update.message.reply_text("Нет активных напоминаний.")
        return
    kb = [
        [InlineKeyboardButton(f"{t.name}", callback_data=f"del_{t.id}")]
        for t in tasks
    ]
    await update.message.reply_text(
        "Выберите напоминание для удаления:",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return DELETE_SERVICE_STEP

# Обработка удаления напоминания через инлайн-кнопки
async def delete_service_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("del_"):
        task_id = int(data.split("_")[1])
        session = Session()
        task = session.query(ServiceTask).get(task_id)
        if not task:
            await query.message.reply_text("Задача не найдена.")
            session.close()
            return
        task_name = task.name
        task.is_active = False
        session.commit()
        session.close()
        await query.message.reply_text(f"Задача «{task_name}» удалена!")
        await service_menu_handler(update, context)
        return SERVICE_MENU

# Шаг 2: обработать выбор
async def delete_service_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip().lower() == "назад":
        await service_menu_handler(update, context)
        return SERVICE_MENU
    key = update.message.text.strip()
    task_id = context.user_data.get("del_service_list", {}).get(key)
    if not task_id:
        await update.message.reply_text("Выберите номер из списка.")
        return
    session = Session()
    task = session.query(ServiceTask).get(task_id)
    if not task:
        await update.message.reply_text("Задача не найдена.")
        session.close()
        return
    task_name = task.name
    task.is_active = False
    session.commit()
    session.close()
    await update.message.reply_text(f"Задача «{task_name}» удалена!")
    context.user_data.pop("del_service_list", None)
    await service_menu_handler(update, context)
    return SERVICE_MENU


async def snooze_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data  # snooze_1_123
    try:
        _, hours, task_id = data.split("_")
        hours = int(hours)
        task_id = int(task_id)
    except Exception:
        await query.message.reply_text("Ошибка формата snooze.")
        return
    session = Session()
    task = session.query(ServiceTask).get(task_id)
    if not task:
        session.close()
        await query.message.reply_text("Задача не найдена.")
        return
    task.next_run = datetime.now() + timedelta(hours=hours)
    session.commit()
    session.close()
    await query.message.reply_text(f"Отложено на {hours} ч.")

# --- New callbacks for force/cancel done ---
async def done_force_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        task_id = int(query.data.split("_")[1])
    except Exception:
        await query.message.reply_text("Ошибка формата запроса.")
        return
    session = Session()
    task = session.query(ServiceTask).get(task_id)
    if not task:
        session.close()
        await query.message.reply_text("Задача не найдена.")
        return
    task_name = task.name
    now = datetime.now()
    task.last_done = now
    proposed = compute_next_run(task.period_days, task.remind_time, base=now)
    if task.next_run and proposed <= task.next_run:
        task.next_run = compute_next_run(task.period_days, task.remind_time, base=task.next_run)
    else:
        task.next_run = proposed
    session.commit()
    next_run_str = task.next_run.strftime('%d.%m.%Y %H:%M')
    session.close()
    await query.message.reply_text(
        f"Задача «{task_name}» выполнена раньше срока.\nСледующее: {next_run_str}"
    )
    await service_menu_handler(update, context)

async def done_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Ок, не отмечаю.")
    await service_menu_handler(update, context)
