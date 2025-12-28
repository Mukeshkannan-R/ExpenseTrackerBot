import logging
import os
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from sheets_service import add_expense_row
import aiohttp.web
from aiohttp import web

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATE, CURRENCY, AMOUNT, CATEGORY, NOTE = range(5)

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8107075959:AAGwtrJnL4LAuXW5_R9HQxisg-Ur0SUQ-bo')
WEBHOOK_PATH = f"/webhook/{TOKEN}"

# ALL YOUR HANDLERS (UNCHANGED - copy exactly)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Expense Bot ready!\n/add - Add expense")

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    calendar, step = DetailedTelegramCalendar().build()
    await update.message.reply_text("📅 Select date:", reply_markup=calendar)
    return DATE

async def date_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    result, key, step = DetailedTelegramCalendar().process(query.data)
    if not result and key:
        await query.edit_message_text(f"Select date: {LSTEP[step]}", reply_markup=key)
    elif result:
        context.user_data["date"] = result.strftime("%Y-%m-%d")
        keyboard = [[InlineKeyboardButton("₹ INR", callback_data="INR"), InlineKeyboardButton("$ USD", callback_data="USD"), InlineKeyboardButton("€ EUR", callback_data="EUR")]]
        await query.edit_message_text(
            f"📅 Date: {context.user_data['date']}\n💰 Choose currency:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CURRENCY

async def currency_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    currency_map = {"INR": "₹", "USD": "$", "EUR": "€"}
    context.user_data["currency"] = currency_map[query.data]
    await query.edit_message_text(
        f"💰 Currency: {context.user_data['currency']}\nEnter amount (e.g. 250):"
    )
    return AMOUNT

async def amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        context.user_data["amount"] = amount
        keyboard = [
            [InlineKeyboardButton("🍚 Food", callback_data="Food"), InlineKeyboardButton("🚗 Transport", callback_data="Transport")],
            [InlineKeyboardButton("💡 Bills", callback_data="Bills"), InlineKeyboardButton("❓ Other", callback_data="Other")]
        ]
        await update.message.reply_text("🏷️ Choose category:", reply_markup=InlineKeyboardMarkup(keyboard))
        return CATEGORY
    except ValueError:
        await update.message.reply_text("❌ Enter valid number only")
        return AMOUNT

async def category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["category"] = query.data
    await query.edit_message_text("📝 Optional note (or send '-' to skip):")
    return NOTE

async def note_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note = update.message.text if update.message.text != "-" else ""
    context.user_data["note"] = note
    
    user = update.message.from_user
    data = context.user_data
    
    success = add_expense_row(
        data["date"], data["amount"], data["currency"],
        data["category"], note, user.id, user.username
    )
    
    await update.message.reply_text(
        f"✅ Saved!\n📅 {data['date']}\n💰 {data['currency']}{data['amount']}\n🏷️ {data['category']}"
        if success else "❌ Save failed - check logs"
    )
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled")
    context.user_data.clear()
    return ConversationHandler.END

# FIXED WEBHOOK HANDLER (Direct Bot + Application)
async def telegram_webhook_handler(request):
    json_data = await request.json()
    update = Update.de_json(json_data, request.app['bot'])
    await request.app['application'].process_update(update)
    return web.json_response({}, status=200)

# FIXED STARTUP (No ApplicationBuilder - Pure webhook)
async def on_startup(app):
    app['bot'] = Bot(token=TOKEN)
    app['application'] = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_command)],
        states={
            DATE: [CallbackQueryHandler(date_handler)],
            CURRENCY: [CallbackQueryHandler(currency_handler)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_handler)],
            CATEGORY: [CallbackQueryHandler(category_handler)],
            NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, note_handler)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    
    app['application'].add_handler(CommandHandler("start", start))
    app['application'].add_handler(conv_handler)
    
    await app['application'].initialize()
    await app['application'].start()
    logger.info("🤖 PURE WEBHOOK BOT READY!")

async def on_shutdown(app):
    await app['application'].stop()
    await app['application'].shutdown()

async def set_webhook(request):
    webhook_url = f"https://{request.host}{WEBHOOK_PATH}"
    await request.app['bot'].set_webhook(url=webhook_url)
    return web.json_response({"status": "success", "webhook_url": webhook_url})

def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, telegram_webhook_handler)
    app.router.add_get('/health', lambda req: web.json_response({"status": "ok"}))
    app.router.add_post('/setwebhook', set_webhook)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    port = int(os.getenv('PORT', 10000))
    web.run_app(app, host='0.0.0.0', port=port)

if __name__ == "__main__":
    main()