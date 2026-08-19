import os
import sqlite3
import logging
from typing import Optional

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =========================================================
# SOZLAMALAR
# =========================================================

TOKEN = os.getenv("BOT_TOKEN", "")
CHANNEL = os.getenv("CHANNEL_USERNAME", "@OPENBUJETRASMI")

# Bot egasining Telegram ID'si
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# Adminlar ID'si: 123456;654321 kabi
ADMIN_IDS_TEXT = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = set()

if ADMIN_IDS_TEXT:
    for x in ADMIN_IDS_TEXT.split(";"):
        try:
            ADMIN_IDS.add(int(x.strip()))
        except ValueError:
            pass

if OWNER_ID:
    ADMIN_IDS.add(OWNER_ID)

DB_FILE = "bot.db"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# DATABASE
# =========================================================

def db():
    return sqlite3.connect(DB_FILE)


def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            added_count INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            voter_id INTEGER,
            participant_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(voter_id, participant_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    con.commit()
    con.close()


def save_user(user):
    con = db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO users(user_id, username, first_name)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            username=excluded.username,
            first_name=excluded.first_name
    """, (
        user.id,
        user.username or "",
        user.first_name or "",
    ))

    con.commit()
    con.close()


def get_all_users():
    con = db()
    cur = con.cursor()
    cur.execute("SELECT user_id FROM users")
    rows = cur.fetchall()
    con.close()
    return [x[0] for x in rows]


def set_setting(key, value):
    con = db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO settings(key, value)
        VALUES (?, ?)
        ON CONFLICT(key)
        DO UPDATE SET value=excluded.value
    """, (key, value))

    con.commit()
    con.close()


def get_setting(key, default=None):
    con = db()
    cur = con.cursor()

    cur.execute(
        "SELECT value FROM settings WHERE key=?",
        (key,)
    )

    row = cur.fetchone()
    con.close()

    if row:
        return row[0]

    return default


# =========================================================
# ADMIN
# =========================================================

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# =========================================================
# MAJBURIY OBUNA
# =========================================================

async def is_subscribed(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int
) -> bool:

    try:
        member = await context.bot.get_chat_member(
            CHANNEL,
            user_id
        )

        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        )

    except Exception as e:
        logger.warning("Subscription check error: %s", e)
        return False


