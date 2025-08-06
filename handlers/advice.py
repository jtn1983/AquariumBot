# handlers/advice.py

from telegram import Update
from telegram.ext import ContextTypes
from db import Session, Measurement
from parameters import PARAMETERS
from parameter_info import PARAMETER_INFO
from handlers.measurement import TYPE_MAP
from sqlalchemy import func

async def advice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    aquarium_id = context.user_data["aquarium_id"]
    aq_type_ru = context.user_data.get("aq_type", "морской")
    aq_type = TYPE_MAP.get(aq_type_ru, "marine")

    session = Session()
    subquery = (
        session.query(
            Measurement.param,
            func.max(Measurement.created_at).label("max_created_at")
        )
        .filter(Measurement.aquarium_id == aquarium_id)
        .group_by(Measurement.param)
    ).subquery()

    last_measures = (
        session.query(Measurement.param, Measurement.value, Measurement.created_at)
        .join(subquery, (Measurement.param == subquery.c.param) & (Measurement.created_at == subquery.c.max_created_at))
        .all()
    )

    tips = []
    for param, value, created_at in last_measures:
        norm = PARAMETERS[param][aq_type]
        info = PARAMETER_INFO[param]
        tip_text = ""

        if value < norm["min"]:
            danger = info.get("danger_low", {}).get(aq_type) or info.get("danger_low", {}).get("common", "")
            correction = info.get("correction_low", {}).get(aq_type) or info.get("correction_low", {}).get("common", "")
            tip_text = (danger + "\n" + correction).strip()
        elif value > norm["max"]:
            danger = info.get("danger_high", {}).get(aq_type) or info.get("danger_high", {}).get("common", "")
            correction = info.get("correction_high", {}).get(aq_type) or info.get("correction_high", {}).get("common", "")
            tip_text = (danger + "\n" + correction).strip()

        if tip_text:
            tips.append(
                f"<b>{param}</b>: {value} (норма: {norm['min']}–{norm['max']} {norm['unit']}, измерено: {created_at.strftime('%d.%m.%Y')})\n{tip_text}"
            )

    if not tips:
        await update.message.reply_text("🎉 Все показатели в норме! Продолжайте в том же духе.")
    else:
        await update.message.reply_text("⚠️ Найдены отклонения и рекомендации:\n\n" + "\n\n".join(tips), parse_mode="HTML")