import os
import json
import time
import requests
from datetime import datetime
import telebot
import threading
import re
import logging

json_directory = "./json"

def create_json_dir():
    if not os.path.exists('json'):
        os.makedirs('json')
        
create_json_dir()

API_TOKEN = 'TELEGRAM_API_TOKEN'
bot = telebot.TeleBot(API_TOKEN)

ALL_COIN_FILE = 'all_coin.json'

base_url = "https://api.coingecko.com/api/v3/coins/markets"
params = {
    'vs_currency': 'usd',
    'order': 'market_cap_desc',
    'per_page': 250,
    'sparkline': 'false',
    'price_change_percentage': '1h,24h,7d,30d,1y'
}

def update_all_coin_file():
    all_coins = []

    for page in range(1, 9):
        params['page'] = page
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            data = response.json()
            all_coins.extend(data)
        else:
            print(f"Failed to fetch data for page {page}. Status code: {response.status_code}")

    if all_coins:
        with open(ALL_COIN_FILE, 'w') as f:
            json.dump(all_coins, f, indent=4)
        print("JSON data received and saved to file")
    else:
        print("No data received to save to file")

    time.sleep(60)  

update_thread = threading.Thread(target=update_all_coin_file)
update_thread.start()

COIN_FILE_PATH = 'all_coin.json'
def send_start_menu(message):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("لیست رمز ارز ها", callback_data='list_coins'))
    markup.add(telebot.types.InlineKeyboardButton("بالاترین ها", callback_data='max_changes'),
               telebot.types.InlineKeyboardButton("پایینترین ها", callback_data='min_changes'))
    markup.add(telebot.types.InlineKeyboardButton("اختصاصی", callback_data='vip'))
    markup.add(telebot.types.InlineKeyboardButton("بهترین نسبت ولوم", callback_data='best_volume_ratio'),
               telebot.types.InlineKeyboardButton("بالاترین ولوم روزانه", callback_data='top_daily_volume'))
    markup.add(telebot.types.InlineKeyboardButton("یادآور", callback_data='alert'))
    markup.add(telebot.types.InlineKeyboardButton("محاسبه حمایت مقاومت", callback_data='support_resistance'))
    bot.send_message(message.chat.id, "خوش آمدید! لطفا یکی از گزینه‌ها را انتخاب کنید:", reply_markup=markup)
@bot.message_handler(commands=['start'])
def handle_start(message):
    send_start_menu(message)
    
@bot.callback_query_handler(func=lambda call: call.data == 'back')
def handle_back_to_start(call):
    send_start_menu(call.message)


user_alerts = {}

def load_coins():
    """بارگذاری اطلاعات کوین‌ها از فایل JSON."""
    if os.path.exists(ALL_COIN_FILE):
        with open(ALL_COIN_FILE, 'r') as f:
            return json.load(f)
    return []

def get_current_price(symbol):
    """دریافت قیمت لحظه‌ای کوین از API بایننس."""
    try:
        url = f"https://api.binance.com/api/v3/ticker/price"
        params = {'symbol': f"{symbol.upper()}USDT"}
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            return float(data['price'])
        else:
            logging.error(f"Error fetching current price: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Exception fetching current price: {e}")
        return None

def check_alerts():
    try:
        while True:
            for filename in os.listdir(json_directory):
                if filename.endswith('_alert.json'):
                    chat_id = filename.split('_')[0]
                    file_path = os.path.join(json_directory, filename)

                    with open(file_path, 'r') as file:
                        alerts = json.load(file)

                    for symbol, alerts_data in alerts.items():
                        for alert_id, alert_data in alerts_data.items():
                            if alert_data['status'] == 'active':
                                current_price = get_current_price(alert_data['symbol'])
                                if current_price is not None:
                                    if alert_data['alert_type'] == 'take_profit' and current_price >= alert_data['target_price']:
                                        send_alert_message(chat_id, alert_data['symbol'], alert_id, current_price, alert_data['alert_type'], alert_data['target_price'], get_coin_image_url(alert_data['symbol']))
                                        alert_data['status'] = 'inactive'
                                        save_alert_data(file_path, alerts)
                                    elif alert_data['alert_type'] == 'stop_loss' and current_price <= alert_data['target_price']:
                                        send_alert_message(chat_id, alert_data['symbol'], alert_id, current_price, alert_data['alert_type'], alert_data['target_price'], get_coin_image_url(alert_data['symbol']))
                                        alert_data['status'] = 'inactive'
                                        save_alert_data(file_path, alerts)
                                else:
                                    logging.warning(f"Failed to fetch current price for {alert_data['symbol']}")
            time.sleep(60)
    except Exception as e:
        logging.error(f"Error in check_alerts: {e}")

