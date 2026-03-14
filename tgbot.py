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

# Токен API Gismeteo (получить на gismeteo.ru/api/)
GISMETEO_TOKEN = 'ваш_реальный_токен_gismeteo'  # ЗАМЕНИТЕ НА РЕАЛЬНЫЙ ТОКЕН!

# ID города по умолчанию (например, Москва - 4368)
DEFAULT_CITY_ID = 4368

# Порт для веб-сервера (Render передает это через переменную окружения)
PORT = int(os.getenv('PORT', 10000))
# =============================================

# Инициализация бота и Flask
bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

# Функция для получения текущей погоды по ID города
def get_current_weather(city_id):
    """Получает текущую погоду через API Gismeteo"""
    url = f"https://api.gismeteo.net/v2/weather/current/{city_id}/"
    headers = {
        'X-Gismeteo-Token': GISMETEO_TOKEN,
        'Accept': 'application/json'
    }
    params = {
        'lang': 'ru'
    }
    
    try:
        print(f"Запрос погоды для city_id: {city_id}")
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Ошибка API: {e}")
        return None

# Функция для поиска города по названию
def search_city(city_name):
    """Ищет город по названию через API Gismeteo"""
    url = "https://api.gismeteo.net/v2/search/cities/"
    headers = {
        'X-Gismeteo-Token': GISMETEO_TOKEN,
        'Accept': 'application/json'
    }
    params = {
        'query': city_name,
        'lang': 'ru'
    }
    
    try:
        print(f"Поиск города: {city_name}")
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Ошибка API при поиске города: {e}")
        return None

# Функция форматирования погоды для вывода
def format_weather(weather_data, city_name):
    """Форматирует данные о погоде для красивого вывода"""
    try:
        response = weather_data['response']
        
        # Температура
        temp_c = response['temperature']['air']['C']
        
        # Ощущается как
        comfort_c = response['temperature']['comfort']['C']
        
        # Описание погоды
        description = response['description']['full']
        
        # Влажность
        humidity = response['humidity']['percent']
        
        # Давление
        pressure_mm = response['pressure']['mm_hg_atm']
        
        # Ветер
        wind_speed = response['wind']['speed']['m_s']
        wind_direction_deg = response['wind']['direction']['degree']
        
        # Направление ветра текстом
        directions = ['северный', 'северо-восточный', 'восточный', 'юго-восточный', 
                      'южный', 'юго-западный', 'западный', 'северо-западный']
        wind_dir_text = directions[round(wind_direction_deg / 45) % 8]
        
        # Дата обновления
        local_time = datetime.fromisoformat(response['date']['local'].replace(' ', 'T'))
        time_str = local_time.strftime('%d.%m.%Y %H:%M')
        
        result = (
            f"🌍 **Погода в {city_name}**\n"
            f"📅 {time_str}\n\n"
            f"🌡 **Температура:** {temp_c}°C\n"
            f"🤔 **Ощущается как:** {comfort_c}°C\n"
            f"☁️ **Описание:** {description}\n"
            f"💧 **Влажность:** {humidity}%\n"
            f"📊 **Давление:** {pressure_mm} мм рт.ст.\n"
            f"🌬 **Ветер:** {wind_speed} м/с, {wind_dir_text}\n"
        )
        return result
    except (KeyError, TypeError) as e:
        print(f"Ошибка форматирования данных: {e}")
        return "Не удалось обработать данные о погоде."

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, 
                 "Привет! Я бот погоды от Gismeteo.\n"
                 "Используй /weather <город> чтобы узнать погоду.\n"
                 "Например: /weather Москва")

# Обработчик команды /weather
@bot.message_handler(commands=['weather'])
def send_weather(message):
    # Проверка наличия токена Gismeteo
    if GISMETEO_TOKEN == 'ваш_реальный_токен_gismeteo':
        bot.reply_to(message, "❌ **Ошибка:** API Gismeteo не настроено. Пожалуйста, замените токен в коде.", parse_mode='Markdown')
        return
    
    # Получаем название города из сообщения
    try:
        city_name = message.text.split(' ', 1)[1]
    except IndexError:
        bot.reply_to(message, "Пожалуйста, укажите город. Например: /weather Москва")
        return
    
    # Отправляем сообщение о начале поиска
    msg = bot.reply_to(message, f"🔍 Ищу погоду для города {city_name}...")
    
    # Ищем город
    search_result = search_city(city_name)
    
    if not search_result or 'response' not in search_result or len(search_result['response']) == 0:
        bot.edit_message_text(f"❌ Город '{city_name}' не найден. Попробуйте другое название.", 
                            chat_id=message.chat.id, message_id=msg.message_id)
        return
    
    # Берем первый найденный город
    city = search_result['response'][0]
    city_id = city['id']
    found_city_name = city['name']
    
    bot.edit_message_text(f"✅ Город {found_city_name} найден. Получаю погоду...", 
                        chat_id=message.chat.id, message_id=msg.message_id)
    
    # Получаем погоду
    weather = get_current_weather(city_id)
    
    if weather and 'response' in weather:
        weather_text = format_weather(weather, found_city_name)
        bot.edit_message_text(weather_text, chat_id=message.chat.id, 
                            message_id=msg.message_id, parse_mode='Markdown')
    else:
        bot.edit_message_text("❌ Не удалось получить данные о погоде. Попробуйте позже.", 
                            chat_id=message.chat.id, message_id=msg.message_id)

# Обработчик текстовых сообщений
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "Используйте команду /weather <город>")

# Flask маршруты для проверки работоспособности
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
    print(f"  • Gismeteo токен: {'⚠️ не настроен' if GISMETEO_TOKEN == 'ваш_реальный_токен_gismeteo' else '✅'}")
    print(f"  • Порт для веб-сервера: {PORT}")
    print("="*50 + "\n")
    
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    print("✅ Бот запущен в фоновом потоке")
    
    # Запускаем Flask сервер для поддержки порта
    print(f"🚀 Запуск веб-сервера на порту {PORT}...")
    app.run(host='0.0.0.0', port=PORT)
