from telegram import Update, InputMediaPhoto
from telegram.ext import ContextTypes
from datetime import datetime
from db import Session, Note, Aquarium, NotePhoto
from handlers import NOTES_MENU, NOTE_ADD, NOTE_EDIT, NOTE_DELETE_CONFIRM, AQUARIUM_MENU
from utils.keyboards import aquarium_menu, notes_list_menu, note_view_menu, note_delete_confirm_menu, note_add_menu

PAGE_SIZE = 5


def _format_notes_page(session: Session, aquarium_id: int, page: int):
    q = (session.query(Note)
         .filter_by(aquarium_id=aquarium_id)
         .order_by(Note.is_pinned.desc(), Note.updated_at.desc()))
    total = q.count()
    notes = q.offset(page * PAGE_SIZE).limit(PAGE_SIZE).all()
    has_prev = page > 0
    has_next = (page + 1) * PAGE_SIZE < total

    page_map = {}
    lines = []
    if total == 0:
        lines.append("Заметок пока нет.\nНажмите «➕ Добавить заметку», чтобы создать первую.")
    else:
        for idx, n in enumerate(notes, start=1):
            page_map[str(idx)] = n.id
            pin = "📌 " if n.is_pinned else ""
            title = (n.title or (n.text[:30] + ("…" if len(n.text) > 30 else ""))) or "Без заголовка"
            dt = n.updated_at.strftime("%d.%m.%Y %H:%M")
            lines.append(f"{idx}. {pin}{title}  —  {dt}")
        lines.append("\nЧтобы открыть заметку — отправьте её номер (1–5).")

    return "\n".join(lines), page_map, has_prev, has_next, total


async def notes_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    aquarium_id = context.user_data.get("aquarium_id")
    if not aquarium_id:
        await update.effective_message.reply_text("Сначала выберите аквариум.", reply_markup=aquarium_menu())
        return AQUARIUM_MENU

    page = int(context.user_data.get("notes_page", 0))
    session = Session()
    text, page_map, has_prev, has_next, total = _format_notes_page(session, aquarium_id, page)

    context.user_data["notes_page"] = page
    context.user_data["notes_page_map"] = page_map

    title = session.get(Aquarium, aquarium_id).name
    head = f"Заметки для «{title}» ({total}):" if total else f"Заметки для «{title}»"
    await update.effective_message.reply_text(head)
    await update.effective_message.reply_text(text, reply_markup=notes_list_menu(has_prev, has_next))
    return NOTES_MENU

async def notes_prev_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    page = int(context.user_data.get("notes_page", 0))
    if page > 0:
        context.user_data["notes_page"] = page - 1
    return await notes_menu_handler(update, context)

async def notes_next_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    page = int(context.user_data.get("notes_page", 0))
    context.user_data["notes_page"] = page + 1
    return await notes_menu_handler(update, context)

async def open_note_by_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    num = update.message.text.strip()
    page_map = context.user_data.get("notes_page_map", {})
    if num not in page_map:
        await update.message.reply_text("Номер вне текущей страницы. Отправьте 1–5 или листайте страницы.")
        return NOTES_MENU
    note_id = page_map[num]
    return await note_view_show(update, context, note_id)

async def note_view_show(update: Update, context: ContextTypes.DEFAULT_TYPE, note_id: int):
    session = Session()
    note = session.get(Note, note_id)
    if not note:
        await update.effective_message.reply_text("Заметка не найдена.")
        return await notes_menu_handler(update, context)
    context.user_data["note_id"] = note.id
    # Заголовок и текст
    header = (
        f"<b>{note.title or 'Заметка'}</b>\n\n{note.text}\n\n"
        f"<i>Обновлено: {note.updated_at.strftime('%d.%m.%Y %H:%M')}</i>"
    )
    # Отправка альбома, если есть фото
    if note.photos:
        media = []
        for idx, ph in enumerate(note.photos):
            if idx == 0:
                media.append(InputMediaPhoto(ph.file_id, caption=header, parse_mode="HTML"))
            else:
                media.append(InputMediaPhoto(ph.file_id))
        await update.effective_message.reply_media_group(media)
        # После альбома отправляем клавиатуру
        await update.effective_message.reply_text("Действия со заметкой:", reply_markup=note_view_menu(note.is_pinned))
    else:
        await update.effective_message.reply_text(header, parse_mode="HTML", reply_markup=note_view_menu(note.is_pinned))
    return NOTES_MENU

# ----- Actions via bottom keyboard -----
async def notes_add_from_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отправьте текст заметки (или «Отмена»)." )
    return NOTE_ADD

