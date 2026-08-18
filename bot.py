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

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL = "@OPENBUJETRASMI"
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

logging.basicConfig(level=logging.INFO)

# Foydalanuvchilar
users = set()

# Konkurs qatnashchilari: username -> ovoz
participants = {}

# Bir odam bir qatnashchiga bir marta ovoz beradi
votes = set()

# Konkurs holati
contest_active = False


def results_text():
    if not participants:
        return "Hozircha hech kim konkursga qo‘shilmagan."

    ranking = sorted(
        participants.items(),
        key=lambda x: x[1],
        reverse=True
    )

    text = ""

    for username, count in ranking:
        text += f"@{username} — {count}\n"

    return text


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
                "📊 NATIJALAR",
                callback_data="results"
            )
        ]
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user:
        return

    users.add(user.id)

    # Ovoz linki orqali kirish
    if context.args and context.args[0].startswith("vote_"):
        target = context.args[0][5:].lower()

        if not contest_active:
            await update.message.reply_text(
                "⛔ Hozircha faol konkurs yo‘q."
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
            "🏆 OVOZ BATTLE\n\n"
            "1️⃣ Avval kanalga obuna bo‘ling.\n"
            "2️⃣ Keyin 🗳 OVOZ BERISH tugmasini bosing.",
            reply_markup=keyboard
        )
        return

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🏆 OVOZLI KONKURS",
                callback_data="menu_voice"
            )
        ],
        [
            InlineKeyboardButton(
                "🎲 RANDOM KONKURS",
                callback_data="menu_random"
            ),
            InlineKeyboardButton(
                "⚔️ LIKE BATTLE",
                callback_data="menu_battle"
            )
        ],
        [
            InlineKeyboardButton(
                "🔍 KONKURSNI TEKSHIRISH",
                callback_data="menu_check"
            )
        ]
    ])

    await update.message.reply_text(
        "✅ Xush kelibsiz!\n\n"
        "🤖 Bot ishga tushdi!\n\n"
        "📌 Kanalda:\n"
        "• #konkurs — ovozli konkurs\n"
        "• #random — random konkurs\n"
        "• #batl — like battle\n\n"
        "👇 Kerakli bo‘limni tanlang:",
        reply_markup=keyboard
    )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_voice":
        await query.edit_message_text(
            "🏆 OVOZLI KONKURS\n\n"
            "Kanalga #konkurs yozilganda konkurs boshlanadi.\n\n"
            "Har bir qatnashchi o‘z ovoz linkini oladi."
        )

    elif query.data == "menu_random":
        await query.edit_message_text(
            "🎲 RANDOM KONKURS\n\n"
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
            "Like battle bo‘limi."
        )

    elif query.data == "menu_check":
        await query.edit_message_text(
            "🔍 KONKURSNI TEKSHIRISH\n\n"
            "Ovozlar bot orqali nazorat qilinadi."
        )


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
            "❗ Avval Telegram username qo‘ying.",
            show_alert=True
        )
        return

    username = user.username.lower()

    # Istagancha odam qo‘shilishi mumkin
    if username not in participants:
        participants[username] = 0

    me = await context.bot.get_me()

    link = f"https://t.me/{me.username}?start=vote_{username}"

    await query.edit_message_text(
        "🎉 KONKURSGA QO‘SHILDINGIZ!\n\n"
        f"👤 @{username}\n"
        f"🗳 Ovozlar: {participants[username]}\n\n"
        "🔗 Shaxsiy ovoz linkingiz:\n"
        f"{link}\n\n"
        "📢 Linkni do‘stlaringizga yuboring.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "📊 NATIJALAR",
                    callback_data="results"
                )
            ]
        ])
    )


async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not participants:
        text = "🏆 NATIJALAR\n\nHozircha qatnashchilar yo‘q."
    else:
        ranking = sorted(
            participants.items(),
            key=lambda x: x[1],
            reverse=True
        )

        text = "🏆 NATIJALAR\n\n"

        for i, (username, count) in enumerate(ranking, 1):
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            else:
                medal = f"{i}."

            text += f"{medal} @{username} — {count}\n"

    await query.edit_message_text(
        text,
        reply_markup=contest_keyboard()
    )


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
            "❌ Ishtirokchi topilmadi.",
            show_alert=True
        )
        return

    # Kanalga obunani tekshirish
    try:
        member = await context.bot.get_chat_member(
            CHANNEL,
            voter.id
        )

        if member.status in ("left", "kicked"):
            await query.answer(
                "❗ Avval kanalga obuna bo‘ling!",
                show_alert=True
            )
            return

    except Exception as error:
        logging.error("Obuna tekshirish xatosi: %s", error)

       
