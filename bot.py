import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# =========================================================
# SOZLAMALAR
# =========================================================

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL = "@OPENBUJETRASMI"
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

DATA_FILE = "data.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# =========================================================
# DATA
# =========================================================

data = {
    "contest_active": False,
    "contest_text": "",
    "participants": {},
    "votes": {},
    "users": []
}


def load_data():
    global data

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        save_data()


def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if user.id not in data["users"]:
        data["users"].append(user.id)
        save_data()

    # /start=vote_123
    if context.args:

        arg = context.args[0]

        if arg.startswith("vote_"):
            try:
                participant_id = int(
                    arg.replace("vote_", "")
                )

                await process_referral_vote(
                    update,
                    context,
                    participant_id
                )
                return

            except Exception:
                pass

    keyboard = [
        [
            InlineKeyboardButton(
                "🏆 KONKURS",
                callback_data="open_contest"
            )
        ]
    ]

    text = (
        "🏆 <b>Ovoz Battle Pro</b>\n\n"
        "Konkursda qatnashish yoki ovoz berish "
        "uchun kerakli tugmani tanlang."
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================================================
# SUBSCRIPTION
# =========================================================

async def is_subscribed(bot, user_id):

    try:

        member = await bot.get_chat_member(
            CHANNEL,
            user_id
        )

        return member.status in [
            "member",
            "administrator",
            "creator"
        ]

    except Exception as e:

        logging.error(
            f"Obuna tekshirish xatosi: {e}"
        )

        return False


# =========================================================
# HOMIY KANAL
# =========================================================

def sponsor_keyboard():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📢 Homiy kanal",
                url=f"https://t.me/{CHANNEL.replace('@', '')}"
            )
        ],
        [
            InlineKeyboardButton(
                "✅ Obunani tekshirish",
                callback_data="check_subscription"
            )
        ]
    ])


async def subscription_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = (
        "🏆 <b>KonkursOvozbot</b>\n\n"
        "Ovoz berish uchun homiy kanalga "
        "obuna bo‘ling."
    )

    if update.callback_query:

        await update.callback_query.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=sponsor_keyboard()
        )

    else:

        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=sponsor_keyboard()
        )


# =========================================================
# KONKURS MATNI
# =========================================================

def contest_keyboard():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🏆 KONKURSGA QO‘SHILISH ➕",
                callback_data="join_contest"
            )
        ],
        [
            InlineKeyboardButton(
                "📊 Natijalar",
                callback_data="results"
            )
        ]
    ])


def build_contest_text():

    participants = data["participants"]

    text = data["contest_text"]

    if not text:
        text = (
            "🏆 <b>BATL Boshlandi</b> 🥳\n\n"
            "❗ Konkurs shartlari:\n"
            "Kanalga obuna bo‘lish va do‘stlaringiz "
            "sizga ovoz berishini so‘rashdan iborat.\n\n"
            "🎁 <b>Konkursga qo‘yilgan yutuqlar</b>\n"
            "Hozircha sir 🤫\n\n"
            "➕ <b>Konkursga qo‘shilish uchun</b>\n"
            "quyidagi tugmani bosing 👇\n\n"
        )

    text += "\n\n"

    if participants:

        text += "👥 <b>Qatnashchilar:</b>\n\n"

        sorted_people = sorted(
            participants.items(),
            key=lambda x: x[1]["votes"],
            reverse=True
        )

        for pid, person in sorted_people:

            username = person["username"]

            if username:
                name = f"@{username}"
            else:
                name = person["name"]

            text += (
                f"👤 <b>{name}</b> — "
                f"{person['votes']} 📦\n"
            )

    else:

        text += (
            "👥 Hozircha hech kim "
            "konkursga qo‘shilmagan."
        )

    return text


# =========================================================
# KONKURSNI OCHISH
# =========================================================

