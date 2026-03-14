import telebot
import requests
import json
import os
import sys
import time
import threading
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, jsonify

# ================= НАСТРОЙКИ =================
# Токен вашего Telegram-бота (получить у @BotFather)
TELEGRAM_TOKEN = '8717465292:AAGaMse1y8ZlLmXjEeXoyw8WnuvuPwCF_fk'

# API ключ OpenWeatherMap 
OPENWEATHER_API_KEY = '1876ff689a7c2880fc5a535a4a8c2966' 

# Порт для веб-сервера (Render передает это через переменную окружения)
PORT = int(os.getenv('PORT', 10000))
# =============================================

# Инициализация бота и Flask
bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

# Словарь для перевода русских названий городов на английские
CITY_TRANSLATION = {
    'москва': 'Moscow',
    'мск': 'Moscow',
    'санкт-петербург': 'Saint Petersburg',
    'спб': 'Saint Petersburg',
    'питер': 'Saint Petersburg',
    'петербург': 'Saint Petersburg',
    'казань': 'Kazan',
    'новосибирск': 'Novosibirsk',
    'екатеринбург': 'Yekaterinburg',
    'нижний новгород': 'Nizhny Novgorod',
    'самара': 'Samara',
    'омск': 'Omsk',
    'ростов-на-дону': 'Rostov-on-Don',
    'ростов': 'Rostov-on-Don',
    'уфа': 'Ufa',
    'красноярск': 'Krasnoyarsk',
    'пермь': 'Perm',
    'воронеж': 'Voronezh',
    'волгоград': 'Volgograd',
    'краснодар': 'Krasnodar',
    'саратов': 'Saratov',
    'тюмень': 'Tyumen',
    'сочи': 'Sochi',
    'БКК': 'Bangkok'
}

# Функция для получения текущей погоды через OpenMap
def get_current_weather(city_name):
    """Получает текущую погоду через OpenWeatherMap API"""
    
    # Проверяем, есть ли город в словаре перевода
    city_lower = city_name.lower().strip()
    if city_lower in CITY_TRANSLATION:
        city_name = CITY_TRANSLATION[city_lower]
        print(f"Перевели город на английский: {city_name}")
    
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        'q': city_name,
        'appid': OPENWEATHER_API_KEY,
        'units': 'metric',  # Для температуры в Цельсиях
        'lang': 'ru'  # Для описания на русском
    }
    
    try:
        print(f"Запрос погоды для города: {city_name}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Ошибка API: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Статус код: {e.response.status_code}")
            print(f"Ответ: {e.response.text}")
        return None

# Функция для получения погоды по координатам (запасной вариант)
def get_weather_by_coords(lat, lon):
    """Получает погоду по координатам"""
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        'lat': lat,
        'lon': lon,
        'appid': OPENWEATHER_API_KEY,
        'units': 'metric',
        'lang': 'ru'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except:
        return None

# Функция для поиска города (если прямое название не работает)
def search_city_alternative(city_name):
    """Пытается найти город через поиск"""
    url = "http://api.openweathermap.org/geo/1.0/direct"
    params = {
        'q': city_name,
        'limit': 1,
        'appid': OPENWEATHER_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data and len(data) > 0:
            return data[0]
        return None
    except:
        return None

# Функция форматирования погоды для вывода
def format_weather(weather_data, city_name):
    """Форматирует данные о погоде для красивого вывода"""
    try:
        # Основные данные
        temp = weather_data['main']['temp']
        feels_like = weather_data['main']['feels_like']
        humidity = weather_data['main']['humidity']
        pressure = weather_data['main']['pressure']  # в гПа
        
        # Описание погоды
        description = weather_data['weather'][0]['description'].capitalize()
        
        # Ветер
        wind_speed = weather_data['wind']['speed']
        wind_deg = weather_data['wind'].get('deg', 0)
        
        # Направление ветра текстом
        directions = ['северный', 'северо-восточный', 'восточный', 'юго-восточный', 
                      'южный', 'юго-западный', 'западный', 'северо-западный']
        wind_dir_index = round(wind_deg / 45) % 8
        wind_dir_text = directions[wind_dir_index]
        
        # Давление в мм рт.ст. (1 гПа ≈ 0.75 мм рт.ст.)
        pressure_mm = int(pressure * 0.75)
        
        # Название города из ответа API (может отличаться от введенного)
        city_display = weather_data.get('name', city_name)
        country = weather_data.get('sys', {}).get('country', '')
        location = f"{city_display}, {country}" if country else city_display
        
        result = (
            f"🌍 **Погода в {location}**\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"🌡 **Температура:** {temp:.1f}°C\n"
            f"🤔 **Ощущается как:** {feels_like:.1f}°C\n"
            f"☁️ **Описание:** {description}\n"
            f"💧 **Влажность:** {humidity}%\n"
            f"📊 **Давление:** {pressure_mm} мм рт.ст.\n"
            f"🌬 **Ветер:** {wind_speed:.1f} м/с, {wind_dir_text}\n"
        )
        return result
    except (KeyError, TypeError) as e:
        print(f"Ошибка форматирования данных: {e}")
        return "Не удалось обработать данные о погоде."

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "👋 **Привет! Я бот Синоптик!**\n\n"
        "🌤 **Команды:**\n"
        "• `/weather <город> или просто <Город>` - узнать погоду\n"
        "• `/help` - справка\n\n"
        "📝 **Примеры:**\n"
        "`/weather Москва`\n"
        "`London`\n"
        "`Уфа`\n\n"
        "Я понимаю русские и английские названия городов!"
    )
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

