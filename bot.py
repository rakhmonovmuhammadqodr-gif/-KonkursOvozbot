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

logger = logging.getLogger(__name__)


# =========================================================
# DATA
# =========================================================

DEFAULT_DATA = {
    "contest_active": False,
    "contest_text": "",
    "contest_message_id": None,
    "participants": {},
    "votes": {},
    "users": []
}

data = DEFAULT_DATA.copy()


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )
    except Exception as e:
        logger.error(f"DATA SAQLASH XATOSI: {e}")


def load_data():
    global data

    try:
        if not os.path.exists(DATA_FILE):
            data = DEFAULT_DATA.copy()
            save_data()
            return

        with open(DATA_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        if not isinstance(loaded, dict):
            data = DEFAULT_DATA.copy()
            save_data()
            return

        data = DEFAULT_DATA.copy()
        data.update(loaded)

        if not isinstance(data.get("participants"), dict):
            data["participants"] = {}

        if not isinstance(data.get("votes"), dict):
            data["votes"] = {}

        if not isinstance(data.get("users"), list):
            data["users"] = []

    except Exception as e:
        logger.error(f"DATA OCHISH XATOSI: {e}")
        data = DEFAULT_DATA.copy()
        save_data()


# =========================================================
# FOYDALANUVCHI
# =========================================================

def add_user(user_id: int):
    if user_id not in data["users"]:
        data["users"].append(user_id)
        save_data()


# =========================================================
# OBUNA TEKSHIRISH
# =========================================================

async def is_subscribed(bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(
            CHANNEL,
            user_id
        )

        return member.status in (
            "member",
            "administrator",
            "creator"
        )

    except Exception as e:
        logger.error(
            f"Obuna tekshirish xatosi: {e}"
        )
        return False


def sponsor_keyboard():
    channel_username = CHANNEL.replace("@", "")

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📢 Homiy kanal",
                url=f"https://t.me/{channel_username}"
            )
        ],
        [
            InlineKeyboardButton(
                "✅ Obunani tekshirish",
                callback_data="check_subscription"
            )
        ]
    ])


async def show_subscription_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = (
        "🏆 <b>KonkursOvozbot</b>\n\n"
        "Ovoz berish uchun avval homiy kanalga "
        "obuna bo‘ling 👇"
    )

    if update.callback_query:
        await update.callback_query.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=sponsor_keyboard()
        )
    elif update.message:
        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=sponsor_keyboard()
        )


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_user:
        return

    user = update.effective_user

    add_user(user.id)

    # /start vote_123456
    if context.args:

        argument = context.args[0]

        if argument.startswith("vote_"):

            try:
                participant_id = int(
                    argument.replace("vote_", "", 1)
                )

                await process_referral_vote(
                    update,
                    context,
                    participant_id
                )

                return

            except ValueError:
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

    if update.message:
        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# =========================================================
# KONKURS TUGMALARI
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


# =========================================================
# KONKURS MATNI
# =========================================================

