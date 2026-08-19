import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# =========================
# SOZLAMALAR
# =========================

TOKEN = os.getenv("BOT_TOKEN")

# BOT EGASINING TELEGRAM ID SI
OWNER_ID = 8992965478

# Boshlang'ich homiy kanal
CHANNEL = "@OPENBUJETRASMI"

# =========================
# DATABASE
# =========================

db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    joined INTEGER DEFAULT 1
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS votes (
    voter_id INTEGER,
    target_id INTEGER,
    UNIQUE(voter_id, target_id)
)
""")

db.commit()


# =========================
# FOYDALANUVCHI SAQLASH
# =========================

def save_user(user):
    cur.execute("""
    INSERT OR REPLACE INTO users
    (user_id, username, first_name, joined)
    VALUES (?, ?, ?, 1)
    """, (
        user.id,
        user.username or "",
        user.first_name or "",
    ))
    db.commit()


# =========================
# OBUNA TEKSHIRISH
# =========================

async def is_subscribed(user_id, context):
    try:
        member = await context.bot.get_chat_member(
            chat_id=CHANNEL,
            user_id=user_id
        )

        return member.status in [
            "member",
            "administrator",
            "creator"
        ]

    except Exception:
        return False


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    save_user(user)

    keyboard = [
        [
            InlineKeyboardButton(
                "📢 Homiy kanalga obuna bo‘lish",
                url=f"https://t.me/{CHANNEL.replace('@', '')}"
            )
        ],
        [
            InlineKeyboardButton(
                "✅ Obunani tekshirish",
                callback_data="check_sub"
            )
        ],
        [
            InlineKeyboardButton(
                "🗳 Ovoz berish",
                callback_data="vote_menu"
            )
        ]
    ]

    await update.message.reply_text(
        "👋 Assalomu alaykum!\n\n"
        "🏆 KonkursOvozbotga xush kelibsiz!\n\n"
        "Ovoz berish uchun avval homiy kanalga obuna bo‘ling.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# CALLBACK
# =========================

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = query.from_user

    # OBUNANI TEKSHIRISH
    if query.data == "check_sub":

        if await is_subscribed(user.id, context):

            await query.message.reply_text(
                "✅ Obuna tasdiqlandi!\n\n"
                "Endi ovoz berishingiz mumkin."
            )

        else:

            await query.message.reply_text(
                "❌ Siz hali homiy kanalga obuna bo‘lmagansiz.\n\n"
                "Avval kanalga obuna bo‘ling."
            )

    # OVOZ MENYUSI
    elif query.data == "vote_menu":

        if not await is_subscribed(user.id, context):

            await query.message.reply_text(
                "❌ Avval homiy kanalga obuna bo‘ling!"
            )
            return

        cur.execute("""
        SELECT user_id, first_name
        FROM users
        WHERE user_id != ?
        ORDER BY first_name
        """, (user.id,))

        users = cur.fetchall()

        if not users:
            await query.message.reply_text(
                "Hozircha boshqa ishtirokchilar yo‘q."
            )
            return

        buttons = []

        for uid, name in users:

            cur.execute(
                "SELECT COUNT(*) FROM votes WHERE target_id=?",
                (uid,)
            )

            vote_count = cur.fetchone()[0]

            buttons.append([
                InlineKeyboardButton(
                    f"{name} — {vote_count} ta ovoz",
                    callback_data=f"vote_{uid}"
                )
            ])

        await query.message.reply_text(
            "🗳 Ovoz bermoqchi bo‘lgan ishtirokchini tanlang:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # OVOZ BERISH
    elif query.data.startswith("vote_"):

        if not await is_subscribed(user.id, context):

            await query.message.reply_text(
                "❌ Avval homiy kanalga obuna bo‘ling!"
            )
            return

        target_id = int(query.data.split("_")[1])

        if target_id == user.id:

            await query.message.reply_text(
                "❌ O‘zingizga ovoz bera olmaysiz."
            )
            return

        try:

            cur.execute(
                "INSERT INTO votes (voter_id, target_id) VALUES (?, ?)",
                (user.id, target_id)
            )

            db.commit()

            cur.execute(
                "SELECT first_name FROM users WHERE user_id=?",
                (target_id,)
            )

            result = cur.fetchone()

            name = result[0] if result else "Ishtirokchi"

            cur.execute(
                "SELECT COUNT(*) FROM votes WHERE target_id=?",
                (target_id,)
            )

            count = cur.fetchone()[0]

            await query.message.reply_text(
                f"✅ Ovoz berildi!\n\n"
                f"👤 {name}\n"
                f"🗳 Ovozlar: {count} ta"
            )

        except sqlite3.IntegrityError:

            await query.message.reply_text(
                "⚠️ Siz bu ishtirokchiga allaqachon ovoz bergansiz."
            )


# =========================
# ADMIN PANEL
# =========================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if user.id != OWNER_ID:
        return

    cur.execute("SELECT COUNT(*) FROM users")
    total = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM users WHERE joined=1"
    )
    active = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM users WHERE joined=0"
    )
    left = cur.fetchone()[0]

    keyboard = [
        [
            InlineKeyboardButton(
                "📢 Homiy kanalni o‘zgartirish",
                callback_data="change_channel"
            )
        ],
        [
            InlineKeyboardButton(
                "📊 Statistika",
                callback_data="stats"
            )
        ]
    ]

    await update.message.reply_text(
        "👑 ADMIN PANEL",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# ADMIN CALLBACK
# =========================

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        return

    if query.data == "stats":

        cur.execute("SELECT COUNT(*) FROM users")
        total = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM users WHERE joined=1"
        )
        active = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM users WHERE joined=0"
        )
        left = cur.fetchone()[0]

        await query.message.reply_text(
            "📊 BOT STATISTIKASI\n\n"
            f"👥 Jami foydalanuvchilar: {total}\n"
            f"🟢 Faol: {active}\n"
            f"🔴 Chiqib ketgan: {left}"
        )

    elif query.data == "change_channel":

        await query.message.reply_text(
            "📢 Yangi homiy kanal username'sini yuboring.\n\n"
            "Masalan:\n"
            "@KanalNomi"
        )

        context.user_data["waiting_channel"] = True


# =========================
# ADMIN MATN QABUL QILISH
# =========================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global CHANNEL

    user = update.effective_user

    if user.id != OWNER_ID:
        return

    if context.user_data.get("waiting_channel"):

        new_channel = update.message.text.strip()

        if not new_channel.startswith("@"):
            new_channel = "@" + new_channel

        CHANNEL = new_channel

        context.user_data["waiting_channel"] = False

        await update.message.reply_text(
            f"✅ Homiy kanal o‘zgartirildi:\n\n{CHANNEL}"
        )


# =========================
# BOTNI ISHGA TUSHIRISH
# =========================

def main():

    if not TOKEN:
        raise ValueError("BOT_TOKEN topilmadi!")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern="^(stats|change_channel)$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            callback
        )
    )

    app.add_handler(
        # Oddiy text xabarlarini admin kanal o'zgartirish uchun oladi
        # Boshqa foydalanuvchilar uchun hech narsa qilmaydi
        CommandHandler("setchannel", admin)
    )

    print("BOT ISHLADI!")

    app.run_polling()


if __name__ == "__main__":
    main()