# Обработчик команды /help
@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = (
        "📖 **Справка**\n\n"
        "Я показываю текущую погоду в любом городе мира.\n\n"
        "🔍 **Как использовать:**\n"
        "Напиши `/weather Москва` или просто название города\n\n"
        "🌍 **Подсказки:**\n"
        "• Можно писать на русском или английском\n"
        "• Для больших городов сработает сразу\n"
        "• Для маленьких - уточните страну (London,GB)\n\n"
        "❓ Если город не найден, попробуйте английское название"
    )
    bot.reply_to(message, help_text, parse_mode='Markdown')

# Обработчик команды /weather
@bot.message_handler(commands=['weather'])
def send_weather(message):
    # Получаем название города из сообщения
    try:
        city_name = message.text.split(' ', 1)[1].strip()
        if not city_name:
            raise IndexError
    except IndexError:
        bot.reply_to(message, 
                    "❌ **Пожалуйста, укажите город.**\n\n"
                    "Пример: `/weather Москва`\n"
                    "Или просто отправьте название города", 
                    parse_mode='Markdown')
        return
    
    # Отправляем сообщение о начале поиска
    msg = bot.reply_to(message, f"🔍 Ищу погоду для города *{city_name}*...", parse_mode='Markdown')
    
    # Сохраняем оригинальное название для сообщения об ошибке
    original_city = city_name
    
    # Пытаемся получить погоду напрямую
    weather = get_current_weather(city_name)
    
    # Если не получилось, пробуем через поиск
    if not weather or 'main' not in weather:
        print(f"Прямой запрос не удался, пробуем поиск для: {city_name}")
        city_info = search_city_alternative(city_name)
        
        if city_info:
            # Получаем погоду по координатам
            weather = get_weather_by_coords(city_info['lat'], city_info['lon'])
            if weather and 'main' in weather:
                # Сохраняем найденное название
                weather['name'] = city_info.get('local_names', {}).get('ru', city_info['name'])
    
    if weather and 'main' in weather:
        weather_text = format_weather(weather, original_city)
        bot.edit_message_text(weather_text, chat_id=message.chat.id, 
                            message_id=msg.message_id, parse_mode='Markdown')
    else:
        error_msg = (
            f"❌ **Город '{original_city}' не найден.**\n\n"
            "💡 **Попробуйте:**\n"
            "• Проверить название\n"
            "• Использовать английское название\n"
            "• Указать город и страну (Moscow,RU)\n"
            "• Написать на латинице\n\n"
            "📝 **Примеры:**\n"
            "`Moscow`\n"
            "`London,GB`\n"
            "`New York`"
        )
        bot.edit_message_text(error_msg, chat_id=message.chat.id, 
                            message_id=msg.message_id, parse_mode='Markdown')

# Обработчик текстовых сообщений (если просто отправить название города)
@bot.message_handler(func=lambda message: message.text and not message.text.startswith('/'))
def handle_city_name(message):
    city_name = message.text.strip()
    
    # Отправляем сообщение о начале поиска
    msg = bot.reply_to(message, f"🔍 Ищу погоду для города *{city_name}*...", parse_mode='Markdown')
    
    # Сохраняем оригинальное название
    original_city = city_name
    
    # Пытаемся получить погоду
    weather = get_current_weather(city_name)
    
    if not weather or 'main' not in weather:
        city_info = search_city_alternative(city_name)
        if city_info:
            weather = get_weather_by_coords(city_info['lat'], city_info['lon'])
            if weather and 'main' in weather:
                weather['name'] = city_info.get('local_names', {}).get('ru', city_info['name'])
    
    if weather and 'main' in weather:
        weather_text = format_weather(weather, original_city)
        bot.edit_message_text(weather_text, chat_id=message.chat.id, 
                            message_id=msg.message_id, parse_mode='Markdown')
    else:
        bot.edit_message_text(f"❌ Город '{original_city}' не найден. Попробуйте /help", 
                            chat_id=message.chat.id, message_id=msg.message_id)

# Flask маршруты для Render
@app.route('/')
def index():
    return jsonify({
        'status': 'ok',
        'message': 'Weather bot is running!',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'telegram_bot': 'running',
        'timestamp': datetime.now().isoformat()
    })

def run_bot():
    """Запускает бота в отдельном потоке"""
    print("🔄 Запуск бота в отдельном потоке...")
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ Ошибка в работе бота: {e}")
        time.sleep(5)
        run_bot()

# Запуск приложения
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🤖 TELEGRAM БОТ С ПОГОДОЙ")
    print("="*50)
    print(f"📊 Статус:")
    print(f"  • Telegram токен: {'✅' if TELEGRAM_TOKEN else '❌'}")
    print(f"  • OpenWeatherMap ключ: {'✅' if OPENWEATHER_API_KEY else '❌'}")
    print(f"  • Порт для веб-сервера: {PORT}")
    print("="*50 + "\n")
    
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    print("✅ Бот запущен в фоновом потоке")
    
    # Запускаем Flask сервер для поддержки порта
    print(f"🚀 Запуск веб-сервера на порту {PORT}...")
    app.run(host='0.0.0.0', port=PORT)
