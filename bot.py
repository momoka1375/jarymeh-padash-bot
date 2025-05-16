import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from datetime import datetime
import os

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ذخیره‌سازی جریمه‌ها و پاداش‌ها در یک دیکشنری
data = {}

def add_entry(update: Update, context: CallbackContext, entry_type='جریمه'):
    if len(context.args) < 3:
        update.message.reply_text(f"استفاده صحیح:/{entry_type} @کاربر مبلغ توضیح")
        return

    username = context.args[0].lstrip('@')
    try:
        amount = int(context.args[1])
    except ValueError:
        update.message.reply_text("مبلغ باید عدد باشد.")
        return

    reason = ' '.join(context.args[2:])
    date = datetime.now().strftime('%Y-%m-%d')

    if username not in data:
        data[username] = []

    data[username].append({'type': entry_type, 'amount': amount, 'reason': reason, 'date': date})
    update.message.reply_text(f"{entry_type} برای {username} به مبلغ {amount} ثبت شد.")

def remove_entry(update: Update, context: CallbackContext):
    if len(context.args) < 2:
        update.message.reply_text("استفاده صحیح:/حذف @کاربر شماره")
        return

    username = context.args[0].lstrip('@')
    try:
        index = int(context.args[1]) - 1
    except ValueError:
        update.message.reply_text("شماره باید عدد باشد.")
        return

    if username not in data or index < 0 or index >= len(data[username]):
        update.message.reply_text("اطلاعات معتبر نیست.")
        return

    removed = data[username].pop(index)
    update.message.reply_text(f"ورودی حذف شد: {removed['type']} به مبلغ {removed['amount']}")

def report(update: Update, context: CallbackContext):
    if not data:
        update.message.reply_text("هیچ داده‌ای ثبت نشده.")
        return

    text = ''
    for user, entries in data.items():
        total_penalty = sum(e['amount'] for e in entries if e['type'] == 'جریمه')
        total_reward = sum(e['amount'] for e in entries if e['type'] == 'پاداش')
        text += f"@{user}: جریمه: {total_penalty} تومان پاداش: {total_reward} تومان"
        
    update.message.reply_text(text)

def main():
    TOKEN = os.getenv("7719555239:AAGBFO0gRs933ppHVP04nSmi-pikDSTLJtE")
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", lambda update, context: update.message.reply_text("ربات فعال است")))
    dp.add_handler(CommandHandler("جریمه", lambda u, c: add_entry(u, c, 'جریمه')))
    dp.add_handler(CommandHandler("پاداش", lambda u, c: add_entry(u, c, 'پاداش')))
    dp.add_handler(CommandHandler("گزارش", report))
    dp.add_handler(CommandHandler("حذف", remove_entry))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__': main()
