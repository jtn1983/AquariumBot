# utils/keyboards.py

from telegram import ReplyKeyboardMarkup, KeyboardButton
from parameters import PARAMETERS
from types_map import TYPE_MAP

def main_menu():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("Мои аквариумы")],
         [KeyboardButton("Добавить аквариум")]],
        resize_keyboard=True
    )

def aquarium_menu():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("➕ Измерение"), KeyboardButton("📅 История")],
            [KeyboardButton("График"), KeyboardButton("🗒 Заметки"), KeyboardButton("Советы")], 
            [KeyboardButton("Настройка"), KeyboardButton("Обслуживание")], 
            [KeyboardButton("Вернуться")]
        ],
        resize_keyboard=True
    )

def setting_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("Изменить название"), KeyboardButton("Изменить литраж")],
            [KeyboardButton("Изменить тип"), KeyboardButton("Удалить аквариум")],
            [KeyboardButton("Назад")]
        ],
        resize_keyboard=True
    )

def param_keyboard(aq_type: str):
    marine = {"Соленость", "Кальций Ca", "Магний Mg"}
    kb = []
    aq_type_en = TYPE_MAP.get(aq_type, "marine")
    for p, n in PARAMETERS.items():
        if aq_type_en == "fresh" and p in marine:
            continue
        limits = n[aq_type_en]
        kb.append([KeyboardButton(f"{p} ({limits['min']}-{limits['max']} {limits['unit']})")])
    kb.append([KeyboardButton("Отмена")])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def cancel_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], resize_keyboard=True)

def notes_list_menu(has_prev: bool, has_next: bool):
    rows = [[KeyboardButton("➕ Добавить заметку")]]
    nav = []
    if has_prev:
        nav.append(KeyboardButton("⬅️ Предыдущие"))
    if has_next:
        nav.append(KeyboardButton("➡️ Следующие"))
    if nav:
        rows.append(nav)
    rows.append([KeyboardButton("↩️ Назад к аквариуму")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def note_view_menu(is_pinned: bool):
    pin_label = "📌 Открепить" if is_pinned else "📌 Закрепить"
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("✏️ Редактировать"), KeyboardButton("🗑 Удалить")],
            [KeyboardButton(pin_label), KeyboardButton("↩️ К списку заметок")],
        ],
        resize_keyboard=True
    )

def note_delete_confirm_menu():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("✅ Да, удалить")],
            [KeyboardButton("↩️ Отмена удаления")],
        ],
        resize_keyboard=True
    )


def note_add_menu():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("➕ Фото"), KeyboardButton("✏️ Текст")],
            [KeyboardButton("✅ Сохранить"), KeyboardButton("❌ Отмена")],
        ],
        resize_keyboard=True
    )
