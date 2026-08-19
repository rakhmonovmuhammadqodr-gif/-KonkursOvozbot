import os
import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

TOKEN = os.getenv("BOT_TOKEN", "").strip()

CHANNEL = os.getenv(
    "CHANNEL_USERNAME",
    "@OPENBUJETRASMI"
).strip()

# OWNER_ID bo‘lsa ishlatadi.
# Bo‘lmasa ADMIN_ID ni ham qabul qiladi.
OWNER_ID_TEXT = (
    os.getenv("OWNER_ID", "").strip()
    or os.getenv("ADMIN_ID", "").strip()
)

try:
    OWNER_ID = int(OWNER_ID_TEXT) if OWNER_ID_TEXT else 0
except ValueError:
    OWNER_ID = 0


# ADMIN_IDS ham, ADMIN_ID ham ishlaydi
ADMIN_IDS = set()

admin_ids_text = os.getenv("ADMIN_IDS", "").strip()

if admin_ids_text:
    for item in admin_ids_text.replace(",", ";").split(";"):
        item = item.strip()

        if not item:
            continue

        try:
            ADMIN_IDS.add(int(item))
        except ValueError:
            pass


single_admin = os.getenv("ADMIN_ID", "").strip()

if single_admin:
    try:
        ADMIN_IDS.add(int(single_admin))
    except ValueError:
        pass


if OWNER_ID:
    ADMIN_IDS.add(OWNER_ID)


DB_FILE = "bot.db"


# =========================================================
# LOG
# =========================================================

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
            username TEXT DEFAULT '',
            first_name TEXT DEFAULT '',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
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

    con.commit()
    con.close()


def save_user(user):
    if not user:
        return

    con = db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO users (
            user_id,
            username,
            first_name
        )
        VALUES (?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name
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

    cur.execute(
        "SELECT user_id FROM users"
    )

    rows = cur.fetchall()

    con.close()

    return [row[0] for row in rows]


# =========================================================
# ADMIN
# =========================================================

def is_admin(user_id):
    return user_id in ADMIN_IDS


# =========================================================
# OBUNA
# =========================================================

async def is_subscribed(context, user_id):
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
        logger.warning(
            "Subscription check error: %s",
            e
        )

        return False


async def subscription_required(update, context):
    user = update.effective_user

    if not user:
        return False

    # Adminlardan obuna talab qilinmaydi
    if is_admin(user.id):
        return False

    subscribed = await is_subscribed(
        context,
        user.id
    )

    if subscribed:
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
        "⚠️ Botdan foydalanish uchun avval kanalga "
        "obuna bo‘ling.\n\n"
        "Obuna bo‘lgach, «✅ Tekshirish» tugmasini bosing."
    )

    if update.callback_query:
        await update.callback_query.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif update.effective_message:
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

    if not user:
        return

    save_user(user)

    # Referral / vote link
    if context.args:

        argument = context.args[0]

        if argument.startswith("vote_"):

            try:
                participant_id = int(
                    argument.replace("vote_", "")
                )

                await vote_for_participant(
                    update,
                    context,
                    participant_id
                )

                return

            except ValueError:
                pass

    if await subscription_required(
        update,
        context
    ):
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

👇 Kerakli bo‘limni tanlang:"""

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

async def menu_callback(update, context):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    if query.data == "check_sub":

        subscribed = await is_subscribed(
            context,
            user.id
        )

        if subscribed:
            await query.message.reply_text(
                "✅ Obuna tasdiqlandi!\n\n"
                "/start buyrug‘ini bosing."
            )
        else:
            await query.message.reply_text(
                "❌ Hali kanalga obuna bo‘lmagansiz."
            )

        return

    if query.data == "admin_menu":

        if not is_admin(user.id):
            await query.message.reply_text(
                "❌ Sizda admin huquqi yo‘q."
            )
            return

        await query.message.reply_text(
            "👑 ADMIN PANEL\n\n"
            "📢 Oddiy xabar yuborsangiz:\n"
            "→ barcha bot foydalanuvchilariga yuboriladi\n"
            "→ kanalga ham yuboriladi\n\n"
            "📊 /stats — statistika\n"
            "🏆 /top — TOP\n"
            "📢 /post — reply qilingan xabarni kanalga yuborish"
        )

        return

    if await subscription_required(
        update,
        context
    ):
        return

    if query.data == "menu_konkurs":

        await query.message.reply_text(
            "🏆 KONKURS\n\n"
            "Konkursda qatnashish uchun "
            "/konkurs buyrug‘idan foydalaning."
        )

    elif query.data == "menu_random":

        await query.message.reply_text(
            "🎲 RANDOM KONKURS\n\n"
            "#random\n"
            "salom yangi konkurs boshlandik\n"
            "yutuq nft emas\n"
            "shartlari\n"
            "@kanal\n"
            "#soni 3"
        )

    elif query.data == "menu_batl":

        await query.message.reply_text(
            "❤️ LIKE BATL\n\n"
            "Konkurs xabarini forward qilib "
            "batl natijasini tekshirishingiz mumkin."
        )

    elif query.data == "menu_top":

        await show_top(
            query.message
        )


# =========================================================
# PARTICIPANTS
# =========================================================

def add_participant(user_id, username=""):

    con = db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO participants (
            user_id,
            username,
            added_count
        )
        VALUES (?, ?, 0)
        ON CONFLICT(user_id)
        DO UPDATE SET
            username = excluded.username
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
        SELECT
            user_id,
            username,
            added_count
        FROM participants
        ORDER BY added_count DESC
    """)

    rows = cur.fetchall()

    con.close()

    return rows


