import os
import logging
from anthropic import Anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

# ─── Настройки ───────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

# Системный промпт — измени под себя
SYSTEM_PROMPT = "Ты полезный ассистент. Отвечай кратко и по делу."

# ─── Инициализация ────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

client = Anthropic(api_key=ANTHROPIC_API_KEY)

# История диалога для каждого пользователя (хранится в памяти)
user_histories: dict[int, list] = {}


# ─── Команды ─────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []  # сброс истории
    await update.message.reply_text(
        "Привет! Я бот на базе Claude. Просто напиши мне что-нибудь 👋\n"
        "Команда /reset — сбросить историю диалога."
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text("История диалога сброшена ✅")


# ─── Обработка сообщений ──────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    # Инициализируем историю если нет
    if user_id not in user_histories:
        user_histories[user_id] = []

    # Добавляем сообщение пользователя в историю
    user_histories[user_id].append({"role": "user", "content": user_text})

    # Ограничиваем историю последними 20 сообщениями (10 парами)
    if len(user_histories[user_id]) > 20:
        user_histories[user_id] = user_histories[user_id][-20:]

    try:
        # Показываем "печатает..."
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        # Запрос к Claude
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=user_histories[user_id],
        )

        reply = response.content[0].text

        # Добавляем ответ в историю
        user_histories[user_id].append({"role": "assistant", "content": reply})

        await update.message.reply_text(reply)

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуй ещё раз.")


# ─── Запуск ───────────────────────────────────────────────────
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен...")
    app.run_polling()
