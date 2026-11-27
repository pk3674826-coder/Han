import os
import subprocess
import sys
import psutil
import telebot
from telebot import types

# ================= CONFIGURATION =================
BOT_TOKEN = "8894883599:AAH94oPizhJ6YVqJNu-xh-92wLOlSYLLOcM"
ADMIN_ID = 8937162965
MAX_BOTS = 5                                # အများဆုံး Run ခွင့်ပြုမည့် Bot အရေအတွက်
UPLOAD_DIR = "hosted_bots"                  # .py ဖိုင်များ သိမ်းမည့် Folder
# =================================================

bot = telebot.TeleBot(BOT_TOKEN)

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# လက်ရှိ Run နေသော Process များကို မှတ်ထားရန် {filename: subprocess.Popen}
running_processes = {}

def is_admin(message):
    return message.from_user.id == ADMIN_ID

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("📊 System & Bot Stats")
    btn2 = types.KeyboardButton("📂 Manage Running Bots")
    markup.add(btn1, btn2)
    return markup

# /start Command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if not is_admin(message):
        return bot.reply_to(message, "⛔ သင်သည် ဤ Bot ကို အသုံးပြုခွင့် မရှိပါ။")
    
    welcome_text = (
        "🤖 **Python VPS Hosting Bot မှ ကြိုဆိုပါတယ်!**\n\n"
        f"📌 **အများဆုံး Run နိုင်သည့် အရေအတွက်:** {MAX_BOTS} ခု\n"
        "📤 **အသုံးပြုနည်း:** သင် Run လိုသော `.py` ဖိုင်ကို ဒီ Chat ထဲသို့ တိုက်ရိုက် ပို့ပေးလိုက်ပါ။"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

# .py ဖိုင် လက်ခံခြင်းနှင့် Run ခြင်း
@bot.message_handler(content_types=['document'])
def handle_docs(message):
    if not is_admin(message):
        return

    file_name = message.document.file_name
    if not file_name.endswith('.py'):
        return bot.reply_to(message, "❌ `.py` (Python) ဖိုင်များကိုသာ ပေးပို့နိုင်ပါသည်။", parse_mode="Markdown")

    active_count = sum(1 for p in running_processes.values() if p.poll() is None)
    if file_name not in running_processes and active_count >= MAX_BOTS:
        return bot.reply_to(message, f"⚠️ အများဆုံး Bot **{MAX_BOTS}** ခု ပြည့်သွားပါပြီ။ အသစ်ထည့်ရန် အဟောင်းတစ်ခုကို အရင်ပိတ်ပါ။", parse_mode="Markdown")

    msg = bot.reply_to(message, f"⏳ `{file_name}` ကို ဒေါင်းလုဒ်ဆွဲပြီး Run နေပါသည်...", parse_mode="Markdown")

    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_path = os.path.join(UPLOAD_DIR, file_name)

        if file_name in running_processes:
            if running_processes[file_name].poll() is None:
                running_processes[file_name].terminate()
                running_processes[file_name].wait()

        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        log_path = os.path.join(UPLOAD_DIR, f"{file_name}.log")
        log_file = open(log_path, "w")
        proc = subprocess.Popen([sys.executable, file_path], stdout=log_file, stderr=subprocess.STDOUT)
        running_processes[file_name] = proc

        bot.edit_message_text(
            f"✅ **{file_name}** ကို အောင်မြင်စွာ စတင် Run လိုက်ပါပြီ!\n"
            f"🆔 PID: `{proc.pid}`",
            chat_id=message.chat.id,
            message_id=msg.message_id,
            parse_mode="Markdown"
        )
    except Exception as e:
        bot.edit_message_text(f"❌ Error ဖြစ်သွားပါသည်:\n`{str(e)}`", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

# System & Bot CPU/RAM အခြေအနေ ကြည့်ရှုခြင်း
@bot.message_handler(func=lambda message: message.text == "📊 System & Bot Stats")
def show_stats(message):
    if not is_admin(message):
        return

    total_cpu = psutil.cpu_percent(interval=0.5)
    cpu_cores = psutil.cpu_count(logical=True)
    ram = psutil.virtual_memory()
    ram_used = ram.used / (1024 ** 2)
    ram_total = ram.total / (1024 ** 2)

    stats_text = (
        "🖥 **VPS / Server အခြေအနေ**\n"
        f"• **CPU Usage:** `{total_cpu}%` ({cpu_cores} Cores)\n"
        f"• **RAM Usage:** `{ram_used:.1f} MB / {ram_total:.1f} MB` ({ram.percent}%)\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🤖 **Run နေသော Bot များ၏ Resource:**\n\n"
    )

    active_bots = 0
    for name, proc in list(running_processes.items()):
        if proc.poll() is None:
            try:
                p = psutil.Process(proc.pid)
                bot_cpu = p.cpu_percent(interval=0.1)
                bot_ram = p.memory_info().rss / (1024 ** 2)
                stats_text += f"🟢 **{name}** (PID: `{proc.pid}`)\n   └ CPU: `{bot_cpu}%` | RAM: `{bot_ram:.2f} MB`\n\n"
                active_bots += 1
            except psutil.NoSuchProcess:
                stats_text += f"🔴 **{name}** (ရပ်တန့်သွားပါသည်)\n\n"
        else:
            stats_text += f"🔴 **{name}** (ရပ်တန့်သွားပါသည် - Error ရှိနိုင်ပါသည်)\n\n"

    if not running_processes:
        stats_text += "_လက်ရှိ ထည့်သွင်းထားသော Bot မရှိသေးပါ။_"
    else:
        stats_text += f"📌 **Slot အသုံးပြုမှု:** `{active_bots} / {MAX_BOTS}`"

    bot.send_message(message.chat.id, stats_text, parse_mode="Markdown")

# Bot များကို ပိတ်ရန် / ဖျက်ရန် / Log ကြည့်ရန်
@bot.message_handler(func=lambda message: message.text == "📂 Manage Running Bots")
def manage_bots(message):
    if not is_admin(message):
        return

    if not running_processes:
        return bot.send_message(message.chat.id, "📂 လက်ရှိ စီမံခန့်ခွဲစရာ Bot မရှိသေးပါ။")

    markup = types.InlineKeyboardMarkup()
    for name, proc in running_processes.items():
        status = "🟢" if proc.poll() is None else "🔴"
        btn_stop = types.InlineKeyboardButton(f"{status} {name} (Stop/Del)", callback_data=f"del_{name}")
        btn_log = types.InlineKeyboardButton("📄 Log", callback_data=f"log_{name}")
        markup.add(btn_stop, btn_log)

    bot.send_message(message.chat.id, "⚙️ ပိတ်သိမ်းလိုသော သို့မဟုတ် Log ကြည့်လိုသော Bot ကို ရွေးချယ်ပါ-", reply_markup=markup)

# Inline Button နှိပ်သည့်အခါ အလုပ်လုပ်ရန်
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.from_user.id != ADMIN_ID:
        return

    action, file_name = call.data.split("_", 1)

    if action == "del":
        if file_name in running_processes:
            proc = running_processes[file_name]
            if proc.poll() is None:
                proc.terminate()
                proc.wait()
            del running_processes[file_name]

            file_path = os.path.join(UPLOAD_DIR, file_name)
            log_path = os.path.join(UPLOAD_DIR, f"{file_name}.log")
            if os.path.exists(file_path): os.remove(file_path)
            if os.path.exists(log_path): os.remove(log_path)

            bot.answer_callback_query(call.id, f"{file_name} ကို ပိတ်ပြီး ဖျက်လိုက်ပါပြီ။")
            bot.edit_message_text(f"🗑 **{file_name}** ကို ရပ်တန့်ပြီး ဖျက်သိမ်းလိုက်ပါပြီ။", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

    elif action == "log":
        log_path = os.path.join(UPLOAD_DIR, f"{file_name}.log")
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                logs = f.read()[-3000:]
            if not logs.strip():
                logs = "Log မှတ်တမ်း မရှိသေးပါ။"
            bot.send_message(call.message.chat.id, f"📄 **{file_name} Logs:**\n```\n{logs}\n```", parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "Log ဖိုင် မတွေ့ပါ။")

print("Hosting Bot is running...")
bot.infinity_polling()
