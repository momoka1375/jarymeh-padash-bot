import logging
import csv
import os
from datetime import datetime
from telegram import Update, ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# تنظیم لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

BOT_TOKEN = os.getenv('BOT_TOKEN')

DATA_FILE = 'penalties.csv'

# بررسی مدیر بودن کاربر
async def is_admin(update: Update, user_id: int) -> bool:
    chat = update.effective_chat
    member = await chat.get_member(user_id)
    return member.status in ['administrator', 'creator']

# ثبت یک ردیف در فایل CSV
def append_to_csv(row):
    file_exists = os.path.isfile(DATA_FILE)
    with open(DATA_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['id', 'date', 'username', 'type', 'amount', 'reason'])
        writer.writerow(row)

# خواندن کل داده‌ها
def read_data():
    if not os.path.isfile(DATA_FILE):
        return []
    with open(DATA_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

# نوشتن کل داده‌ها (برای حذف و اصلاح)
def write_data(data):
    with open(DATA_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'date', 'username', 'type', 'amount', 'reason'])
        writer.writeheader()
        writer.writerows(data)

# گرفتن شناسه بعدی
def next_id(data):
    if not data:
        return 1
    return max(int(row['id']) for row in data) + 1

# دستور جریمه و پاداش (نوع: 'جریمه' یا 'پاداش')
async def handle_penalty(update: Update, context: ContextTypes.DEFAULT_TYPE, penalty_type: str):
    user = update.effective_user
    if not await is_admin(update, user.id):
        await update.message.reply_text("فقط مدیران می‌توانند این دستور را اجرا کنند.")
        return

    if len(context.args) < 3:
        await update.message.reply_text(f"فرمت درست: /{penalty_type} @username مبلغ دلیل")
        return

    username = context.args[0]
    if not username.startswith('@'):
        await update.message.reply_text("لطفاً نام کاربری را با @ وارد کنید.")
        return
    try:
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("مبلغ باید عدد صحیح باشد.")
        return

    reason = ' '.join(context.args[2:])
    data = read_data()
    new_id = next_id(data)
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    append_to_csv([new_id, date_str, username, penalty_type, amount, reason])
    await update.message.reply_text(f"{penalty_type} ثبت شد:\nID: {new_id}\nکاربر: {username}\nمبلغ: {amount}\nدلیل: {reason}")

async def jarihme_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_penalty(update, context, 'جریمه')

async def padosh_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_penalty(update, context, 'پاداش')

# دستور مجموع
async def majmo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if len(context.args) != 1:
        await update.message.reply_text("فرمت درست: /مجموع @username")
        return
    username = context.args[0]
    if not username.startswith('@'):
        await update.message.reply_text("لطفاً نام کاربری را با @ وارد کنید.")
        return

    data = read_data()
    total_jarihme = sum(int(row['amount']) for row in data if row['username'] == username and row['type'] == 'جریمه')
    total_padosh = sum(int(row['amount']) for row in data if row['username'] == username and row['type'] == 'پاداش')
    net = total_padosh - total_jarihme
    text = f"گزارش برای {username}:\nجریمه کل: {total_jarihme}\nپاداش کل: {total_padosh}\nخالص: {net}"
    await update.message.reply_text(text)
# دستور گزارش ماه (ارسال فایل CSV)
async def report_month_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(update, user.id):
        await update.message.reply_text("فقط مدیران می‌توانند این دستور را اجرا کنند.")
        return

    if not os.path.isfile(DATA_FILE):
        await update.message.reply_text("هنوز داده‌ای ثبت نشده است.")
        return

    await update.message.reply_document(open(DATA_FILE, 'rb'), filename='penalties.csv')

# حذف بر اساس ID
async def delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(update, user.id):
        await update.message.reply_text("فقط مدیران می‌توانند این دستور را اجرا کنند.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("فرمت درست: /حذف ID")
        return

    try:
        del_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("شناسه باید عدد صحیح باشد.")
        return

    data = read_data()
    new_data = [row for row in data if int(row['id']) != del_id]
    if len(new_data) == len(data):
        await update.message.reply_text("شناسه پیدا نشد.")
        return

    write_data(new_data)
    await update.message.reply_text(f"آیتم با شناسه {del_id} حذف شد.")

# اصلاح بر اساس ID
async def edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(update, user.id):
        await update.message.reply_text("فقط مدیران می‌توانند این دستور را اجرا کنند.")
        return

    if len(context.args) < 3:
        await update.message.reply_text("فرمت درست: /اصلاح ID مبلغ دلیل")
        return

    try:
        edit_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("شناسه و مبلغ باید عدد صحیح باشند.")
        return

    reason = ' '.join(context.args[2:])
    data = read_data()
    found = False
    for row in data:
        if int(row['id']) == edit_id:
            row['amount'] = amount
            row['reason'] = reason
            found = True
            break
    if not found:
        await update.message.reply_text("شناسه پیدا نشد.")
        return

    write_data(data)
    await update.message.reply_text(f"آیتم با شناسه {edit_id} اصلاح شد.")

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ربات جریمه-پاداش فعال است.\nدستورات:\n"
                                    "/جریمه @user مبلغ دلیل\n"
                                    "/پاداش @user مبلغ دلیل\n"
                                    "/مجموع @user\n"
                                    "/گزارش_ماه\n"
                                    "/حذف id\n"
                                    "/اصلاح id مبلغ دلیل")

if name == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("جریمه", jarihme_handler))
    app.add_handler(CommandHandler("پاداش", padosh_handler))
    app.add_handler(CommandHandler("مجموع", majmo_handler))
    app.add_handler(CommandHandler("گزارش_ماه", report_month_handler))
    app.add_handler(CommandHandler("حذف", delete_handler))
    app.add_handler(CommandHandler("اصلاح", edit_handler))

    print("Bot is running...")
    app.run_polling()