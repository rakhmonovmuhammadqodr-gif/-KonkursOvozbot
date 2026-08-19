import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ==================================================
# SOZLAMALAR
# ==================================================

TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 8992965478

# Boshlang'ich homiy kanal
DEFAULT_CHANNEL = "@OPENBUJETRASMI"

# ==================================================
# DATABASE
# ==================================================

db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS votes (
    voter_id INTEGER,
    target_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(voter_id, target_id)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

db.commit()


# ==================================================
# HOMIY KANALNI OLISH
# ==================================================

def get_channel():
    cur.execute(
        "SELECT value FROM settings WHERE key='channel'"
    )
    result = cur.fetchone()

    if result:
        return result[0]

    cur.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("channel", DEFAULT_CHANNEL)
    )
    db.commit()

    return DEFAULT_CHANNEL


def set_channel(channel):
    cur.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("channel", channel)
    )
    db.commit()


# ==================================================
# USER SAQLASH
# ==================================================

def save_user(user):

    cur.execute("""
        INSERT OR REPLACE INTO users
        (user_id, username, first_name)
        VALUES (?, ?, ?)
    """, (
        user.id,
        user.username or "",
        user.first_name or "Foydalanuvchi"
    ))

    db.commit()


# ==================================================
# OBUNA TEKSHIRISH
# ==================================================

async def check_subscription(user_id, context):

    channel = get_channel()

    try:

        member = await context.bot.get_chat_member(
            chat_id=channel,
            user_id=user_id
        )

        return member.status in [
            "member",
            "administrator",
            "creator"
        ]

    except Exception:

        return False


# ==================================================
# ASOSIY MENYU
# ==================================================

def main_menu():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🗳 Ovoz berish",
                callback_data="vote_menu"
            )
        ],

        [
            InlineKeyboardButton(
                "🏆 TOP",
                callback_data="top"
            )
        ],

        [
            InlineKeyboardButton(
                "📢 Homiy kanal",
                callback_data="sponsor"
            )
        ]

    ])