def get_coin_image_url(symbol):
    if os.path.exists(ALL_COIN_FILE):
        with open(ALL_COIN_FILE, 'r') as file:
            coins = json.load(file)
            coin = next((coin for coin in coins if coin['symbol'].lower() == symbol.lower()), None)
            return coin['image'] if coin else None
    return None

def send_alert_message(chat_id, symbol, alert_key, current_price, alert_type, target_price, image_url):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton('فعال سازی دوباره', callback_data=f'activate_{symbol}_{alert_key}'))
    markup.add(telebot.types.InlineKeyboardButton('حذف', callback_data=f'delete_{symbol}_{alert_key}'))
    markup.add(telebot.types.InlineKeyboardButton('بازگشت', callback_data='back'))

    try:
        symbol_upper = symbol.upper()
        if alert_type == 'take_profit':
            alert_message = (
                f"هشدار : برداشت سود 🟢\n"
                f"کاربر عزیز، رمز ارز {symbol_upper} به قیمت {current_price} دلار رسیده است.\n"
                f"شماره هشدار: {alert_key}\n"
                f"امیدواریم با این یادآوری لحظات پر سودی را برای شما رقم زده باشیم."
            )
        elif alert_type == 'remining':
            alert_message = (
                f"هشدار : یادآوری 🟡\n"
                f"کاربر عزیز، رمز ارز {symbol_upper} به قیمت {current_price} دلار رسیده است.\n"
                f"شماره هشدار: {alert_key}\n"
                f"امیدواریم با این یادآوری لحظات پر سودی را برای شما رقم زده باشیم."
            )
        elif alert_type == 'stop_loss':
            alert_message = (
                f"هشدار : حد ضرر 🔴\n"
                f"کاربر عزیز، رمز ارز {symbol_upper} به قیمت {current_price} دلار رسیده است.\n"
                f"شماره هشدار: {alert_key}\n"
                f"امیدواریم با این یادآوری لحظات پر سودی را برای شما رقم زده باشیم."
            )

        # ارسال پیام به کاربر
        if image_url:
            bot.send_photo(chat_id, image_url, caption=alert_message, reply_markup=markup)
        else:
            bot.send_message(chat_id, alert_message, reply_markup=markup)
    except Exception as e:
        logging.error(f"Error sending alert message: {e}")

def save_alert_data(file, alert_data):
    try:
        with open(file, 'w') as f:
            json.dump(alert_data, f, indent=4)
    except Exception as e:
        logging.error(f"Error saving alert data to file {file}: {e}")

# اجرای تابع check_alerts در ترد جداگانه
alert_thread = threading.Thread(target=check_alerts)
alert_thread.start()
    
###############################################################################################

