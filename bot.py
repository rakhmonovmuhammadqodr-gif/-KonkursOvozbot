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

users = set()
participants = {}
votes = set()
contest_active = False
contest_message_id = None
contest_chat_id = None


def get_results():
    if not participants:
        return "Hozircha qatnashchilar yo‘q."

    ranking = sorted(
        participants.items(),
        key=lambda x: x[1],
        reverse=True
    )

    lines = []

    for i, (username, count) in enumerate(ranking, 1):
        if i == 1:
            prefix = "🥇"
        elif i == 2:
            prefix = "🥈"
        elif i == 3:
            prefix = "🥉"
        else:
            prefix = f"{i}."

        lines.append(f"{prefix} @{username} — {count}")

    return "\n".join(lines)


def contest_text():
    return (
        "🏆 BATL BOSHLANDI! 🥳\n\n"
        "❗️Konkurs shartlari — kanalga obuna bo‘lish "
        "va do‘stlaringiz sizga ovoz berishini so‘rashdan iborat.\n\n"
        "⚠️ Agar kanalga qo‘shilib ovoz berib chiqib ketsa, "
        "ovozi avtomatik bekor qilinadi.\n\n"
        "🎁 Konkursga qo‘yilgan yutuqlar: 🤫\n\n"
        "📊 KONKURS NATIJALARI\n\n"
        f"{get_results()}"
    )


def keyboard():
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


async def update_contest_message(context):
    if contest_chat_id and contest_message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=contest_chat_id,
                message_id=contest_message_id,
                text=contest_text(),
                reply_markup=keyboard()
            )
        except Exception as e:
            logging.error("Natijani yangilash xatosi: %s", e)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user:
        return

    users.add(user.id)

    if context.args and context.args[0].startswith("vote_"):
        target = context.args[0][5:].lower()

        if not contest_active:
            await update.message.reply_text(
                "⛔ Hozircha faol konkurs yo‘q."
            )
            return

        if target not in participants:
            await update.message.reply_text(
                "❌ Bu ishtirokchi konkursda yo‘q."
            )
            return

        await update.message.reply_text(
            "🏆 OVOZ BERISH\n\n"
            "❗ Avval kanalga obuna bo‘ling.\n"
            "Keyin 🗳 OVOZ BERISH tugmasini bosing.",
            reply_markup=InlineKeyboardMarkup([
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
        )
        return

    await update.message.reply_text(
        "✅ Xush kelibsiz!\n\n"
        "🤖 Ovoz Battle Pro ishga tushdi!\n\n"
        "👇 Kerakli bo‘limni tanlang:",
        reply_markup=InlineKeyboardMarkup([
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
            ]
        ])
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
            "❗ Telegram username qo‘ying.",
            show_alert=True
        )
        return

    username = user.username.lower()

    if username not in participants:
        participants[username] = 0

    me = await context.bot.get_me()

    link = f"https://t.me/{me.username}?start=vote_{username}"

    await query.edit_message_text(
        "🎉 KONKURSGA QO‘SHILDINGIZ!\n\n"
        f"👤 @{username}\n"
        f"🗳 Ovozlar: {participants[username]}\n\n"
        "🔗 Sizning shaxsiy ovoz linkingiz:\n"
        f"{link}\n\n"
        "📢 Shu linkni do‘stlaringizga yuboring.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "📊 NATIJALAR",
                    callback_data="results"
                )
            ]
        ])
    )

    await update_contest_message(context)


async def results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🏆 KONKURS NATIJALARI\n\n"
        + get_results(),
        reply_markup=keyboard()
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

    except Exception as e:
        logging.error("Obuna tekshirish xatosi: %s", e)

        await query.answer(
            "⚠️ Kanal obunasini tekshirib bo‘lmadi.",
            show_alert=True
        )
        return

    vote_key = (voter.id, target)

    if vote_key in votes:
        await query.answer(
            "⛔ Siz bu ishtirokchiga allaqachon ovoz bergansiz.",
            show_alert=True
        )
        return

    votes.add(vote_key)
    participants[target] += 1

    await query.answer("✅ Ovoz qabul qilindi!")

    await query.edit_message_text(
        "✅ OVOZ QABUL QILINDI!\n\n"
        f"🏆 @{target}\n"
        f"🗳 Jami ovoz: {participants[target]}"
    )

    await update_contest_message(context)


async def konkurs_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global contest_active
    global contest_message_id
    global contest_chat_id

    post = update.channel_post

    if not post:
        return

    if post.chat.username:
        if ("@" + post.chat.username).lower() != CHANNEL.lower():
            return

    text = post.text or post.caption or ""

    if text.strip().lower() != "#konkurs":
        return

    contest_active = True
    participants.clear()
    votes.clear()

    sent = await context.bot.send_message(
        chat_id=post.chat_id,
        text=contest_text(),
        reply_markup=keyboard()
    )

    contest_message_id = sent.message_id
    contest_chat_id = sent.chat_id


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏆 TOP 10\n\n" + get_results()
    )


async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global contest_active

    if update.effective_user.id != ADMIN_ID:
        return

    contest_active = False

    await update.message.reply_text(
        "🏆 KONKURS YAKUNLANDI!\n\n"
        + get_results()
    )


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text(
            "📢 Foydalanish:\n/broadcast Xabaringiz"
        )
        return

    text = " ".join(context.args)

    sent = 0

    for user_id in list(users):
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=text
            )
            sent += 1
        except Exception:
            pass

    await update.message.reply_text(
        f"✅ Xabar {sent} ta foydalanuvchiga yuborildi."
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        "📊 STATISTIKA\n\n"
        f"👥 Foydalanuvchilar: {len(users)}\n"
        f"🏆 Qatnashchilar: {len(participants)}\n"
        f"🗳 Ovozlar: {len(votes)}\n"
        f"🔥 Konkurs: "
        f"{'Faol 🟢' if contest_active else 'Yopiq 🔴'}"
    )


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN topilmadi!")

    if ADMIN_ID == 0:
        raise RuntimeError("ADMIN_ID sozlanmagan!")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("finish", finish))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stats", stats))

    app.add_handler(
        CallbackQueryHandler(join, pattern=r"^join$")
    )

    app.add_handler(
        CallbackQueryHandler(results, pattern=r"^results$")
    )

    app.add_handler(
        CallbackQueryHandler(vote, pattern=r"^vote:")
    )

    app.add_handler(
        MessageHandler(
            filters.ChatType.CHANNEL
            & filters.Regex(r"(?i)^#konkurs$"),
            konkurs_post
        )
    )

    print("🏆 Ovoz Battle Pro ishga tushdi!")

    app.run_polling()


if __name__ == "__main__":
    main()