# ==================================================
# START
# ==================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    save_user(user)

    channel = get_channel()

    keyboard = [

        [
            InlineKeyboardButton(
                "📢 Homiy kanal",
                url=f"https://t.me/{channel.replace('@', '')}"
            )
        ],

        [
            InlineKeyboardButton(
                "✅ Obunani tekshirish",
                callback_data="check_sub"
            )
        ]

    ]

    await update.message.reply_text(

        "👋 Assalomu alaykum!\n\n"
        "🏆 KonkursOvozbotga xush kelibsiz!\n\n"
        "🗳 Ovoz berish uchun avval "
        "homiy kanalga obuna bo‘ling.",

        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==================================================
# ASOSIY CALLBACK
# ==================================================

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    save_user(user)

    # ----------------------------------------------
    # OBUNANI TEKSHIRISH
    # ----------------------------------------------

    if query.data == "check_sub":

        if await check_subscription(user.id, context):

            await query.message.reply_text(
                "✅ Obunangiz tasdiqlandi!\n\n"
                "Endi ovoz berishingiz mumkin.",
                reply_markup=main_menu()
            )

        else:

            channel = get_channel()

            keyboard = [

                [
                    InlineKeyboardButton(
                        "📢 Kanalga obuna bo‘lish",
                        url=f"https://t.me/{channel.replace('@', '')}"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🔄 Qayta tekshirish",
                        callback_data="check_sub"
                    )
                ]

            ]

            await query.message.reply_text(
                "❌ Siz hali homiy kanalga obuna bo‘lmagansiz.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    # ----------------------------------------------
    # HOMIY KANAL
    # ----------------------------------------------

    elif query.data == "sponsor":

        channel = get_channel()

        keyboard = [

            [
                InlineKeyboardButton(
                    "📢 Kanalga kirish",
                    url=f"https://t.me/{channel.replace('@', '')}"
                )
            ],

            [
                InlineKeyboardButton(
                    "🔙 Menyu",
                    callback_data="back_menu"
                )
            ]

        ]

        await query.message.reply_text(
            f"📢 Bizning homiy kanal:\n\n{channel}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ----------------------------------------------
    # MENYU
    # ----------------------------------------------

    elif query.data == "back_menu":

        await query.message.reply_text(
            "🏆 Asosiy menyu:",
            reply_markup=main_menu()
        )

    # ----------------------------------------------
    # OVOZ BERISH MENYUSI
    # ----------------------------------------------

    elif query.data == "vote_menu":

        if not await check_subscription(user.id, context):

            channel = get_channel()

            keyboard = [

                [
                    InlineKeyboardButton(
                        "📢 Homiy kanal",
                        url=f"https://t.me/{channel.replace('@', '')}"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "✅ Obunani tekshirish",
                        callback_data="check_sub"
                    )
                ]

            ]

            await query.message.reply_text(
                "❌ Ovoz berishdan oldin homiy kanalga obuna bo‘ling.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

            return

        cur.execute("""
            SELECT user_id, first_name
            FROM users
            WHERE user_id != ?
            ORDER BY first_name COLLATE NOCASE
        """, (user.id,))

        participants = cur.fetchall()

        if not participants:

            await query.message.reply_text(
                "Hozircha boshqa ishtirokchilar yo‘q."
            )

            return

        buttons = []

        for target_id, name in participants:

            cur.execute(
                "SELECT COUNT(*) FROM votes WHERE target_id=?",
                (target_id,)
            )

            vote_count = cur.fetchone()[0]

            buttons.append([

                InlineKeyboardButton(
                    f"{name} — {vote_count} ta ovoz",
                    callback_data=f"vote:{target_id}"
                )

            ])

        await query.message.reply_text(

            "🗳 Ovoz berish\n\n"
            "Ovoz bermoqchi bo‘lgan ishtirokchini tanlang:",

            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # ----------------------------------------------
    # OVOZ
    # ----------------------------------------------

    elif query.data.startswith("vote:"):

        if not await check_subscription(user.id, context):

            await query.message.reply_text(
                "❌ Avval homiy kanalga obuna bo‘ling."
            )

            return

        target_id = int(query.data.split(":")[1])

        if target_id == user.id:

            await query.message.reply_text(
                "❌ O‘zingizga ovoz bera olmaysiz."
            )

            return

        cur.execute(
            "SELECT first_name FROM users WHERE user_id=?",
            (target_id,)
        )

        target = cur.fetchone()

        if not target:

            await query.message.reply_text(
                "❌ Ishtirokchi topilmadi."
            )

            return

        name = target[0]

        try:

            cur.execute("""
                INSERT INTO votes
                (voter_id, target_id)
                VALUES (?, ?)
            """, (
                user.id,
                target_id
            ))

            db.commit()

        except sqlite3.IntegrityError:

            await query.message.reply_text(
                "⚠️ Siz bu ishtirokchiga allaqachon ovoz bergansiz."
            )

            return

        cur.execute(
            "SELECT COUNT(*) FROM votes WHERE target_id=?",
            (target_id,)
        )

        total_votes = cur.fetchone()[0]

        await query.message.reply_text(

            f"✅ Ovoz berildi!\n\n"
            f"👤 {name}\n"
            f"🗳 Jami ovoz: {total_votes} ta",

            reply_markup=main_menu()
        )

    # ----------------------------------------------
    # TOP
    # ----------------------------------------------

    elif query.data == "top":

        cur.execute("""
            SELECT
                u.first_name,
                COUNT(v.target_id) AS votes
            FROM users u
            LEFT JOIN votes v
            ON u.user_id = v.target_id
            GROUP BY u.user_id
            ORDER BY votes DESC
            LIMIT 20
        """)

        top_users = cur.fetchall()

        if not top_users:

            await query.message.reply_text(
                "Hozircha ishtirokchilar yo‘q."
            )

            return

        text = "🏆 TOP ISHTIROKCHILAR\n\n"

        for i, (name, votes) in enumerate(top_users, 1):

            text += f"{i}. {name} — {votes} ta ovoz\n"

        await query.message.reply_text(
            text,
            reply_markup=main_menu()
        )


# ==================================================
# ADMIN PANEL
# ==================================================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if user.id != OWNER_ID:

        await update.message.reply_text(
            "❌ Bu buyruq faqat bot egasi uchun."
        )

        return

    cur.execute(
        "SELECT COUNT(*) FROM users"
    )

    total = cur.fetchone()[0]

    keyboard = [

        [
            InlineKeyboardButton(
                "📊 Statistika",
                callback_data="admin_stats"
            )
        ],

        [
            InlineKeyboardButton(
                "📢 Homiy kanalni o‘zgartirish",
                callback_data="admin_channel"
            )
        ]

    ]

    await update.message.reply_text(

        "👑 ADMIN PANEL\n\n"
        f"👥 Jami foydalanuvchilar: {total} ta",

        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==================================================
# ADMIN CALLBACK
# ==================================================

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    if query.from_user.id != OWNER_ID:
        return

    # ----------------------------------------------
    # STATISTIKA
    # ----------------------------------------------

    if query.data == "admin_stats":

        cur.execute(
            "SELECT COUNT(*) FROM users"
        )

        total = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(DISTINCT voter_id) FROM votes"
        )

        active_voters = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM votes"
        )

        total_votes = cur.fetchone()[0]

        await query.message.reply_text(

            "📊 BOT STATISTIKASI\n\n"

            f"👥 Jami foydalanuvchilar: {total}\n"
            f"🟢 Ovoz bergan faol foydalanuvchilar: {active_voters}\n"
            f"🗳 Jami berilgan ovozlar: {total_votes}\n\n"

            f"📢 Homiy kanal: {get_channel()}"
        )

    # ----------------------------------------------
    # KANAL O'ZGARTIRISH
    # ----------------------------------------------

    elif query.data == "admin_channel":

        context.user_data["waiting_channel"] = True

        await query.message.reply_text(

            "📢 Yangi homiy kanal username'sini yuboring.\n\n"

            "Masalan:\n"
            "@MeningKanalim\n\n"

            "⚠️ Avval botni shu kanalga admin qiling."
        )


# ==================================================
# ADMIN MATN QABUL QILISH
# ==================================================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if user.id != OWNER_ID:
        return

    if not context.user_data.get("waiting_channel"):
        return

    channel = update.message.text.strip()

    if not channel.startswith("@"):
        channel = "@" + channel

    # Kanalni bot orqali tekshirish
    try:

        chat = await context.bot.get_chat(channel)

        if chat.type != "channel":

            await update.message.reply_text(
                "❌ Bu username kanalniki emas."
            )

            return

    except Exception:

        await update.message.reply_text(

            "❌ Kanal topilmadi.\n\n"
            "Username to‘g‘ri ekanini va bot "
            "kanalga admin qilinganini tekshiring."
        )

        return

    set_channel(channel)

    context.user_data["waiting_channel"] = False

    await update.message.reply_text(

        "✅ Homiy kanal muvaffaqiyatli ulandi!\n\n"
        f"📢 Kanal: {channel}"
    )


# ==================================================
# ISHGA TUSHIRISH
# ==================================================

def main():

    if not TOKEN:
        raise ValueError(
            "BOT_TOKEN topilmadi! GitHub Secrets ichiga BOT_TOKEN qo‘ying."
        )

    app = Application.builder().token(TOKEN).build()

    # START
    app.add_handler(
        CommandHandler("start", start)
    )

    # ADMIN
    app.add_handler(
        CommandHandler("admin", admin)
    )

    # ADMIN CALLBACK
    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern="^admin_"
        )
    )

    # ODDIY CALLBACK
    app.add_handler(
        CallbackQueryHandler(callback)
    )

    # ADMIN TEXT
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
        )
    )

    print("BOT ISHLADI!")

    app.run_polling()


if __name__ == "__main__":
    main()
