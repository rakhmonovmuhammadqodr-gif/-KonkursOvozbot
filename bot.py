import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ==================================================
# SOZLAMALAR
# ==================================================

TOKEN = os.getenv("BOT_TOKEN")

# 2 TA BOT EGASI
OWNER_IDS = [
    8992965478,
    8679536810
]

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
    first_name TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS votes (
    voter_id INTEGER,
    target_id INTEGER,
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
# HOMIY KANAL
# ==================================================

def get_channel():

    cur.execute(
        "SELECT value FROM settings WHERE key = 'channel'"
    )

    result = cur.fetchone()

    if result:
        return result[0]

    cur.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)",
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

async def is_subscribed(user_id, context):

    channel = get_channel()

    try:

        member = await context.bot.get_chat_member(
            channel,
            user_id
        )

        return member.status in (
            "member",
            "administrator",
            "creator"
        )

    except Exception:

        return False


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
                callback_data="check"
            )
        ],

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
        ]

    ]

    await update.message.reply_text(

        "🏆 KonkursOvozbot\n\n"
        "Ovoz berish uchun homiy kanalga obuna bo'ling.",

        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==================================================
# ODDIY CALLBACK
# ==================================================

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    save_user(user)


    # ==============================================
    # OBUNANI TEKSHIRISH
    # ==============================================

    if query.data == "check":

        if await is_subscribed(user.id, context):

            await query.message.reply_text(
                "✅ Obuna tasdiqlandi!\n\n"
                "Endi ovoz berishingiz mumkin."
            )

        else:

            await query.message.reply_text(
                "❌ Avval homiy kanalga obuna bo'ling."
            )

        return


    # ==============================================
    # OVOZ MENYUSI
    # ==============================================

    if query.data == "vote_menu":

        if not await is_subscribed(user.id, context):

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
                        "✅ Tekshirish",
                        callback_data="check"
                    )
                ]

            ]

            await query.message.reply_text(
                "❌ Ovoz berish uchun homiy kanalga obuna bo'ling.",
                reply_markup=InlineKeyboardMarkup(keyboard)
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
                "Hozircha ishtirokchilar yo'q."
            )

            return


        buttons = []

        for target_id, name in users:

            cur.execute(
                "SELECT COUNT(*) FROM votes WHERE target_id = ?",
                (target_id,)
            )

            votes = cur.fetchone()[0]

            buttons.append([

                InlineKeyboardButton(
                    f"{name} — {votes} ta ovoz",
                    callback_data=f"vote:{target_id}"
                )

            ])


        await query.message.reply_text(

            "🗳 OVOZ BERISH\n\n"
            "Ovoz bermoqchi bo'lgan ishtirokchini tanlang:",

            reply_markup=InlineKeyboardMarkup(buttons)
        )

        return


    # ==============================================
    # OVOZ BERISH
    # ==============================================

    if query.data.startswith("vote:"):

        if not await is_subscribed(user.id, context):

            await query.message.reply_text(
                "❌ Avval homiy kanalga obuna bo'ling."
            )

            return


        target_id = int(
            query.data.split(":")[1]
        )


        if target_id == user.id:

            await query.message.reply_text(
                "❌ O'zingizga ovoz bera olmaysiz."
            )

            return


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
            "SELECT first_name FROM users WHERE user_id = ?",
            (target_id,)
        )

        result = cur.fetchone()

        name = (
            result[0]
            if result
            else "Ishtirokchi"
        )


        cur.execute(
            "SELECT COUNT(*) FROM votes WHERE target_id = ?",
            (target_id,)
        )

        total = cur.fetchone()[0]


        await query.message.reply_text(

            f"✅ Ovoz berildi!\n\n"
            f"👤 {name}\n"
            f"🗳 {total} ta ovoz"
        )

        return


    # ==============================================
    # TOP
    # ==============================================

    if query.data == "top":

        cur.execute("""
            SELECT
                u.first_name,
                COUNT(v.target_id)
            FROM users u
            LEFT JOIN votes v
            ON u.user_id = v.target_id
            GROUP BY u.user_id
            ORDER BY COUNT(v.target_id) DESC
            LIMIT 20
        """)

        rows = cur.fetchall()


        text = "🏆 TOP ISHTIROKCHILAR\n\n"


        for i, (name, votes) in enumerate(rows, 1):

            text += (
                f"{i}. {name} — "
                f"{votes} ta ovoz\n"
            )


        await query.message.reply_text(text)

        return


