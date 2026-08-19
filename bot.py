import os
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# SOZLAMALAR
# =========================

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL = "@OPENBUJETRASMI"

try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
except ValueError:
    ADMIN_ID = 0

logging.basicConfig(level=logging.INFO)

# =========================
# MA'LUMOTLAR
# =========================

contest_active = False

# username -> ovozlar
participants = {}

# (ovoz beruvchi Telegram ID, nomzod username)
votes = set()

# Botga kirgan foydalanuvchilar
users = set()

# Konkurs xabari
contest_chat_id = None
contest_message_id = None


# =========================
# NATIJALAR
# =========================

def results_text():
    if not participants:
        return "Hozircha hech kim konkursga qo‘shilmagan."

    ranking = sorted(
        participants.items(),
        key=lambda x: x[1],
        reverse=True
    )

    lines = []

    for i, (username, count) in enumerate(ranking, 1):

        if i == 1:
            medal = "🥇"
        elif i == 2:
            medal = "🥈"
        elif i == 3:
            medal = "🥉"
        else:
            medal = f"{i}."

        lines.append(
            f"{medal} @{username} — {count}"
        )

    return "\n".join(lines)


# =========================
# KONKURS KLAVIATURASI
# =========================

def contest_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ KONKURSGA QO‘SHILISH",
                callback_data="join"
            )
        ],
        [
            InlineKeyboardButton(
                "📊 KONKURS NATIJALARI",
                callback_data="results"
            )
        ]
    ])


# =========================
# KONKURS MATNI
# =========================

def contest_text():
    return (
        "🏆 BATL BOSHLANDI!\n\n"
        "❗️Konkurs shartlari — shu kanalga obuna bo‘lish "
        "va do‘stlaringizdan sizga ovoz berishini so‘rash.\n\n"
        "⚠️ Ovoz berish uchun kanalga obuna bo‘lish shart.\n\n"
        "🎁 Konkurs yutuqlari: 🤫\n\n"
        "📊 KONKURS NATIJALARI\n\n"
        f"{results_text()}"
    )


# =========================
# KONKURS XABARINI YANGILASH
# =========================

async def refresh_contest(context):

    if not contest_chat_id or not contest_message_id:
        return

    try:
        await context.bot.edit_message_text(
            chat_id=contest_chat_id,
            message_id=contest_message_id,
            text=contest_text(),
            reply_markup=contest_keyboard()
        )

    except Exception as error:
        logging.error(
            "Konkurs xabarini yangilash xatosi: %s",
            error
        )


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if not user:
        return

    users.add(user.id)

    # Do'st nomzodga ovoz berish uchun kelgan
    if context.args:

        argument = context.args[0]

        if argument.startswith("vote_"):

            target = argument[5:].lower()

            if not contest_active:
                await update.message.reply_text(
                    "⛔ Hozircha faol konkurs yo‘q."
                )
                return

            if target not in participants:
                await update.message.reply_text(
                    "❌ Bu nomzod konkursda topilmadi."
                )
                return

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "📢 KANALGA OBUNA BO‘LISH",
                        url=f"https://t.me/{CHANNEL.replace('@', '')}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🗳 OVOZ BERISH",
                        callback_data=f"vote:{target}"
                    )
                ]
            ])

            await update.message.reply_text(
                "🏆 OVOZ BERISH\n\n"
                f"👤 Nomzod: @{target}\n\n"
                "1️⃣ Kanalga obuna bo‘ling.\n"
                "2️⃣ Keyin 🗳 OVOZ BERISH tugmasini bosing.",
                reply_markup=keyboard
            )

            return

    # Oddiy start
    await update.message.reply_text(
        "✅ Xush kelibsiz!\n\n"
        "🏆 Ovoz Battle Pro\n\n"
        "Konkursda qatnashish yoki ovoz berish uchun "
        "kerakli tugmani tanlang.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🏆 KONKURS",
                    callback_data="menu_contest"
                )
            ]
        ])
    )


# =========================
# KONKURSGA QO‘SHILISH
# =========================

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = query.from_user

    users.add(user.id)

    if not contest_active:
        await query.answer(
            "⛔ Hozircha faol konkurs yo‘q.",
            show_alert=True
        )
        return

    if not user.username:
        await query.answer(
            "❗ Telegram username qo‘ying.",
            show_alert=True
        )
        return

    username = user.username.lower()

    # Yangi nomzod
    if username not in participants:
        participants[username] = 0

    # Bot username
    me = await context.bot.get_me()

    # Yashirin referral link
    vote_link = (
        f"https://t.me/{me.username}"
        f"?start=vote_{username}"
    )

    # Telegram share tugmasi
    share_link = (
        "https://t.me/share/url"
        f"?url={vote_link}"
        f"&text=🏆%20Menga%20ovoz%20bering!"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📤 DO‘STLARNI TAKLIF QILISH",
                url=share_link
            )
        ],
        [
            InlineKeyboardButton(
                "📊 NATIJALAR",
                callback_data="results"
            )
        ]
    ])

    await query.edit_message_text(
        "🎉 KONKURSGA QO‘SHILDINGIZ!\n\n"
        f"👤 @{username}\n"
        f"🗳 Sizda: {participants[username]} ta ovoz\n\n"
        "📤 Pastdagi tugma orqali do‘stlaringizni "
        "taklif qiling.\n\n"
        "Do‘stlaringiz botga kirib, kanalga obuna bo‘lib "
        "sizga ovoz berishlari mumkin.",
        reply_markup=keyboard
    )

    await refresh_contest(context)


