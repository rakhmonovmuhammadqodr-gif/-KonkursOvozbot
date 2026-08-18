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

# Konkurs o'tkaziladigan kanal username'i
CHANNEL = "@KanalUsername"

# Kanal adminining Telegram ID'si
ADMIN_ID = 123456789

users = set()
participants = {}
votes = set()
contest_active = False

logging.basicConfig(level=logging.INFO)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    users.add(user.id)

    args = context.args

    # Referral orqali kelgan odam
    if args and args[0].startswith("vote_"):
        username = args[0][5:]

        if contest_active:
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
                        callback_data=f"vote:{username}"
                    )
                ]
            ]

            await update.message.reply_text(
                "🏆 Ovoz Battle\n\n"
                "Ovoz berish uchun avval kanalga obuna bo‘ling.\n"
                "Keyin 🗳 Ovoz berish tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

    keyboard = [
        [InlineKeyboardButton("🏆 Konkursga qo‘shilish", callback_data="join")]
    ]

    await update.message.reply_text(
        "🏆 Ovoz Battle Pro\n\n"
        "Konkursda qatnashish uchun quyidagi tugmani bosing.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    users.add(user.id)

    if not contest_active:
        await query.edit_message_text(
            "⛔ Hozircha faol konkurs yo‘q."
        )
        return

    username = user.username

    if not username:
        await query.edit_message_text(
            "❗ Ovoz linki yaratish uchun Telegram username'ingiz bo‘lishi kerak."
        )
        return

    participants[user.username] = 0

    me = await context.bot.get_me()

    link = f"https://t.me/{me.username}?start=vote_{user.username}"

    await query.edit_message_text(
        "🎉 Siz konkursga qo‘shildingiz!\n\n"
        f"🔗 Sizning ovoz linkingiz:\n{link}\n\n"
        "📢 Shu linkni do‘stlaringizga yuboring.\n"
        "Har bir haqiqiy ovoz sizning reytingingizni oshiradi."
    )


async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    voter = query.from_user
    target = query.data.split(":", 1)[1]

    if not contest_active:
        await query.edit_message_text("⛔ Konkurs tugagan.")
        return

    try:
        member = await context.bot.get_chat_member(
            CHANNEL,
            voter.id
        )

        if member.status in ["left", "kicked"]:
            await query.answer(
                "❗ Avval kanalga obuna bo‘ling!",
                show_alert=True
            )
            return

    except Exception:
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

    if target not in participants:
        participants[target] = 0

    participants[target] += 1

    await query.edit_message_text(
        "✅ Ovozingiz qabul qilindi!\n\n"
        "🏆 Konkurs ishtirokchisiga ovoz berdingiz."
    )


async def konkurs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global contest_active

    if update.effective_user.id != ADMIN_ID:
        return

    if update.message.chat.type not in ["channel", "supergroup"]:
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

    await update.message.reply_text(
        "🏆 BATTLE BOSHLANDI! 🥳\n\n"
        "❗️Konkurs sharti — shu kanalga obuna bo‘lish "
        "va do‘stlaringizdan sizga ovoz berishini so‘rash.\n\n"
        "⚠️ Kanalga qo‘shilib, ovoz berib chiqib ketilsa, "
        "ovoz avtomatik bekor qilinadi.\n\n"
        "🎁 Konkurs yutuqlari hozircha sir 🤫\n\n"
        "➕ Konkursga qo‘shilish uchun quyidagi tugmani bosing 👇",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not participants:
        await update.message.reply_text(
            "🏆 Hozircha hech kim ovoz olmagan."
        )
        return

    ranking = sorted(
        participants.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    text = "🏆 TOP 10\n\n"

    for i, (username, count) in enumerate(ranking, 1):
        text += f"{i}. @{username} — {count} 🗳\n"

    await update.message.reply_text(text)


async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global contest_active

    if update.effective_user.id != ADMIN_ID:
        return

    contest_active = False

    ranking = sorted(
        participants.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    text = "🏆 KONKURS YAKUNLANDI!\n\n"

    if ranking:
        for i, (username, count) in enumerate(ranking, 1):
            text += f"{i}. @{username} — {count} 🗳\n"
    else:
        text += "Hali ovozlar yo‘q."

    await update.message.reply_text(text)


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
                user_id,
                text
            )
            sent += 1
        except Exception:
            pass

    await update.message.reply_text(
        f"✅ Xabar {sent} ta foydalanuvchiga yuborildi."
    )


def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN topilmadi!")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("finish", finish))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.add_handler(
        CallbackQueryHandler(join, pattern="^join$")
    )

    app.add_handler(
        CallbackQueryHandler(vote, pattern="^vote:")
    )

    app.add_handler(
        MessageHandler(
            filters.Regex(r"^#konkurs$"),
            konkurs
        )
    )

    print("🏆 Ovoz Battle Pro ishga tushdi!")

    app.run_polling()


if __name__ == "__main__":
    main()