# =========================================================
# KONKURS
# =========================================================

async def konkurs(update, context):

    if await subscription_required(
        update,
        context
    ):
        return

    user = update.effective_user

    add_participant(
        user.id,
        user.username
    )

    bot = await context.bot.get_me()

    link = (
        f"https://t.me/{bot.username}"
        f"?start=vote_{user.id}"
    )

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
        "🔗 Sizning shaxsiy linkingiz:\n"
        f"{link}\n\n"
        "Linkni do‘stlaringizga yuboring.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================================================
# VOTE
# =========================================================

async def vote_for_participant(
    update,
    context,
    participant_id
):

    voter = update.effective_user

    save_user(voter)

    if await subscription_required(
        update,
        context
    ):
        return

    if voter.id == participant_id:

        await update.effective_message.reply_text(
            "❌ O‘zingizga ovoz bera olmaysiz."
        )

        return

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT user_id
        FROM participants
        WHERE user_id = ?
    """, (participant_id,))

    participant = cur.fetchone()

    if not participant:

        con.close()

        await update.effective_message.reply_text(
            "❌ Bu ishtirokchi topilmadi."
        )

        return

    cur.execute("""
        SELECT 1
        FROM votes
        WHERE voter_id = ?
        AND participant_id = ?
    """, (
        voter.id,
        participant_id
    ))

    already_voted = cur.fetchone()

    if already_voted:

        con.close()

        await update.effective_message.reply_text(
            "⚠️ Siz bu ishtirokchiga "
            "allaqachon ovoz bergansiz."
        )

        return

    cur.execute("""
        INSERT INTO votes (
            voter_id,
            participant_id
        )
        VALUES (?, ?)
    """, (
        voter.id,
        participant_id
    ))

    cur.execute("""
        UPDATE participants
        SET added_count = added_count + 1
        WHERE user_id = ?
    """, (participant_id,))

    con.commit()
    con.close()

    await update.effective_message.reply_text(
        "✅ Ovoz muvaffaqiyatli berildi!"
    )


async def vote_command(update, context):

    if not context.args:

        await update.message.reply_text(
            "❌ Foydalanish:\n/vote USER_ID"
        )

        return

    try:
        participant_id = int(
            context.args[0]
        )

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

    for number, row in enumerate(
        rows[:10],
        start=1
    ):

        user_id, username, count = row

        if username:
            name = f"@{username}"
        else:
            name = str(user_id)

        text += (
            f"{number}. {name} — "
            f"{count} ovoz\n"
        )

    await message.reply_text(
        text
    )


async def top_command(update, context):

    if await subscription_required(
        update,
        context
    ):
        return

    await show_top(
        update.message
    )


# =========================================================
# RANDOM
# =========================================================

async def random_command(update, context):

    if await subscription_required(
        update,
        context
    ):
        return

    await update.message.reply_text(
        "🎲 RANDOM KONKURS\n\n"
        "Kanalda #random formatidagi "
        "konkurs xabarini yuboring."
    )


# =========================================================
# BATL
# =========================================================

async def batl_command(update, context):

    if await subscription_required(
        update,
        context
    ):
        return

    await update.message.reply_text(
        "❤️ OVOZ BATL\n\n"
        "Quyidagi knopkani bosing va "
        "konkurs xabarini forward qiling."
    )


# =========================================================
# ADMIN → USERS + CHANNEL
# =========================================================

async def admin_message_handler(
    update,
    context
):

    user = update.effective_user

    if not user:
        return

    if not is_admin(user.id):
        return

    message = update.effective_message

    if not message:
        return

    users = get_all_users()

    sent = 0
    failed = 0

    # Foydalanuvchilarga
    for user_id in users:

        if user_id == user.id:
            continue

        try:

            await message.copy(
                chat_id=user_id
            )

            sent += 1

        except Exception as e:

            failed += 1

            logger.warning(
                "User broadcast error %s: %s",
                user_id,
                e
            )

    # Kanalga
    channel_sent = False

    try:

        await message.copy(
            chat_id=CHANNEL
        )

        channel_sent = True

    except Exception as e:

        logger.warning(
            "Channel send error: %s",
            e
        )

    await message.reply_text(
        "📢 Xabar yuborildi!\n\n"
        f"👥 Foydalanuvchilar: {sent}\n"
        f"❌ Xatolar: {failed}\n"
        f"📢 Kanal: "
        f"{'✅' if channel_sent else '❌'}"
    )


# =========================================================
# ADMIN → CHANNEL /post
# =========================================================

async def post_command(update, context):

    user = update.effective_user

    if not is_admin(user.id):

        await update.message.reply_text(
            "❌ Bu buyruq faqat admin uchun."
        )

        return

    if not update.message.reply_to_message:

        await update.message.reply_text(
            "📌 Kanalga yuboriladigan xabarga "
            "reply qilib /post yozing."
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

        logger.exception(e)

        await update.message.reply_text(
            "❌ Kanalga yuborishda xatolik."
        )


# =========================================================
# ADMIN STATS
# =========================================================

async def stats_command(update, context):

    user = update.effective_user

    if not is_admin(user.id):
        return

    users = get_all_users()
    participants = get_participants()

    con = db()
    cur = con.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM votes"
    )

    votes = cur.fetchone()[0]

    con.close()

    await update.message.reply_text(
        "📊 BOT STATISTIKASI\n\n"
        f"👥 Foydalanuvchilar: {len(users)}\n"
        f"🏆 Ishtirokchilar: {len(participants)}\n"
        f"🗳 Ovozlar: {votes}"
    )


# =========================================================
# ADMIN QO‘SHISH
# =========================================================

async def add_admin_command(
    update,
    context
):

    user = update.effective_user

    if user.id != OWNER_ID:
        return

    if not context.args:

        await update.message.reply_text(
            "/addadmin USER_ID"
        )

        return

    try:
        new_admin = int(
            context.args[0]
        )

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
# ADMIN O‘CHIRISH
# =========================================================

async def remove_admin_command(
    update,
    context
):

    user = update.effective_user

    if user.id != OWNER_ID:
        return

    if not context.args:

        await update.message.reply_text(
            "/removeadmin USER_ID"
        )

        return

    try:
        admin_id = int(
            context.args[0]
        )

    except ValueError:

        await update.message.reply_text(
            "❌ ID noto‘g‘ri."
        )

        return

    if admin_id == OWNER_ID:

        await update.message.reply_text(
            "❌ Egani o‘chirib bo‘lmaydi."
        )

        return

    ADMIN_IDS.discard(
        admin_id
    )

    await update.message.reply_text(
        "✅ Admin olib tashlandi."
    )


# =========================================================
# ERROR
# =========================================================

async def error_handler(
    update,
    context
):

    logger.error(
        "Bot error:",
        exc_info=context.error
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if not TOKEN:

        raise RuntimeError(
            "BOT_TOKEN topilmadi! "
            "GitHub Secrets'da BOT_TOKEN yarating."
        )

    if not OWNER_ID:

        raise RuntimeError(
            "OWNER_ID yoki ADMIN_ID topilmadi! "
            "GitHub Secrets'da OWNER_ID yoki ADMIN_ID yarating."
        )

    init_db()

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
            "konkurs",
            konkurs
        )
    )

    app.add_handler(
        CommandHandler(
            "random",
            random_command
        )
    )

    app.add_handler(
        CommandHandler(
            "batl",
            batl_command
        )
    )

    app.add_handler(
        CommandHandler(
            "top",
            top_command
        )
    )

    app.add_handler(
        CommandHandler(
            "vote",
            vote_command
        )
    )

    app.add_handler(
        CommandHandler(
            "stats",
            stats_command
        )
    )

    app.add_handler(
        CommandHandler(
            "post",
            post_command
        )
    )

    app.add_handler(
        CommandHandler(
            "addadmin",
            add_admin_command
        )
    )

    app.add_handler(
        CommandHandler(
            "removeadmin",
            remove_admin_command
        )
    )

    # Tugmalar
    app.add_handler(
        CallbackQueryHandler(
            menu_callback
        )
    )

    # Har qanday oddiy xabar:
    # foydalanuvchini bazaga saqlaydi.
    #
    # Admin xabari bo‘lsa:
    # admin_message_handler ham ishlaydi.
    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            save_user_handler
        ),
        group=1
    )

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
        "KonkursOvozbot ishga tushmoqda..."
    )

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# =========================================================
# USER SAVE HANDLER
# =========================================================

async def save_user_handler(
    update,
    context
):

    if update.effective_user:

        save_user(
            update.effective_user
        )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    main()