# =========================
# NATIJALAR
# =========================

async def results(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🏆 KONKURS NATIJALARI\n\n"
        f"{results_text()}",
        reply_markup=contest_keyboard()
    )


# =========================
# OVOZ BERISH
# =========================

async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    voter = query.from_user

    target = query.data.split(":", 1)[1].lower()

    if not contest_active:
        await query.answer(
            "⛔ Konkurs tugagan.",
            show_alert=True
        )
        return

    if target not in participants:
        await query.answer(
            "❌ Nomzod topilmadi.",
            show_alert=True
        )
        return

    # Kanalga obunani tekshirish
    try:

        member = await context.bot.get_chat_member(
            chat_id=CHANNEL,
            user_id=voter.id
        )

        if member.status in ("left", "kicked"):

            await query.answer(
                "❗ Avval kanalga obuna bo‘ling!",
                show_alert=True
            )

            return

    except Exception as error:

        logging.error(
            "Kanal obunasini tekshirish xatosi: %s",
            error
        )

        await query.answer(
            "⚠️ Kanal obunasini tekshirib bo‘lmadi.",
            show_alert=True
        )

        return

    # Bir odam bir nomzodga bir marta
    vote_key = (
        voter.id,
        target
    )

    if vote_key in votes:

        await query.answer(
            "⛔ Siz bu nomzodga allaqachon ovoz bergansiz.",
            show_alert=True
        )

        return

    # Ovoz qo‘shish
    votes.add(vote_key)

    participants[target] += 1

    await query.answer(
        "✅ Ovoz qabul qilindi!"
    )

    await query.edit_message_text(
        "✅ OVOZ QABUL QILINDI!\n\n"
        f"🏆 Nomzod: @{target}\n"
        f"🗳 Jami ovoz: {participants[target]}"
    )

    # Kanal konkurs xabarini yangilash
    await refresh_contest(context)


# =========================
# #KONKURS
# =========================

async def konkurs_post(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    global contest_active
    global contest_chat_id
    global contest_message_id

    post = update.channel_post

    if not post:
        return

    # Faqat kerakli kanal
    if post.chat.username:

        current_channel = (
            "@" + post.chat.username
        )

        if current_channel.lower() != CHANNEL.lower():
            return

    text = post.text or post.caption or ""

    if text.strip().lower() != "#konkurs":
        return

    # Yangi konkurs
    contest_active = True

    participants.clear()
    votes.clear()

    sent = await context.bot.send_message(
        chat_id=post.chat_id,
        text=contest_text(),
        reply_markup=contest_keyboard()
    )

    contest_chat_id = sent.chat_id
    contest_message_id = sent.message_id


# =========================
# TOP
# =========================

async def top(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🏆 TOP NATIJALAR\n\n"
        f"{results_text()}"
    )


# =========================
# FINISH
# =========================

async def finish(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    global contest_active

    if update.effective_user.id != ADMIN_ID:
        return

    contest_active = False

    await update.message.reply_text(
        "🏆 KONKURS YAKUNLANDI!\n\n"
        f"{results_text()}"
    )


# =========================
# STATS
# =========================

async def stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        "📊 BOT STATISTIKASI\n\n"
        f"👥 Foydalanuvchilar: {len(users)}\n"
        f"🏆 Nomzodlar: {len(participants)}\n"
        f"🗳 Ovozlar: {len(votes)}\n\n"
        f"🔥 Konkurs: "
        f"{'FAOL 🟢' if contest_active else 'YOPIQ 🔴'}"
    )


# =========================
# MAIN
# =========================

def main():

    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN topilmadi!"
        )

    if ADMIN_ID == 0:
        raise RuntimeError(
            "ADMIN_ID sozlanmagan!"
        )

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    # Commands
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "top",
            top
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
            "stats",
            stats
        )
    )

    # Konkursga qo‘shilish
    app.add_handler(
        CallbackQueryHandler(
            join,
            pattern=r"^join$"
        )
    )

    # Natijalar
    app.add_handler(
        CallbackQueryHandler(
            results,
            pattern=r"^results$"
        )
    )

    # Ovoz
    app.add_handler(
        CallbackQueryHandler(
            vote,
            pattern=r"^vote:"
        )
    )

    # Kanalda #konkurs
    app.add_handler(
        MessageHandler(
            filters.ChatType.CHANNEL
            & filters.Regex(
                r"(?i)^#konkurs$"
            ),
            konkurs_post
        )
    )

    print(
        "🏆 Ovoz Battle Pro ishga tushdi!"
    )

    app.run_polling()


if __name__ == "__main__":
    main()