@bot.callback_query_handler(func=lambda call: call.data.startswith('activate_'))
def handle_activate_alert(call):
    # استخراج اطلاعات از کلید
    data = call.data.split('_')
    symbol = data[1]
    alert_key = data[2]
    
    chat_id = call.message.chat.id
    file_name = os.path.join(json_directory, f'{chat_id}_alert.json')
    
    try:
        with open(file_name, 'r') as file:
            alert_data = json.load(file)
        
        if symbol in alert_data:
            sub_data = alert_data[symbol]
            if alert_key in sub_data and sub_data[alert_key]['status'] == 'inactive':
                sub_data[alert_key]['status'] = 'active'
                    
            with open(file_name, 'w') as file:
                json.dump(alert_data, file, indent=4)
            
            bot.send_message(chat_id, f'کاربر عزیز هشدار برای این رمز ارز دوباره فعال شد.', 
                             reply_markup=telebot.types.ReplyKeyboardRemove())
            send_start_menu(call.message)
        else:
            bot.send_message(chat_id, 'یادآوری مورد نظر یافت نشد.')
    except FileNotFoundError:
        bot.send_message(chat_id, 'خطا در دریافت اطلاعات از فایل جیسون')
    except json.JSONDecodeError:
        bot.send_message(chat_id, 'خطا در پردازش فایل JSON')

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def handle_delete_alert(call):
    chat_id = call.message.chat.id
    try:
        # چاپ داده‌های دریافتی برای اشکال‌زدایی
        logging.info(f"Received data: {call.data}")
        
        # استخراج اطلاعات از کلید
        data = call.data.split('_')
        logging.info(f"Split data: {data}")
        
        if len(data) != 3:
            raise ValueError("Invalid callback data format")
        
        symbol = data[1]
        alert_key = data[2]
        
        # ارسال پیام تأیید
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton('تایید', callback_data=f'confirm_delete_{symbol}_{alert_key}'))
        markup.add(telebot.types.InlineKeyboardButton('بازگشت', callback_data='back'))

        bot.send_message(chat_id, 'کاربر عزیز با حذف این یادآور تمامی اطلاعات مربوط به این یادآور حذف خواهد شد. در صورت اطمینان بر روی دکمه تایید کلیک کنید.', reply_markup=markup)
    except Exception as e:
        logging.error(f"Error in handle_delete_alert: {e}")
        bot.send_message(chat_id, 'خطا در پردازش درخواست حذف.')

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_delete_'))
def handle_confirm_delete(call):
    chat_id = call.message.chat.id
    try:
        # استخراج اطلاعات از کلید
        data = call.data.split('_')
        logging.info(f"Confirm delete data: {data}")
        
        if len(data) != 4:
            raise ValueError("Invalid callback data format")

        symbol = data[2]
        alert_key = data[3]

        file_name = os.path.join(json_directory, f'{chat_id}_alert.json')

        # حذف یادآور
        with open(file_name, 'r') as file:
            alert_data = json.load(file)

        if symbol in alert_data:
            sub_data = alert_data[symbol]
            if alert_key in sub_data:
                del sub_data[alert_key]
                
                if not sub_data:
                    del alert_data[symbol]
                
                with open(file_name, 'w') as file:
                    json.dump(alert_data, file, indent=4)

                bot.send_message(chat_id, 'کاربر عزیز اطلاعات یادآوری این ارز حذف گردید.', 
                                 reply_markup=telebot.types.ReplyKeyboardRemove())
            else:
                bot.send_message(chat_id, 'یادآوری مورد نظر یافت نشد.')
        else:
            bot.send_message(chat_id, 'نماد مورد نظر یافت نشد.')

        send_start_menu(call.message)
    except Exception as e:
        logging.error(f"Error in handle_confirm_delete: {e}")
        bot.send_message(chat_id, 'خطا در حذف یادآور.')



###############################################################################################


user_alerts = {}

@bot.callback_query_handler(func=lambda call: call.data == 'alert')
def handle_alert_query(call):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton('ثبت هشدار', callback_data='set_alert'))
    markup.add(telebot.types.InlineKeyboardButton('مشاهده هشدار ها', callback_data='view_alerts'))
    markup.add(telebot.types.InlineKeyboardButton('تنظیمات', callback_data='settings'))
    
    bot.send_message(call.message.chat.id, 'ثبت هشدار جدید', reply_markup=markup)
    
#########################################################################################
def load_coins():
    """بارگذاری اطلاعات کوین‌ها از فایل JSON."""
    if os.path.exists(ALL_COIN_FILE):
        with open(ALL_COIN_FILE, 'r') as f:
            return json.load(f)
    return []


@bot.callback_query_handler(func=lambda call: call.data == 'set_alert')
def set_alert(call):
    bot.send_message(call.message.chat.id, 'لطفاً نماد ارز دیجیتالی که می‌خواهید هشدار برای آن تنظیم کنید را وارد کنید.')
    bot.register_next_step_handler(call.message, get_symbol)

