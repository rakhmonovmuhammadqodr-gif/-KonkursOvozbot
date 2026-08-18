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

# GitHub Secret orqali beriladi:
# ADMIN_ID = Telegram ID raqaming
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# =========================
# MA'LUMOTLAR
# =========================

users = set()

participants = {}
votes = set()

contest_active = False


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user:
        return

    users.add(user.id)

    args = context.args

    # Do'stning ovoz linki orqali kirish
    if args and args[0].startswith("vote_"):

        target = args[0][5:]

        if not contest_active:
            await update.message.reply_text(
                "⛔ Hozircha faol ovozli konkurs yo‘q."
            )
            return

        keyboard = [
            [
                InlineKeyboardButton(
                    "📢 Kanalga obuna bo‘lish",
                    url=f"https://t.me/{CHANNEL.replace('@', '')}"
                )
            ],
            [
                InlineKeyboardButton(
                    "🗳 Ovoz berish",
                    callback_data=f"vote:{target}"
                )
            ],
        ]

        await update.message.reply_text(
            "🏆 OVOZ BATTLE\n\n"
            "❗ Ovoz berish uchun avval kanalga obuna bo‘ling.\n\n"
            "1️⃣ Kanalga obuna bo‘ling\n"
            "2️⃣ «🗳 Ovoz berish» tugmasini bosing",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        return

    # Oddiy start menyusi

    keyboard = [
        [
            InlineKeyboardButton(
                "🏆 Ovozli konkurs",
                callback_data="menu_voice"
            )
        ],
        [
            InlineKeyboardButton(
                "🎲 Random konkurs",
                callback_data="menu_random"
            ),
            InlineKeyboardButton(
                "⚔️ Like Battle",
                callback_data="menu_battle"
            ),
        ],
        [
            InlineKeyboardButton(
                "🔍 Konkursni tekshirish",
                callback_data="menu_check"
            )
        ],
    ]

    await update.message.reply_text(
        "✅ Xush kelibsiz!\n\n"
        "🤖 Bot ishga tushdi!\n\n"
        "📌 Kanalda:\n"
        "• #konkurs — ovozli konkurs\n"
        "• #random — random konkurs\n"
        "• #batl — like battle\n\n"
        "📝 Random konkurs formati:\n"
        "#random\n"
        "salom yangi konkurs boshlandi\n"
        "yutuq: NFT\n"
        "shartlari\n"
        "@kanal\n"
        "#soni 3\n\n"
        "🔍 Ovoz battle tekshirish:\n"
        "• Quyidagi knopkani bosing va konkurs xabarini forward qiling\n\n"
        "👇 Kerakli bo‘limni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# =========================
# MENU TUGMALARI
# =========================

async def menu_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_voice":
        await query.edit_message_text(
            "🏆 OVOZLI KONKURS\n\n"
            "Kanalga #konkurs yozilganda konkurs avtomatik boshlanadi.\n\n"
            "Har bir qatnashchiga shaxsiy ovoz linki beriladi.\n"
            "Do‘stlari shu link orqali ovoz beradi."
        )

    elif query.data == "menu_random":
        await query.edit_message_text(
            "🎲 RANDOM KONKURS\n\n"
            "Kanalda quyidagi formatdan foydalaning:\n\n"
            "#random\n"
            "Konkurs matni\n"
            "Yutuq\n"
            "Shartlari\n"
            "@kanal\n"
            "#soni 3"
        )

    elif query.data == "menu_battle":
        await query.edit_message_text(
            "⚔️ LIKE BATTLE\n\n"
            "Bu bo‘lim orqali like/reaction asosidagi "
            "battle funksiyasini ishlatish mumkin."
        )

    elif query.data == "menu_check":
        await query.edit_message_text(
            "🔍 KONKURSNI TEKSHIRISH\n\n"
            "Hozirgi versiyada ovozlar bot orqali nazorat qilinadi."
        )


# =========================
# KONKURS QO‘SHILISH
# =========================

async def join_contest(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    user = query.from_user

    users.add(user.id)

    if not contest_active:
        await query.edit_message_text(
            "⛔ Hozircha faol konkurs yo‘q."
        )
        return

    if not user.username:
        await query.edit_message_text(
            "❗ Telegram username'ingiz yo‘q.\n\n"
            "Avval Telegram Settings → Username orqali username qo‘ying."
        )
        return

    username = user.username.lower()

    if username not in participants:
        participants[username] = 0

    me = await context.bot.get_me()

    link = (
        f"https://t.me/{me.username}"
        f"?start=vote_{username}"
    )

    await query.edit_message_text(
        "🎉 Siz konkursga qo‘shildingiz!\n\n"
        f"👤 Ishtirokchi: @{username}\n"
        f"🗳 Ovozlar: {participants[username]}\n\n"
        "🔗 Sizning shaxsiy ovoz linkingiz:\n"
        f"{link}\n\n"
        "📢 Linkni do‘stlaringizga yuboring!"
    )


# =========================
# OVOZ BERISH
# =========================

async def vote(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query

    voter = query.from_user

    try:
        await query.answer()
    except Exception:
        pass

    if not contest_active:
        await query.answer(
            "⛔ Konkurs tugagan.",
            show_alert=True
        )
        return

    target = query.data.split(":", 1)[1].lower()

    if target not in participants:
        await query.answer(
            "❌ Bunday ishtirokchi topilmadi.",
            show_alert=True
        )
        return

    # Kanal obunasini tekshirish
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
            "Obunani tekshirishda xato: %s",
            error
        )

        await query.answer(
            "⚠️ Kanal obunasini tekshirib bo‘lmadi.",
            show_alert=True
        )
        return

    # Bir odam bir ishtirokchiga faqat bir marta
    vote_key = (voter.id, target)

    if vote_key in votes:
        await query.answer(
            "⛔ Siz allaqachon ovoz bergansiz.",
            show_alert=True
        )
        return

    votes.add(vote_key)

    participants[target] += 1

    await query.edit_message_text(
        "✅ OVOZ QABUL QILINDI!\n\n"
        f"🏆 Ishtirokchi: @{target}\n"
        f"🗳 Jami ovoz: {participants[target]}"
    )


# =========================
# #KONKURS
# =========================

async def konkurs_post(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    global contest_active

    post = update.channel_post

    if not post:
        return

    # Faqat bizning kanal
    if post.chat.username:
        channel_username = "@" + post.chat.username

        if channel_username.lower() != CHANNEL.lower():
            return

    text = post.text or post.caption or ""

    if text.strip().lower() != "#konkurs":
        return

    contest_active = True

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ Konkursga qo‘shilish",
                callback_data="join"
            )
        ]
    ]

    await context.bot.send_message(
        chat_id=post.chat_id,

        text=(
            "🏆 BATTLE BOSHLANDI! 🥳\n\n"
            "❗️Konkurs sharti — shu kanalga obuna bo‘lish "
            "va do‘stlaringizdan sizga ovoz berishini so‘rash.\n\n"
            "⚠️ Kanalga qo‘shilib ovoz berib, keyin chiqib "
            "ketilsa, ovoz keyingi tekshiruvda hisobdan chiqariladi.\n\n"
            "🎁 Konkurs yutuqlari hozircha sir 🤫\n\n"
            "➕ Konkursga qo‘shilish uchun quyidagi "
            "tugmani bosing 👇"
        ),

        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# TOP
# =========================

async def top(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not participants:
        await update.message.reply_text(
            "🏆 Hozircha hech qanday ovoz yo‘q."
        )
        return

    ranking = sorted(
        participants.items(),
        key=lambda item: item[1],
        reverse=True
    )[:10]

    text = "🏆 TOP 10\n\n"

    medals = [
        "🥇",
        "🥈",
        "🥉",
    ]

    for index, (username, count) in enumerate(
        ranking,
        start=1
    ):
        medal = (
            medals[index - 1]
            if index <= 3
            else f"{index}."
        )

        text += (
            f"{medal} @{username} — "
            f"{count} 🗳\n"
        )

    await update.message.reply_text(text)


# =========================
# KONKURSNI YAKUNLASH
# =========================

async def finish(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    global contest_active

    if update.effective_user.id != ADMIN_ID:
        return

    contest_active = False

    if not participants:
        await update.message.reply_text(
            "⛔ Konkursda qatnashchilar yo‘q."
        )
        return

    ranking = sorted(
        participants.items(),
        key=lambda item: item[1],
        reverse=True
    )

    text = "🏆 KONKURS YAKUNLANDI!\n\n"

    for index, (username, count) in enumerate(
        ranking[:10],
        start=1
    ):
        text += (
            f"{index}. @{username} — "
            f"{count} 🗳\n"
        )

    await update.message.reply_text(text)


# =========================
# BROADCAST
# =========================

async def broadcast(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text(
            "📢 Foydalanish:\n\n"
            "/broadcast Xabaringiz"
        )
        return

    text = " ".join(context.args)

    sent = 0
    failed = 0

    for user_id in list(users):

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=text
            )

            sent += 1

        except Exception:
            failed += 1

    await update.message.reply_text(
        "📢 Xabar yuborildi!\n\n"
        f"✅ Yetkazildi: {sent}\n"
        f"❌ Yetkazilmadi: {failed}"
    )


# =========================
# STATISTIKA
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
        f"🏆 Ishtirokchilar: {len(participants)}\n"
        f"🗳 Ovozlar: {len(votes)}\n"
        f"🔥 Konkurs: "
        f"{'Faol 🟢' if contest_active else 'Yopiq 🔴'}"
    )


# =========================
# ADMIN HELP
# =========================

async def admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        "👑 ADMIN BUYRUQLARI\n\n"
        "/top — TOP 10\n"
        "/finish — konkursni tugatish\n"
        "/stats — statistika\n"
        "/broadcast Xabar — reklama/xabar yuborish"
    )


# =========================
# MAIN
# =========================

def main():

    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN GitHub Secret sifatida topilmadi!"
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
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("top", top)
    )

    app.add_handler(
        CommandHandler("finish", finish)
    )

    app.add_handler(
        CommandHandler("broadcast", broadcast)
    )

    app.add_handler(
        CommandHandler("stats", stats)
    )

    app.add_handler(
        CommandHandler("admin", admin)
    )

    # Menu
    app.add_handler(
        CallbackQueryHandler(
            join_contest,
            pattern=r"^join$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            vote,
            pattern=r"^vote:"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            menu_callback,
            pattern=r"^menu_"
        )
    )

    # Kanal postlari
    app.add_handler(
        MessageHandler(
            filters.ChatType.CHANNEL
            & filters.Regex(
                r"(?i)^#konkurs$"
            ),
            konkurs_post
        )
    )

    print("🏆 Ovoz Battle Pro ishga tushdi!")

    app.run_polling()


if __name__ == "__main__":
    main()
