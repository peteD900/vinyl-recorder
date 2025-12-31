from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    context.user_data["original_text"] = user_text

    keyboard = [
        [InlineKeyboardButton("Make Capitals", callback_data="capitals")],
        [InlineKeyboardButton("Remove Spaces", callback_data="remove_spaces")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Got: {user_text}\nWhat do you want to do?", reply_markup=reply_markup
    )


async def transform_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    original = context.user_data.get("original_text", "")

    # Transform the text
    if query.data == "capitals":
        transformed = original.upper()
    elif query.data == "remove_spaces":
        transformed = original.replace(" ", "")

    # Store the transformed version for next step
    context.user_data["transformed_text"] = transformed

    # Now offer ANALYSIS buttons
    keyboard = [
        [InlineKeyboardButton("Count Characters", callback_data="count_chars")],
        [InlineKeyboardButton("Count Spaces", callback_data="count_spaces")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"Result: {transformed}\nNow what?", reply_markup=reply_markup
    )


async def analysis_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Get the transformed text from previous step
    print(context.user_data)
    text = context.user_data.get("transformed_text", "")

    if query.data == "count_chars":
        result = f"Character count: {len(text)}"
    elif query.data == "count_spaces":
        result = f"Space count: {text.count(' ')}"

    final_result = f"{context.user_data.get('original_text')}\n{text}\n{result}"

    await query.edit_message_text(final_result)


# Build app
app = Application.builder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
app.add_handler(
    CallbackQueryHandler(transform_buttons, pattern="^(capitals|remove_spaces)$")
)
app.add_handler(
    CallbackQueryHandler(analysis_buttons, pattern="^(count_chars|count_spaces)$")
)
app.run_polling()
