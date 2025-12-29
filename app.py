import os
import json
from datetime import datetime, timedelta

import pytz
import gspread
from flask import Flask, request
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from google.oauth2.service_account import Credentials

# -----------------------------
# CONFIG
# -----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

IST = pytz.timezone("Asia/Kolkata")

# -----------------------------
# GOOGLE SHEETS SETUP
# -----------------------------
service_account_info = json.loads(SERVICE_ACCOUNT_JSON)

scopes = ["https://www.googleapis.com/auth/spreadsheets"]

creds = Credentials.from_service_account_info(
    service_account_info,
    scopes=scopes
)

gspread_client = gspread.authorize(creds)
sheet = gspread_client.open_by_key(SPREADSHEET_ID).sheet1

# -----------------------------
# APP SETUP
# -----------------------------
app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()

# In-memory user state
user_state = {}

# -----------------------------
# HELPERS
# -----------------------------
def current_time_12h():
    return datetime.now(IST).strftime("%I:%M %p")

# -----------------------------
# HANDLERS
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Add Expense", callback_data="add_expense")]
    ]
    await update.message.reply_text(
        "👋 Welcome to Expense Tracker Bot\nChoose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# -----------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    # ADD EXPENSE
    if query.data == "add_expense":
        keyboard = [
            [InlineKeyboardButton("Today", callback_data="date_today")],
            [InlineKeyboardButton("Yesterday", callback_data="date_yesterday")]
        ]
        await query.message.reply_text(
            "📅 Select expense date:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # DATE SELECTION
    elif query.data.startswith("date_"):
        today = datetime.now(IST).date()

        if query.data == "date_today":
            selected_date = today
        else:
            selected_date = today - timedelta(days=1)

        user_state[user_id] = {
            "date": selected_date.strftime("%d-%b-%Y"),
            "time": current_time_12h()
        }

        await query.message.reply_text("💰 Enter amount (₹):")

    # SAVE EXPENSE
    elif query.data == "save_expense":
        data = user_state.get(user_id)

        sheet.append_row([
            data["date"],
            data["time"],
            data["amount"],
            data["note"],
            user_id
        ])

        user_state.pop(user_id, None)

        await query.message.reply_text("✅ Expense saved successfully")

    # CANCEL
    elif query.data == "cancel":
        user_state.pop(user_id, None)
        await query.message.reply_text("❌ Expense cancelled")

# -----------------------------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_id not in user_state:
        return

    # AMOUNT
    if "amount" not in user_state[user_id]:
        if not text.replace(".", "", 1).isdigit():
            await update.message.reply_text("❌ Please enter a valid amount")
            return

        user_state[user_id]["amount"] = text
        await update.message.reply_text("📝 Enter note for this expense:")
        return

    # NOTE
    if "note" not in user_state[user_id]:
        user_state[user_id]["note"] = text
        data = user_state[user_id]

        summary = (
            f"📌 Expense Summary\n\n"
            f"Date: {data['date']}\n"
            f"Time: {data['time']}\n"
            f"Amount: ₹{data['amount']}\n"
            f"Note: {data['note']}"
        )

        keyboard = [
            [InlineKeyboardButton("✅ Save", callback_data="save_expense")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
        ]

        await update.message.reply_text(
            summary,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# -----------------------------
# REGISTER HANDLERS
# -----------------------------
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

# -----------------------------
# WEBHOOK
# -----------------------------
@app.route("/webhook", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "ok"

# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.route("/")
def health():
    return "Expense Bot is running 🚀"

# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))