async def back_to_aquarium_from_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("notes_page_map", None)
    await update.message.reply_text("Выберите действие.", reply_markup=aquarium_menu())
    return AQUARIUM_MENU

async def back_to_list_from_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await notes_menu_handler(update, context)

async def note_edit_from_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("note_id"):
        await update.message.reply_text("Сначала откройте заметку из списка.")
        return NOTES_MENU
    await update.message.reply_text("Отправьте новый текст заметки (или «Отмена»)." )
    return NOTE_EDIT

async def note_delete_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("note_id"):
        await update.message.reply_text("Сначала откройте заметку из списка.")
        return NOTES_MENU
    await update.message.reply_text("Удалить эту заметку?", reply_markup=note_delete_confirm_menu())
    return NOTE_DELETE_CONFIRM

async def note_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text.strip()
    note_id = context.user_data.get("note_id")
    if choice == "✅ Да, удалить" and note_id:
        session = Session()
        note = session.get(Note, note_id)
        if note:
            session.delete(note)
            session.commit()
            session.close()
        context.user_data.pop("note_id", None)
        await update.message.reply_text("Заметка удалена.")
        return await notes_menu_handler(update, context)
    else:
        await update.message.reply_text("Отмена удаления.")
        return await note_view_show(update, context, note_id)

async def note_pin_toggle_from_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note_id = context.user_data.get("note_id")
    if not note_id:
        await update.message.reply_text("Сначала откройте заметку из списка.")
        return NOTES_MENU
    session = Session()
    note = session.get(Note, note_id)
    if note:
        note.is_pinned = not note.is_pinned
        note.updated_at = datetime.utcnow()
        session.commit()
        session.close()
    return await note_view_show(update, context, note_id)


# ----- Saving text -----
async def note_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Инициализация накопителя
    if 'new_note_text' not in context.user_data:
        context.user_data['new_note_text'] = ''
        context.user_data['new_note_photos'] = []
    # Покажем меню действий
    await update.message.reply_text(
        "Добавление заметки: выберите действие или отправьте фото/текст",
        reply_markup=note_add_menu()
    )

    text = update.message.text
    # Ignore initial add-button click
    if text == "➕ Добавить заметку":
        return NOTE_ADD

    # Отмена создания
    if text == "❌ Отмена":
        context.user_data.pop('new_note_text', None)
        context.user_data.pop('new_note_photos', None)
        await update.message.reply_text("Создание заметки отменено.", reply_markup=None)
        return await notes_menu_handler(update, context)
    # Сохранение заметки
    if text == "✅ Сохранить":
        aquarium_id = context.user_data.get("aquarium_id")
        session = Session()
        note = Note(
            aquarium_id=aquarium_id,
            user_id=update.effective_user.id,
            text=context.user_data['new_note_text'],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(note)
        session.commit()
        # Сохраняем фото
        for file_id, caption in context.user_data['new_note_photos']:
            photo = NotePhoto(note_id=note.id, file_id=file_id, caption=caption)
            session.add(photo)
        session.commit()
        session.close()
        # Очистка
        context.user_data.pop('new_note_text', None)
        context.user_data.pop('new_note_photos', None)
        await update.message.reply_text("Заметка сохранена.", reply_markup=None)
        return await notes_menu_handler(update, context)

    # Приём фото
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        caption = update.message.caption or ''
        context.user_data['new_note_photos'].append((file_id, caption))
        await update.message.reply_text("Фото добавлено.", reply_markup=note_add_menu())
        return NOTE_ADD

    # Приём текста (не кнопки)
    if text and text not in ["✅ Сохранить", "❌ Отмена", "➕ Фото", "✏️ Текст", "➕ Добавить заметку"]:
        context.user_data['new_note_text'] = text
        await update.message.reply_text("Текст добавлен.", reply_markup=note_add_menu())
        return NOTE_ADD

    # Обработка кнопок
    if text == "➕ Фото":
        await update.message.reply_text("Пришлите фото для заметки.", reply_markup=None)
        return NOTE_ADD
    if text == "✏️ Текст":
        await update.message.reply_text("Пришлите текст заметки.", reply_markup=None)
        return NOTE_ADD

    return NOTE_ADD

async def note_edit_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if txt.lower() == "отмена":
        return await notes_menu_handler(update, context)
    note_id = context.user_data.get("note_id")
    if not note_id:
        return await notes_menu_handler(update, context)
    session = Session()
    note = session.get(Note, note_id)
    if note:
        note.text = txt
        note.updated_at = datetime.utcnow()
        session.commit()
        session.close()
        await update.message.reply_text("Изменено.")
    return await notes_menu_handler(update, context)