async def subscription_required(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> bool:

    user = update.effective_user

    if is_admin(user.id):
        return False

    ok = await is_subscribed(context, user.id)

    if ok:
        return False

    keyboard = [
        [
            InlineKeyboardButton(
                "📢 Kanalga obuna bo‘lish",
                url=f"https://t.me/{CHANNEL.lstrip('@')}"
            )
        ],
        [
            InlineKeyboardButton(
                "✅ Tekshirish",
                callback_data="check_sub"
            )
        ]
    ]

    text = (
        "⚠️ Botdan foydalanish uchun avval kanalga obuna bo‘ling.\n\n"
        "Obuna bo‘lgach, «Tekshirish» tugmasini bosing."
    )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.effective_message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    return True


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    save_user(user)

    # Referral
    if context.args:
        arg = context.args[0]

        if arg.startswith("vote_"):
            try:
                participant_id = int(arg.replace("vote_", ""))

                await vote_for_participant(
                    update,
                    context,
                    participant_id
                )

                return

            except ValueError:
                pass

    if await subscription_required(update, context):
        return

    text = """✅ Xush kelibsiz!

🤖 Bot ishga tushdi!

📌 Kanalda:
   • #konkurs - ovozli konkurs
   • #random - random konkurs
   • #batl - like batl (yangi!)

📝 Random konkurs formati:
   #random
   salom yangi konkurs boshlandik
   yutuq nft emas
   shartlari
   @kanal
   #soni 3

🔍 Ovoz batl tekshirish:
   • Quyidagi knopkani bosing va konkurs xabarini forward qiling

👇 Kerakli bo‘limni tanlang:
"""

    keyboard = [
        [
            InlineKeyboardButton(
                "🏆 #KONKURS",
                callback_data="menu_konkurs"
            )
        ],
        [
            InlineKeyboardButton(
                "🎲 #RANDOM",
                callback_data="menu_random"
            ),
            InlineKeyboardButton(
                "❤️ #BATL",
                callback_data="menu_batl"
            )
        ],
        [
            InlineKeyboardButton(
                "🏅 TOP",
                callback_data="menu_top"
            )
        ],
    ]

    if is_admin(user.id):
        keyboard.append([
            InlineKeyboardButton(
                "👑 ADMIN",
                callback_data="admin_menu"
            )
        ])

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================================================
# MENU
# =========================================================

async def menu_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "check_sub":
        ok = await is_subscribed(
            context,
            query.from_user.id
        )

        if ok:
            await query.message.reply_text(
                "✅ Obuna tasdiqlandi!\n/start buyrug‘ini bosing."
            )
        else:
            await query.message.reply_text(
                "❌ Hali kanalga obuna bo‘lmagansiz."
            )

        return

    if await subscription_required(update, context):
        return

    if data == "menu_konkurs":

        await query.message.reply_text(
            "🏆 KONKURS\n\n"
            "Konkursda qatnashish uchun konkurs xabaridagi "
            "ishtirok etish tugmasidan foydalaning."
        )

    elif data == "menu_random":

        await query.message.reply_text(
            "🎲 RANDOM KONKURS\n\n"
            "Random konkurs formati:\n\n"
            "#random\n"
            "salom yangi konkurs boshlandik\n"
            "yutuq nft emas\n"
            "shartlari\n"
            "@kanal\n"
            "#soni 3"
        )

    elif data == "menu_batl":

        await query.message.reply_text(
            "❤️ LIKE BATL\n\n"
            "Konkurs xabarini forward qilib, "
            "batl natijasini tekshirishingiz mumkin."
        )

    elif data == "menu_top":

        await show_top(query.message)

    elif data == "admin_menu":

        if not is_admin(query.from_user.id):
            return

        await query.message.reply_text(
            "👑 ADMIN PANEL\n\n"
            "📢 Broadcast:\n"
            "Botga yuborgan xabaringizni foydalanuvchilarga "
            "tarqatish uchun xabarni yuboring.\n\n"
            "Kanalga yuborish uchun:\n"
            "/post"
        )


# =========================================================
# PARTICIPANT
# =========================================================

async def add_participant(user_id, username=""):

    con = db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO participants(user_id, username, added_count)
        VALUES (?, ?, 0)
        ON CONFLICT(user_id)
        DO UPDATE SET username=excluded.username
    """, (
        user_id,
        username or "",
    ))

    con.commit()
    con.close()


def get_participants():
    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT user_id, username, added_count
        FROM participants
        ORDER BY added_count DESC
    """)

    rows = cur.fetchall()
    con.close()

    return rows


# =========================================================
# KONKURS
# =========================================================