async def open_contest(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query
    await query.answer()

    if not data["contest_active"]:

        await query.message.reply_text(
            "❌ Hozircha faol konkurs yo‘q."
        )

        return

    await query.message.reply_text(
        build_contest_text(),
        parse_mode="HTML",
        reply_markup=contest_keyboard()
    )


# =========================================================
# ADMIN: KONKURS BOSHLASH
# =========================================================

async def konkurs(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "❌ Bu buyruq faqat admin uchun."
        )

        return

    data["contest_active"] = True
    data["participants"] = {}
    data["votes"] = {}

    if context.args:

        data["contest_text"] = " ".join(
            context.args
        )

    else:

        data["contest_text"] = (
            "🏆 <b>BATL Boshlandi</b> 🥳\n\n"
            "❗ <b>Konkurs shartlari</b>\n"
            "Kanalga obuna bo‘lish va "
            "do‘stlaringiz sizga ovoz berishini "
            "so‘rashdan iborat.\n\n"
            "🎁 <b>Konkursga qo‘yilgan yutuqlar</b>\n"
            "Hozircha sir 🤫\n\n"
            "➕ <b>Konkursga qo‘shilish uchun</b>\n"
            "quyidagi tugmani bosing 👇"
        )

    save_data()

    await update.message.reply_text(
        build_contest_text(),
        parse_mode="HTML",
        reply_markup=contest_keyboard()
    )


# =========================================================
# KONKURSGA QO‘SHILISH
# =========================================================

async def join_contest(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query
    await query.answer()

    user = query.from_user

    if not data["contest_active"]:

        await query.message.reply_text(
            "❌ Konkurs tugagan."
        )

        return

    subscribed = await is_subscribed(
        context.bot,
        user.id
    )

    if not subscribed:

        await subscription_message(
            update,
            context
        )

        return

    user_id = str(user.id)

    if user_id in data["participants"]:

        participant = data["participants"][user_id]

        bot_info = await context.bot.get_me()

        link = (
            f"https://t.me/{bot_info.username}"
            f"?start=vote_{user.id}"
        )

        await query.message.reply_text(
            "✅ Siz allaqachon konkursdasiz!\n\n"
            "🔗 <b>Sizning ovoz linkingiz:</b>\n"
            f"{link}\n\n"
            "👥 Shu linkni do‘stlaringizga yuboring.",
            parse_mode="HTML"
        )

        return

    username = user.username or ""

    data["participants"][user_id] = {
        "name": user.full_name,
        "username": username,
        "votes": 0
    }

    save_data()

    bot_info = await context.bot.get_me()

    link = (
        f"https://t.me/{bot_info.username}"
        f"?start=vote_{user.id}"
    )

    await query.message.reply_text(
        "🎉 <b>Konkursga muvaffaqiyatli qo‘shildingiz!</b>\n\n"
        f"👤 Ism: <b>{user.full_name}</b>\n"
        "📦 Ovozlar: <b>0</b>\n\n"
        "🔗 <b>Sizning shaxsiy ovoz linkingiz:</b>\n"
        f"{link}\n\n"
        "👥 Shu linkni do‘stlaringizga yuboring "
        "va sizga ovoz berishlarini so‘rang.",
        parse_mode="HTML"
    )

    # Kanalga yangilangan konkurs xabarini yuborish
    await query.message.reply_text(
        build_contest_text(),
        parse_mode="HTML",
        reply_markup=contest_keyboard()
    )


# =========================================================
# REFERRAL OVOZ
# =========================================================

async def process_referral_vote(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    participant_id: int
):

    voter = update.effective_user

    if not data["contest_active"]:

        await update.message.reply_text(
            "❌ Hozircha faol konkurs yo‘q."
        )

        return

    participant_id = str(participant_id)

    if participant_id not in data["participants"]:

        await update.message.reply_text(
            "❌ Bu qatnashchi topilmadi."
        )

        return

    subscribed = await is_subscribed(
        context.bot,
        voter.id
    )

    if not subscribed:

        await subscription_message(
            update,
            context
        )

        return

    if str(voter.id) == participant_id:

        await update.message.reply_text(
            "❌ O‘zingizga o‘zingiz ovoz bera olmaysiz."
        )

        return

    vote_key = (
        f"{voter.id}_{participant_id}"
    )

    if vote_key in data["votes"]:

        await update.message.reply_text(
            "⚠️ Siz bu qatnashchiga "
            "allaqachon ovoz bergansiz."
        )

        return

    data["votes"][vote_key] = True

    data["participants"][participant_id]["votes"] += 1

    save_data()

    participant = data["participants"][participant_id]

    username = participant["username"]

    if username:
        name = f"@{username}"
    else:
        name = participant["name"]

    await update.message.reply_text(
        "✅ <b>Ovozingiz qabul qilindi!</b>\n\n"
        f"👤 Qatnashchi: <b>{name}</b>\n"
        f"📦 Jami ovoz: <b>{participant['votes']}</b>\n\n"
        "🏆 Konkursda yana boshqa "
        "qatnashchilarga ham ovoz berishingiz mumkin.",
        parse_mode="HTML"
    )


# =========================================================
# OBUNANI TEKSHIRISH
# =========================================================

async def check_subscription(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    subscribed = await is_subscribed(
        context.bot,
        query.from_user.id
    )

    if not subscribed:

        await query.message.reply_text(
            "❌ Siz hali homiy kanalga obuna bo‘lmagansiz."
        )

        return

    await query.message.reply_text(
        "✅ <b>Obuna tasdiqlandi!</b>\n\n"
        "Endi konkursda qatnashishingiz mumkin.",
        parse_mode="HTML",
        reply_markup=contest_keyboard()
    )


# =========================================================
# NATIJALAR
# =========================================================

async def results(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    participants = data["participants"]

    if not participants:

        await query.message.reply_text(
            "📊 Hozircha natijalar yo‘q."
        )

        return

    sorted_people = sorted(
        participants.items(),
        key=lambda x: x[1]["votes"],
        reverse=True
    )

    text = "📊 <b>KONKURS NATIJALARI</b>\n\n"

    medals = {
        1: "🥇",
        2: "🥈",
        3: "🥉"
    }

    for index, (pid, person) in enumerate(
        sorted_people,
        start=1
    ):

        username = person["username"]

        if username:
            name = f"@{username}"
        else:
            name = person["name"]

        medal = medals.get(
            index,
            f"{index}."
        )

        text += (
            f"{medal} <b>{name}</b> — "
            f"{person['votes']} 📦\n"
        )

    await query.message.reply_text(
        text,
        parse_mode="HTML"
    )


# =========================================================
# ADMIN: KONKURSNI TUGATISH
# =========================================================

async def finish(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:

        return

    data["contest_active"] = False

    save_data()

    participants = data["participants"]

    if participants:

        sorted_people = sorted(
            participants.items(),
            key=lambda x: x[1]["votes"],
            reverse=True
        )

        text = "🏁 <b>KONKURS YAKUNLANDI!</b>\n\n"

        for index, (pid, person) in enumerate(
            sorted_people[:10],
            start=1
        ):

            username = person["username"]

            if username:
                name = f"@{username}"
            else:
                name = person["name"]

            text += (
                f"{index}. {name} — "
                f"{person['votes']} 📦\n"
            )

    else:

        text = (
            "🏁 <b>Konkurs yakunlandi!</b>\n\n"
            "Hozircha qatnashchilar bo‘lmagan."
        )

    await update.message.reply_text(
        text,
        parse_mode="HTML"
    )


# =========================================================
# ADMIN: KONKURSDAGI ODAMLAR
# =========================================================

async def participants_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:

        return

    people = data["participants"]

    if not people:

        await update.message.reply_text(
            "👥 Qatnashchilar yo‘q."
        )

        return

    text = "👥 <b>QATNASHCHILAR</b>\n\n"

    for pid, person in people.items():

        username = person["username"]

        if username:
            name = f"@{username}"
        else:
            name = person["name"]

        text += (
            f"👤 {name}\n"
            f"📦 {person['votes']} ovoz\n\n"
        )

    await update.message.reply_text(
        text,
        parse_mode="HTML"
    )


# =========================================================
# ERROR
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logging.error(
        "Xatolik:",
        exc_info=context.error
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if not TOKEN:

        raise ValueError(
            "BOT_TOKEN GitHub Secrets'da topilmadi!"
        )

    load_data()

    app = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    # START
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # ADMIN
    app.add_handler(
        CommandHandler(
            "konkurs",
            konkurs
        )
    )

    app.add_handler(
        CommandHandler(
            "finish",
            finish
        )
    )

    app.add_handler(
        CommandHandler(
            "participants",
            participants_command
        )
    )

    # BUTTONS

    app.add_handler(
        CallbackQueryHandler(
            open_contest,
            pattern="^open_contest$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            join_contest,
            pattern="^join_contest$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            check_subscription,
            pattern="^check_subscription$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            results,
            pattern="^results$"
        )
    )

    app.add_error_handler(
        error_handler
    )

    print(
        "🤖 Ovoz Battle Pro ishga tushdi!"
    )

    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