def get_symbol(message):
    symbol = message.text.lower()
    coins = load_coins()
    coin = next((coin for coin in coins if coin['symbol'] == symbol), None)
    
    if coin:
        current_price = get_current_price(symbol)
        if current_price is None:
            bot.send_message(message.chat.id, 'خطا در دریافت قیمت لحظه‌ای. لطفاً دوباره امتحان کنید.')
            return
        image_url = coin['image']
        user_alerts[message.chat.id] = {'symbol': symbol, 'initial_price': current_price, 'image_url': image_url}
        bot.send_photo(message.chat.id, image_url, caption=f'قیمت فعلی {symbol} برابر {current_price} دلار است.\n'
                                                           'لطفاً قیمت هدف خود را وارد کنید.')
        bot.register_next_step_handler(message, get_alert_value)
    else:
        bot.send_message(message.chat.id, 'نماد ارز دیجیتال مورد نظر یافت نشد. لطفاً مجدداً امتحان کنید.')
        bot.register_next_step_handler(message, get_symbol)

def get_alert_value(message):
    user_data = user_alerts[message.chat.id]
    initial_price = user_data['initial_price']
    symbol = user_data['symbol']
    alert_value = message.text.strip()

    if '%' in alert_value:
        percentage = float(alert_value.replace('%', ''))
        target_price = initial_price * (1 + percentage / 100)
    else:
        target_price = float(alert_value)

    percentage_change = ((target_price - initial_price) / initial_price) * 100
    user_alerts[message.chat.id]['target_price'] = target_price
    user_alerts[message.chat.id]['percentage_change'] = percentage_change

    # ارسال پیام با دکمه‌های شیشه‌ای برای انتخاب وضعیت هشدار
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("برداشت سود 🟢", callback_data="take_profit"),
        telebot.types.InlineKeyboardButton("یادآوری 🟡", callback_data="remining"),
        telebot.types.InlineKeyboardButton("حد ضرر 🔴", callback_data="stop_loss")
    )

    bot.send_message(message.chat.id, f'کاربر عزیز، مبلغ {target_price} دلار برای این ارز به عنوان هدف شما ثبت شد.\n'
                                      f'این ارز تا رسیدن به نقطه هدف شما {percentage_change:.2f}% تغییر خواهد کرد.\n'
                                      'لطفاً نوع هشدار خود را انتخاب کنید:', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ['take_profit', 'remining', 'stop_loss'])
def handle_alert_type(call):
    chat_id = call.message.chat.id
    alert_type = call.data

    if chat_id in user_alerts:
        user_alerts[chat_id]['alert_type'] = alert_type
        save_alert_to_file(chat_id)
        bot.send_message(chat_id, 'وضعیت هشدار شما با موفقیت ثبت شد.')

    # بازگشت به منوی اصلی یا گزینه‌های دیگر
    send_start_menu(call.message)

def save_alert_to_file(chat_id):
    user_data = user_alerts[chat_id]
    alert_data = {
        'symbol': user_data['symbol'],
        'initial_price': user_data['initial_price'],
        'target_price': user_data['target_price'],
        'percentage_change': user_data['percentage_change'],
        'alert_type': user_data.get('alert_type'),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'active',
        'alert_sent': False
    }

    symbol = user_data['symbol'].lower()
    user_alerts_file = f'json/{chat_id}_alert.json'
    
    if os.path.exists(user_alerts_file):
        with open(user_alerts_file, 'r') as f:
            all_alerts = json.load(f)
    else:
        all_alerts = {}

    if symbol not in all_alerts:
        all_alerts[symbol] = {}
    
    alert_number = len(all_alerts[symbol]) + 1
    alert_key = f'alert{alert_number:02d}'
    all_alerts[symbol][alert_key] = alert_data

    with open(user_alerts_file, 'w') as f:
        json.dump(all_alerts, f, indent=4)