def build_contest_text():

    text = data.get("contest_text", "")

    if not text:
        text = (
            "🏆 <b>BATL BOSHLANDI</b> 🥳\n\n"
            "❗ <b>Konkurs shartlari:</b>\n"
            "Kanalga obuna bo‘ling va do‘stlaringizni "
            "sizga ovoz berishga taklif qiling.\n\n"
            "🎁 <b>Konkurs yutuqlari</b>\n"
            "Hozircha sir 🤫\n\n"
            "➕ <b>Konkursga qo‘shilish uchun</b>\n"
            "quyidagi tugmani bosing 👇"
        )

    participants = data.get("participants", {})

    if not participants:

        text += (
            "\n\n👥 <b>Qatnashchilar:</b>\n"
            "Hozircha hech kim qo‘shilmagan."
        )

        return text

    text += "\n\n👥 <b>Qatnashchilar:</b>\n\n"

    sorted_people = sorted(
        participants.items(),
        key=lambda item: item[1].get("votes", 0),
        reverse=True
    )

    for participant_id, person in sorted_people:

        username = person.get("username", "")
        name = person.get("name", "Noma'lum")
        votes = person.get("votes", 0)

        if username:
            display_name = f"@{username}"
        else:
            display_name = name

        text += (
            f"👤 <b>{display_name}</b> — "
            f"{votes} 📦\n"
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

    if not data.get("contest_active", False):

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

    if not update.effective_user:
        return

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "❌ Bu buyruq faqat admin uchun."
        )

        return

    data["contest_active"] = True
    data["participants"] = {}
    data["votes"] = {}
    data["contest_message_id"] = None

    if context.args:

        data["contest_text"] = " ".join(
            context.args
        )

    else:

        data["contest_text"] = (
            "🏆 <b>BATL BOSHLANDI</b> 🥳\n\n"
            "❗ <b>Konkurs shartlari:</b>\n"
            "Kanalga obuna bo‘ling va "
            "do‘stlaringizni sizga ovoz berishga "
            "taklif qiling.\n\n"
            "🎁 <b>Konkurs yutuqlari</b>\n"
            "Hozircha sir 🤫\n\n"
            "➕ <b>Konkursga qo‘shilish uchun</b>\n"
            "quyidagi tugmani bosing 👇"
        )

    save_data()

    # Admin chatida ham ko‘rsatadi
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

    if not data.get("contest_active", False):

        await query.message.reply_text(
            "❌ Konkurs tugagan."
        )

        return

    subscribed = await is_subscribed(
        context.bot,
        user.id
    )

    if not subscribed:

        await show_subscription_message(
            update,
            context
        )

        return

    user_id = str(user.id)

    bot_info = await context.bot.get_me()

    link = (
        f"https://t.me/{bot_info.username}"
        f"?start=vote_{user.id}"
    )

    # Oldindan qo‘shilgan
    if user_id in data["participants"]:

        participant = data["participants"][user_id]

        await query.message.reply_text(
            "✅ <b>Siz allaqachon konkursdasiz!</b>\n\n"
            f"👤 Ism: <b>{participant.get('name', user.full_name)}</b>\n"
            f"📦 Ovozlar: <b>{participant.get('votes', 0)}</b>\n\n"
            "🔗 <b>Sizning ovoz linkingiz:</b>\n"
            f"{link}\n\n"
            "👥 Shu linkni do‘stlaringizga yuboring.",
            parse_mode="HTML"
        )

        return

    # Yangi qatnashchi
    data["participants"][user_id] = {
        "name": user.full_name,
        "username": user.username or "",
        "votes": 0
    }

    save_data()

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


# =========================================================
# REFERRAL OVOZ
# =========================================================

async def process_referral_vote(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    participant_id: int
):

    voter = update.effective_user

    if not data.get("contest_active", False):

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

    # Ovoz beruvchi kanalga obuna bo‘lishi kerak
    subscribed = await is_subscribed(
        context.bot,
        voter.id
    )

    if not subscribed:

        await show_subscription_message(
            update,
            context
        )

        return

    # O‘ziga ovoz
    if str(voter.id) == participant_id:

        await update.message.reply_text(
            "❌ O‘zingizga o‘zingiz ovoz bera olmaysiz."
        )

        return

    # Bitta odam bitta qatnashchiga faqat bir marta
    vote_key = f"{voter.id}_{participant_id}"

    if vote_key in data["votes"]:

        await update.message.reply_text(
            "⚠️ Siz bu qatnashchiga "
            "allaqachon ovoz bergansiz."
        )

        return

    data["votes"][vote_key] = True

    data["participants"][participant_id]["votes"] = (
        data["participants"][participant_id].get("votes", 0) + 1
    )

    save_data()

    participant = data["participants"][participant_id]

    username = participant.get("username", "")
    name = participant.get("name", "Noma'lum")

    if username:
        display_name = f"@{username}"
    else:
        display_name = name

    await update.message.reply_text(
        "✅ <b>Ovozingiz qabul qilindi!</b>\n\n"
        f"👤 Qatnashchi: <b>{display_name}</b>\n"
        f"📦 Jami ovoz: <b>{participant['votes']}</b>",
        parse_mode="HTML"
    )


