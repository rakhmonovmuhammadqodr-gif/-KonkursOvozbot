import os
import sqlite3
from datetime import datetime, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# =====================================================
# SOZLAMALAR
# =====================================================

TOKEN = os.getenv("BOT_TOKEN")

OWNER_IDS = [
    8992965478,
    8679536810
]

DEFAULT_CHANNEL = "@OPENBUJETRASMI"

# =====================================================
# DATABASE
# =====================================================

db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    joined_at TEXT,
    last_seen TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS votes (
    voter_id INTEGER,
    target_id INTEGER,
    created_at TEXT,
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


# =====================================================
# VAQT
# =====================================================

def now():
    return datetime.now(timezone.utc).isoformat()


# =====================================================
# HOMIY KANAL
# =====================================================

def get_channel():

    cur.execute(
        "SELECT value FROM settings WHERE key='channel'"
    )

    result = cur.fetchone()

    if result:
        return result[0]

    cur.execute(
        "INSERT INTO settings (key,value) VALUES (?,?)",
        ("channel", DEFAULT_CHANNEL)
    )

    db.commit()

    return DEFAULT_CHANNEL


def set_channel(channel):

    cur.execute(
        "INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)",
        ("channel", channel)
    )

    db.commit()


# =====================================================
# FOYDALANUVCHI SAQLASH
# =====================================================

def save_user(user):

    current = now()

    cur.execute(
        "SELECT user_id FROM users WHERE user_id=?",
        (user.id,)
    )

    exists = cur.fetchone()

    if exists:

        cur.execute("""
            UPDATE users
            SET username=?,
                first_name=?,
                last_seen=?
            WHERE user_id=?
        """, (
            user.username or "",
            user.first_name or "Foydalanuvchi",
            current,
            user.id
        ))

    else:

        cur.execute("""
            INSERT INTO users
            (user_id, username, first_name, joined_at, last_seen)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user.id,
            user.username or "",
            user.first_name or "Foydalanuvchi",
            current,
            current
        ))

    db.commit()


# =====================================================
# OBUNANI TEKSHIRISH
# =====================================================

async def is_subscribed(user_id, context):

    channel = get_channel()

    try:

        member = await context.bot.get_chat_member(
            chat_id=channel,
            user_id=user_id
        )

        return member.status in (
            "member",
            "administrator",
            "creator"
        )

    except Exception:

        return False


# =====================================================
# HOMIY KANAL TUGMASI
# =====================================================

def sponsor_buttons():

    channel = get_channel()

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "📢 Homiy kanal",
                url=f"https://t.me/{channel.replace('@','')}"
            )
        ],

        [
            InlineKeyboardButton(
                "✅ Obunani tekshirish",
                callback_data="check_sub"
            )
        ]

    ])


# =====================================================
# ASOSIY MENYU
# =====================================================

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


# =====================================================
# START
# =====================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    save_user(user)

    await update.message.reply_text(

        "🏆 KONKURS OVOZ BOT\n\n"
        "Assalomu alaykum!\n\n"
        "🗳 Ovoz berish uchun avval homiy "
        "kanalga obuna bo‘ling.",

        reply_markup=sponsor_buttons()
    )


# =====================================================
# CALLBACK
# =====================================================

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    save_user(user)


    # ================================================
    # OBUNA TEKSHIRISH
    # ================================================

    if query.data == "check_sub":

        if await is_subscribed(user.id, context):

            await query.message.reply_text(
                "✅ Obuna tasdiqlandi!\n\n"
                "Endi ovoz berishingiz mumkin.",
                reply_markup=main_menu()
            )

        else:

            await query.message.reply_text(
                "❌ Siz hali homiy kanalga obuna bo‘lmagansiz.",
                reply_markup=sponsor_buttons()
            )

        return


    # ================================================
    # HOMIY KANAL
    # ================================================

    if query.data == "sponsor":

        channel = get_channel()

        keyboard = InlineKeyboardMarkup([

            [
                InlineKeyboardButton(
                    "📢 Kanalga kirish",
                    url=f"https://t.me/{channel.replace('@','')}"
                )
            ],

            [
                InlineKeyboardButton(
                    "🔙 Orqaga",
                    callback_data="back"
                )
            ]

        ])

        await query.message.reply_text(
            f"📢 Homiy kanal:\n\n{channel}",
            reply_markup=keyboard
        )

        return


    # ================================================
    # ORQAGA
    # ================================================

    if query.data == "back":

        await query.message.reply_text(
            "🏠 Asosiy menyu:",
            reply_markup=main_menu()
        )

        return


    # ================================================
    # OVOZ BERISH
    # ================================================

    if query.data == "vote_menu":

        if not await is_subscribed(user.id, context):

            await query.message.reply_text(
                "❌ Ovoz berish uchun homiy kanalga obuna bo‘ling.",
                reply_markup=sponsor_buttons()
            )

            return


        # MUHIM:
        # BU YERDA ADMIN EMAS,
        # BOTGA KIRGAN BARCHA ODAMLAR OLINGAN

        cur.execute("""
            SELECT user_id, first_name
            FROM users
            ORDER BY first_name COLLATE NOCASE
        """)

        users = cur.fetchall()

        if not users:

            await query.message.reply_text(
                "Hozircha ishtirokchilar yo‘q."
            )

            return


        buttons = []

        for target_id, name in users:

            # O'ziga ovoz berish tugmasini ham ko'rsatmaymiz
            if target_id == user.id:
                continue

            cur.execute("""
                SELECT COUNT(*)
                FROM votes
                WHERE target_id=?
            """, (target_id,))

            vote_count = cur.fetchone()[0]

            buttons.append([

                InlineKeyboardButton(
                    f"{name} — {vote_count} ta ovoz",
                    callback_data=f"vote:{target_id}"
                )

            ])


        if not buttons:

            await query.message.reply_text(
                "Hozircha sizdan boshqa ishtirokchi yo‘q."
            )

            return


        await query.message.reply_text(

            "🗳 OVOZ BERISH\n\n"
            "Ovoz bermoqchi bo‘lgan odamni tanlang:",

            reply_markup=InlineKeyboardMarkup(buttons)
        )

        return


    # ================================================
    # OVOZ
    # ================================================

    if query.data.startswith("vote:"):

        if not await is_subscribed(user.id, context):

            await query.message.reply_text(
                "❌ Avval homiy kanalga obuna bo‘ling."
            )

            return


        target_id = int(
            query.data.split(":")[1]
        )


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


        try:

            cur.execute("""
                INSERT INTO votes
                (voter_id, target_id, created_at)
                VALUES (?, ?, ?)
            """, (
                user.id,
                target_id,
                now()
            ))

            db.commit()

        except sqlite3.IntegrityError:

            await query.message.reply_text(
                "⚠️ Siz bu ishtirokchiga allaqachon ovoz bergansiz."
            )

            return


        name = target[0]

        cur.execute("""
            SELECT COUNT(*)
            FROM votes
            WHERE target_id=?
        """, (target_id,))

        total = cur.fetchone()[0]


        await query.message.reply_text(

            "✅ OVOZ QABUL QILINDI!\n\n"
            f"👤 {name}\n"
            f"🗳 {total} ta ovoz",

            reply_markup=main_menu()
        )

        return


    # ================================================
    # TOP
    # ================================================

    if query.data == "top":

        cur.execute("""
            SELECT
                u.first_name,
                COUNT(v.target_id) AS vote_count
            FROM users u
            LEFT JOIN votes v
            ON u.user_id = v.target_id
            GROUP BY u.user_id
            ORDER BY vote_count DESC, u.first_name ASC
            LIMIT 50
        """)

        rows = cur.fetchall()

        if not rows:

            await query.message.reply_text(
                "🏆 Hozircha TOP bo‘sh."
            )

            return


        text = "🏆 TOP ISHTIROKCHILAR\n\n"

        for i, (name, votes) in enumerate(rows, 1):

            text += (
                f"{i}. {name} — "
                f"{votes} ta ovoz\n"
            )


        await query.message.reply_text(
            text,
            reply_markup=main_menu()
        )

        return


# =====================================================
# /KONKURS
# =====================================================

async def konkurs(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    save_user(user)

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "📢 Homiy kanalga obuna bo‘lish",
                url=f"https://t.me/{get_channel().replace('@','')}"
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

    ])


    await update.message.reply_text(

        "🏆 KONKURS BOSHLANDI!\n\n"
        "🗳 Ishtirokchilar ovoz yig‘adi.\n"
        "👥 Eng ko‘p ovoz olganlar TOPda chiqadi.\n\n"
        "📢 Ovoz berishdan oldin homiy "
        "kanalga obuna bo‘ling.",

        reply_markup=keyboard
    )


# =====================================================
# ADMIN
# =====================================================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if user.id not in OWNER_IDS:

        await update.message.reply_text(
            "❌ Sizda admin huquqi yo‘q."
        )

        return


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

    total_votes = cur.fetchone()[0]


    keyboard = InlineKeyboardMarkup([

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

    ])


    await update.message.reply_text(

        "👑 ADMIN PANEL\n\n"

        f"👥 Jami odam: {total}\n"
        f"🟢 Faol ovoz beruvchilar: {active}\n"
        f"🗳 Jami ovozlar: {total_votes}\n\n"

        f"📢 Homiy: {get_channel()}",

        reply_markup=keyboard
    )


# =====================================================
# ADMIN CALLBACK
# =====================================================

async def admin_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()


    if query.from_user.id not in OWNER_IDS:
        return


    # ================================================
    # STATISTIKA
    # ================================================

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

            f"👥 Jami foydalanuvchilar: {total}\n"
            f"🟢 Faol ovoz berganlar: {active}\n"
            f"🗳 Jami ovozlar: {votes}\n\n"

            f"📢 Homiy kanal: {get_channel()}"
        )

        return


    # ================================================
    # HOMIY KANAL
    # ================================================

    if query.data == "admin_channel":

        context.user_data["waiting_channel"] = True

        await query.message.reply_text(

            "📢 Homiy kanal username'ini yuboring.\n\n"

            "Masalan:\n"
            "@KanalNomi\n\n"

            "⚠️ Bot o‘sha kanalga admin qilingan bo‘lishi kerak."
        )

        return


# =====================================================
# ADMIN KANAL NOMINI QABUL QILISH
# =====================================================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user


    if user.id not in OWNER_IDS:
        return


    if not context.user_data.get("waiting_channel"):
        return


    channel = update.message.text.strip()


    if not channel.startswith("@"):
        channel = "@" + channel


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
            "Username'ni tekshiring va botni "
            "kanalga admin qiling."
        )

        return


    set_channel(channel)

    context.user_data["waiting_channel"] = False


    await update.message.reply_text(

        "✅ HOMIY KANAL ULANDI!\n\n"
        f"📢 {channel}"
    )


# =====================================================
# MAIN
# =====================================================

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


    # /start
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    # /admin
    app.add_handler(
        CommandHandler(
            "admin",
            admin
        )
    )


    # /konkurs
    app.add_handler(
        CommandHandler(
            "konkurs",
            konkurs
        )
    )


    # Admin tugmalari
    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern="^admin_"
        )
    )


    # Oddiy tugmalar
    app.add_handler(
        CallbackQueryHandler(
            callback
        )
    )


    # Admin kanal username'i
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