# def send_start_menu(message):
#     # بازگشت به منوی اصلی یا ارائه گزینه‌های دیگر به کاربر
#     markup = telebot.types.ReplyKeyboardMarkup(row_width=2)
#     markup.add('ثبت هشدار', 'مشاهده هشدارها')
#     bot.send_message(message.chat.id, 'لطفاً یک گزینه را انتخاب کنید:', reply_markup=markup)



@bot.callback_query_handler(func=lambda call: call.data == 'view_alerts')
def view_alerts(call):
    chat_id = call.message.chat.id  # استخراج chat_id از callback_query
    file_name = f'json/{chat_id}_alert.json'
    
    try:
        with open(file_name, 'r') as file:
            alert_data = json.load(file)
            markup = telebot.types.InlineKeyboardMarkup()

            # ساختن دکمه‌ها بر اساس کلیدهای سطح اول JSON
            for user_key in alert_data.keys():
                button = telebot.types.InlineKeyboardButton(user_key, callback_data='view_' + user_key)
                markup.add(button)
            
            bot.send_message(chat_id, 'هشدارهای شما:', reply_markup=markup)
    except FileNotFoundError:
        bot.send_message(chat_id, 'خطا در دریافت اطلاعات از فایل جیسون')


@bot.callback_query_handler(func=lambda call: call.data.startswith('view_'))
def handle_view_alert(call):
    main_key = call.data.replace('view_', '')
    chat_id = call.message.chat.id
    file_name = f'json/{chat_id}_alert.json'
    all_coins_file = ALL_COIN_FILE

    try:
        with open(file_name, 'r') as file:
            alert_data = json.load(file)
        
        with open(all_coins_file, 'r') as coin_file:
            all_coins_data = json.load(coin_file)
        
        # استفاده از main_key به عنوان symbol
        symbol = main_key.lower()
        
        coin = next((coin for coin in all_coins_data if coin['symbol'].lower() == symbol), None)
        if not coin:
            bot.send_message(chat_id, 'لوگوی ارز دیجیتال یافت نشد.')
            return
        
        coin_image_url = coin['image']
        
        if symbol in alert_data:
            sub_data = alert_data[symbol]
            for alert_key, alert_info in sub_data.items():
                # تعیین وضعیت هشدار بر اساس alert_type
                alert_type = alert_info.get('alert_type', 'نامشخص')
                if alert_type == 'take_profit':
                    alert_type_text = 'برداشت سود 🟢'
                elif alert_type == 'remining':
                    alert_type_text = 'یادآوری 🟡'
                elif alert_type == 'stop_loss':
                    alert_type_text = 'حد ضرر 🔴'
                else:
                    alert_type_text = 'نامشخص'
                
                # دریافت قیمت لحظه‌ای از API بایننس
                current_price = get_current_price(symbol)
                if current_price is None:
                    bot.send_message(chat_id, 'خطا در دریافت قیمت لحظه‌ای. لطفاً دوباره امتحان کنید.')
                    continue
                
                markup = telebot.types.InlineKeyboardMarkup()
                markup.add(telebot.types.InlineKeyboardButton('ویرایش', callback_data=f'edit_{symbol}_{alert_key}'))
                markup.add(telebot.types.InlineKeyboardButton('حذف', callback_data=f'delete_{symbol}_{alert_key}'))
                markup.add(telebot.types.InlineKeyboardButton('بازگشت', callback_data='back'))

                alert_number = re.search(r'\d+', alert_key).group()

                bot.send_photo(chat_id, coin_image_url, caption=f'یادآور شماره: {alert_number}\n'
                                                                f'مبلغ فعلی: {current_price} دلار\n'
                                                                f'مبلغ هشدار: {alert_info["target_price"]} دلار\n'
                                                                f'درصد تغییر تا هشدار: {alert_info["percentage_change"]:.2f}%\n'
                                                                f'وضعیت: {alert_info["status"]}\n'
                                                                f'نوع هشدار: {alert_type_text}\n',
                                                                reply_markup=markup)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        bot.send_message(chat_id, 'خطا در خواندن فایل JSON یا یافتن اطلاعات.')

@bot.callback_query_handler(func=lambda call: call.data == 'back')
def go_back(call):
    view_alerts(call)

       
    
    
bot.polling()
    