# ==================================================
# ADMIN PANEL
# ==================================================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user


    # FAQAT 2 TA EGA
    if user.id not in OWNER_IDS:

        await update.message.reply_text(
            "❌ Sizda admin huquqi yo'q."
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
                "📢 Homiy kanalni o'zgartirish",
                callback_data="admin_channel"
            )
        ]

    ]


    await update.message.reply_text(

        "👑 ADMIN PANEL\n\n"
        f"👥 Botdagi odamlar: {total} ta",

        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# ==================================================
# ADMIN CALLBACK
# ==================================================

async def admin_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()


    # FAQAT 2 TA EGA
    if query.from_user.id not in OWNER_IDS:
        return


    # ==============================================
    # STATISTIKA
    # ==============================================

    if query.data == "admin_stats":

        cur.execute(
            "SELECT COUNT(*) FROM users"
        )

        total = cur.fetchone()[0]


        cur.execute(
            "SELECT COUNT(DISTINCT voter_id) FROM votes"
        )

        active = cur.fetchone()[0]


        cur.execute(
            "SELECT COUNT(*) FROM votes"
        )

        votes = cur.fetchone()[0]


        await query.message.reply_text(

            "📊 BOT STATISTIKASI\n\n"

            f"👥 Jami odam: {total}\n"
            f"🟢 Faol ovoz beruvchilar: {active}\n"
            f"🗳 Jami ovozlar: {votes}\n\n"
            f"📢 Homiy kanal: {get_channel()}"
        )

        return


    # ==============================================
    # HOMIY KANAL
    # ==============================================

    if query.data == "admin_channel":

        context.user_data[
            "waiting_channel"
        ] = True


        await query.message.reply_text(

            "📢 Homiy kanal username'sini yuboring.\n\n"

            "Masalan:\n"
            "@KanalNomi\n\n"

            "⚠️ Bot avval kanalga admin qilingan bo'lishi kerak."
        )

        return


# ==================================================
# ADMIN TEXT
# ==================================================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user


    # FAQAT 2 TA EGA
    if user.id not in OWNER_IDS:
        return


    if not context.user_data.get(
        "waiting_channel"
    ):
        return


    channel = update.message.text.strip()


    if not channel.startswith("@"):

        channel = "@" + channel


    try:

        chat = await context.bot.get_chat(
            channel
        )


        if chat.type != "channel":

            await update.message.reply_text(
                "❌ Bu username kanalniki emas."
            )

            return


    except Exception:

        await update.message.reply_text(

            "❌ Kanal topilmadi.\n\n"

            "Kanal username'ini tekshiring.\n"
            "Bot kanalga admin bo'lishi kerak."
        )

        return


    set_channel(channel)


    context.user_data[
        "waiting_channel"
    ] = False


    await update.message.reply_text(

        "✅ Homiy kanal muvaffaqiyatli ulandi!\n\n"
        f"📢 {channel}"
    )


# ==================================================
# MAIN
# ==================================================

def main():

    if not TOKEN:

        raise ValueError(
            "BOT_TOKEN topilmadi!"
        )


    app = (
        Application
        .builder()
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
            "admin",
            admin
        )
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
        CallbackQueryHandler(
            callback
        )
    )


    # ADMIN TEXT
    app.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            text_handler
        )
    )


    print("BOT ISHLADI!")


    app.run_polling()


if __name__ == "__main__":
    main()