async def konkurs(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if await subscription_required(update, context):
        return

    user = update.effective_user

    await add_participant(
        user.id,
        user.username
    )

    me = await context.bot.get_me()

    username = me.username

    link = f"https://t.me/{username}?start=vote_{user.id}"

    keyboard = [
        [
            InlineKeyboardButton(
                "🗳 OVOZ BERISH",
                url=link
            )
        ]
    ]

    await update.message.reply_text(
        "🏆 Konkursga muvaffaqiyatli qo‘shildingiz!\n\n"
        "🔗 Sizning shaxsiy ovoz linkingiz:\n"
        f"{link}\n\n"
        "Do‘stlaringizga yuboring."
        ,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================================================
# VOTE
# =========================================================

async def vote_for_participant(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    participant_id: int
):

    voter = update.effective_user
    save_user(voter)

    if await subscription_required(update, context):
        return

    if voter.id == participant_id:

        await update.effective_message.reply_text(
            "❌ O‘zingizga ovoz bera olmaysiz."
        )

        return

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT 1
        FROM participants
        WHERE user_id=?
    """, (participant_id,))

    if not cur.fetchone():
        con.close()

        await update.effective_message.reply_text(
            "❌ Bu ishtirokchi topilmadi."
        )

        return

    cur.execute("""
        SELECT 1
        FROM votes
        WHERE voter_id=? AND participant_id=?
    """, (
        voter.id,
        participant_id,
    ))

    if cur.fetchone():
        con.close()

        await update.effective_message.reply_text(
            "⚠️ Siz bu ishtirokchiga allaqachon ovoz bergansiz."
        )

        return

    cur.execute("""
        INSERT INTO votes(voter_id, participant_id)
        VALUES (?, ?)
    """, (
        voter.id,
        participant_id,
    ))

    cur.execute("""
        UPDATE participants
        SET added_count = added_count + 1
        WHERE user_id=?
    """, (participant_id,))

    con.commit()
    con.close()

    await update.effective_message.reply_text(
        "✅ Ovoz muvaffaqiyatli berildi!"
    )


async def vote_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:
        await update.message.reply_text(
            "❌ Ishtirokchi ID ko‘rsatilmagan."
        )
        return

    try:
        participant_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ ID noto‘g‘ri."
        )
        return

    await vote_for_participant(
        update,
        context,
        participant_id
    )


# =========================================================
# TOP
# =========================================================

async def show_top(message):

    rows = get_participants()

    if not rows:
        await message.reply_text(
            "🏆 Hozircha TOP bo‘sh."
        )
        return

    text = "🏆 TOP ISHTIROKCHILAR\n\n"

    for i, (user_id, username, count) in enumerate(
        rows[:10],
        start=1
    ):

        name = f"@{username}" if username else str(user_id)

        text += (
            f"{i}. {name} — {count} ovoz\n"
        )

    await message.reply_text(text)


async def top_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if await subscription_required(update, context):
        return

    await show_top(update.message)


# =========================================================
# RANDOM
# =========================================================

async def random_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if await subscription_required(update, context):
        return

    await update.message.reply_text(
        "🎲 Random konkurs\n\n"
        "Kanalda #random formatidagi konkurs "
        "xabarini yuboring."
    )


# =========================================================
# BATL
# =========================================================

async def batl_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if await subscription_required(update, context):
        return

    await update.message.reply_text(
        "❤️ Ovoz batl tekshirish\n\n"
        "Quyidagi knopkani bosing va konkurs "
        "xabarini forward qiling."
    )


# =========================================================
# ADMIN BROADCAST
# =========================================================

async def admin_broadcast_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not is_admin(user.id):
        return

    users = get_all_users()

    sent = 0
    failed = 0

    for user_id in users:

        try:

            await update.message.copy(
                chat_id=user_id
            )

            sent += 1

        except Exception as e:

            failed += 1
            logger.warning(
                "Broadcast failed %s: %s",
                user_id,
                e
            )

    await update.message.reply_text(
        "📢 Broadcast tugadi!\n\n"
        f"✅ Yuborildi: {sent}\n"
        f"❌ Xatolik: {failed}"
    )


# =========================================================
# ADMIN → KANAL
# =========================================================

async def post_to_channel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text(
            "❌ Bu buyruq faqat admin uchun."
        )
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "📌 Kanalga yuboriladigan xabarga reply qilib "
            "/post yozing."
        )
        return

    try:

        await update.message.reply_to_message.copy(
            chat_id=CHANNEL
        )

        await update.message.reply_text(
            "✅ Xabar kanalga yuborildi."
        )

    except Exception as e:

        await update.message.reply_text(
            f"❌ Kanalga yuborishda xatolik:\n{e}"
        )


# =========================================================
# ADMIN → BOT USERS + CHANNEL
# =========================================================

async def admin_message_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not is_admin(user.id):
        return

    # Agar xabar /post buyruq emas va oddiy admin xabari bo‘lsa,
    # foydalanuvchilarga tarqatiladi.

    users = get_all_users()

    sent = 0
    failed = 0

    for user_id in users:

        if user_id == user.id:
            continue

        try:

            await update.message.copy(
                chat_id=user_id
            )

            sent += 1

        except Exception as e:

            failed += 1
            logger.warning(
                "Admin broadcast error: %s",
                e
            )

    # Kanalga ham yuborish
    channel_ok = False

    try:

        await update.message.copy(
            chat_id=CHANNEL
        )

        channel_ok = True

    except Exception as e:

        logger.warning(
            "Channel send error: %s",
            e
        )

    await update.message.reply_text(
        "📢 Admin xabari tarqatildi!\n\n"
        f"👥 Foydalanuvchilar: {sent}\n"
        f"❌ Xatolar: {failed}\n"
        f"📢 Kanal: {'✅' if channel_ok else '❌'}"
    )


# =========================================================
# ADMIN STATISTIKA
# =========================================================

async def stats_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(update.effective_user.id):
        return

    users = get_all_users()
    participants = get_participants()

    con = db()
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM votes")
    votes_count = cur.fetchone()[0]

    con.close()

    await update.message.reply_text(
        "📊 BOT STATISTIKASI\n\n"
        f"👥 Foydalanuvchilar: {len(users)}\n"
        f"🏆 Ishtirokchilar: {len(participants)}\n"
        f"🗳 Ovozlar: {votes_count}"
    )


# =========================================================
# ADMINLARNI QO‘SHISH
# =========================================================

async def add_admin_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != OWNER_ID:
        return

    if not context.args:
        await update.message.reply_text(
            "Foydalanish:\n/addadmin USER_ID"
        )
        return

    try:
        new_admin = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ ID noto‘g‘ri."
        )
        return

    ADMIN_IDS.add(new_admin)

    await update.message.reply_text(
        f"✅ {new_admin} admin qilindi."
    )


# =========================================================
# ADMINLARNI O‘CHIRISH
# =========================================================

async def remove_admin_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != OWNER_ID:
        return

    if not context.args:
        await update.message.reply_text(
            "Foydalanish:\n/removeadmin USER_ID"
        )
        return

    try:
        admin_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ ID noto‘g‘ri."
        )
        return

    if admin_id == OWNER_ID:
        await update.message.reply_text(
            "❌ Egani adminlikdan olib bo‘lmaydi."
        )
        return

    ADMIN_IDS.discard(admin_id)

    await update.message.reply_text(
        "✅ Admin olib tashlandi."
    )


# =========================================================
# XATOLIK
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.error(
        "Exception while handling update:",
        exc_info=context.error
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN topilmadi!"
        )

    if not OWNER_ID:
        raise RuntimeError(
            "OWNER_ID topilmadi!"
        )

    init_db()

    app = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    # Commands
    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("konkurs", konkurs)
    )

    app.add_handler(
        CommandHandler("random", random_command)
    )

    app.add_handler(
        CommandHandler("batl", batl_command)
    )

    app.add_handler(
        CommandHandler("top", top_command)
    )

    app.add_handler(
        CommandHandler("vote", vote_command)
    )

    app.add_handler(
        CommandHandler("stats", stats_command)
    )

    app.add_handler(
        CommandHandler("post", post_to_channel)
    )

    app.add_handler(
        CommandHandler("addadmin", add_admin_command)
    )

    app.add_handler(
        CommandHandler("removeadmin", remove_admin_command)
    )

    # Buttons
    app.add_handler(
        CallbackQueryHandler(
            menu_callback
        )
    )

    # Oddiy foydalanuvchilarni database'ga yozish
    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            save_and_ignore
        ),
        group=1
    )

    # Admin xabarlari
    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            admin_message_handler
        ),
        group=2
    )

    app.add_error_handler(
        error_handler
    )

    logger.info(
        "KonkursOvozbot ishga tushdi!"
    )

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


async def save_and_ignore(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user:
        save_user(
            update.effective_user
        )


if __name__ == "__main__":
    main()