# =========================================================
# OBUNANI QAYTA TEKSHIRISH
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

    participants = data.get("participants", {})

    if not participants:

        await query.message.reply_text(
            "📊 Hozircha natijalar yo‘q."
        )

        return

    sorted_people = sorted(
        participants.items(),
        key=lambda item: item[1].get("votes", 0),
        reverse=True
    )

    text = "📊 <b>KONKURS NATIJALARI</b>\n\n"

    medals = {
        1: "🥇",
        2: "🥈",
        3: "🥉"
    }

    for index, (participant_id, person) in enumerate(
        sorted_people,
        start=1
    ):

        username = person.get("username", "")
        name = person.get("name", "Noma'lum")
        votes = person.get("votes", 0)

        if username:
            display_name = f"@{username}"
        else:
            display_name = name

        medal = medals.get(
            index,
            f"{index}."
        )

        text += (
            f"{medal} <b>{display_name}</b> — "
            f"{votes} 📦\n"
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

    if not update.effective_user:
        return

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "❌ Bu buyruq faqat admin uchun."
        )

        return

    data["contest_active"] = False
    save_data()

    participants = data.get("participants", {})

    if participants:

        sorted_people = sorted(
            participants.items(),
            key=lambda item: item[1].get("votes", 0),
            reverse=True
        )

        text = "🏁 <b>KONKURS YAKUNLANDI!</b>\n\n"

        for index, (participant_id, person) in enumerate(
            sorted_people[:10],
            start=1
        ):

            username = person.get("username", "")
            name = person.get("name", "Noma'lum")
            votes = person.get("votes", 0)

            if username:
                display_name = f"@{username}"
            else:
                display_name = name

            text += (
                f"{index}. {display_name} — "
                f"{votes} 📦\n"
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
# ADMIN: QATNASHCHILAR
# =========================================================

async def participants_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_user:
        return

    if update.effective_user.id != ADMIN_ID:
        return

    people = data.get("participants", {})

    if not people:

        await update.message.reply_text(
            "👥 Qatnashchilar yo‘q."
        )

        return

    text = "👥 <b>QATNASHCHILAR</b>\n\n"

    sorted_people = sorted(
        people.items(),
        key=lambda item: item[1].get("votes", 0),
        reverse=True
    )

    for index, (participant_id, person) in enumerate(
        sorted_people,
        start=1
    ):

        username = person.get("username", "")
        name = person.get("name", "Noma'lum")
        votes = person.get("votes", 0)

        if username:
            display_name = f"@{username}"
        else:
            display_name = name

        text += (
            f"{index}. 👤 {display_name}\n"
            f"📦 {votes} ovoz\n\n"
        )

    await update.message.reply_text(
        text,
        parse_mode="HTML"
    )


# =========================================================
# ADMIN: STATISTIKA
# =========================================================

async def stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_user:
        return

    if update.effective_user.id != ADMIN_ID:
        return

    users_count = len(data.get("users", []))
    participants_count = len(
        data.get("participants", {})
    )
    votes_count = len(
        data.get("votes", {})
    )

    text = (
        "📊 <b>BOT STATISTIKASI</b>\n\n"
        f"👥 Botdan foydalanganlar: <b>{users_count}</b>\n"
        f"🏆 Qatnashchilar: <b>{participants_count}</b>\n"
        f"📦 Berilgan ovozlar: <b>{votes_count}</b>\n"
        f"🔴 Konkurs: "
        f"<b>{'Faol' if data.get('contest_active') else 'Yopiq'}</b>"
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

    logger.error(
        "Bot xatosi:",
        exc_info=context.error
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN GitHub Secrets'da topilmadi!"
        )

    if ADMIN_ID == 0:
        raise RuntimeError(
            "ADMIN_ID GitHub Secrets'da noto'g'ri!"
        )

    load_data()

    app = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    # -------------------------
    # COMMANDS
    # -------------------------

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

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

    app.add_handler(
        CommandHandler(
            "stats",
            stats
        )
    )

    # -------------------------
    # BUTTONS
    # -------------------------

    app.add_handler(
        CallbackQueryHandler(
            open_contest,
            pattern=r"^open_contest$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            join_contest,
            pattern=r"^join_contest$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            check_subscription,
            pattern=r"^check_subscription$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            results,
            pattern=r"^results$"
        )
    )

    # -------------------------
    # ERROR
    # -------------------------

    app.add_error_handler(
        error_handler
    )

    print(
        "🤖 Ovoz Battle Pro ishga tushdi!"
    )

    print(
        "✅ Bot polling rejimida ishlayapti..."
    )

    # MUHIM:
    # Bu qator botni doimiy ishlatadi.
    # GitHub Actions'da run-bot "6 soat" deb turishi
    # shuning uchun normal.
    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
