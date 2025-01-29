from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
import random
import datetime
import asyncio
import logging
import os
import sqlite3
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Replace with your actual Telegram bot token
API_TOKEN = '7854106709:AAHeIIyM3aUH8cxzIX68MgOxzA-XgKQ4-r0'

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()
scheduler = AsyncIOScheduler()

# Database setup
db_path = "bot_users.db"

def init_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        daily_count INTEGER DEFAULT 0,
                        last_reset TEXT
                      )''')
    conn.commit()
    conn.close()

init_db()

def add_username_column():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Проверяем, существует ли столбец username
    cursor.execute("PRAGMA table_info(users)")
    columns = [info[1] for info in cursor.fetchall()]
    if "username" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
        conn.commit()
    conn.close()

def add_first_name_column():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    columns = [info[1] for info in cursor.fetchall()]
    if "first_name" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN first_name TEXT")
        conn.commit()
    conn.close()

add_first_name_column()

# Вызовите эту функцию один раз при запуске
add_username_column()

def get_user_data(user_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT daily_count, last_reset FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def set_user_data(user_id, daily_count, last_reset, username=None, first_name=None):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users (user_id, daily_count, last_reset, username, first_name)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
        daily_count = excluded.daily_count,
        last_reset = excluded.last_reset,
        username = COALESCE(excluded.username, username),
        first_name = COALESCE(excluded.first_name, first_name)
        """,
        (user_id, daily_count, last_reset, username, first_name)
    )
    conn.commit()
    conn.close()

def reset_user_attempts():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

def load_card_descriptions(filename="card_descriptions.txt"):
    descriptions = {}
    if not os.path.exists(filename):
        logging.warning(f"Файл {filename} не найден.")
        return descriptions  # Возвращаем пустой словарь

    with open(filename, "r", encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split(":", 1)  # Разделяем по первому двоеточию
            if len(parts) == 2:
                card_name, description = parts
                descriptions[card_name.strip()] = description.strip()
    return descriptions

# Загрузка описаний карт при запуске
card_descriptions = load_card_descriptions()
  
    # Сбрасываем только для пользователей с попытками <= MAX_ATTEMPTS и прошло 24 часа
    cursor.execute("""
        UPDATE users 
        SET daily_count = 0, last_reset = ?
        WHERE (daily_count <= ? OR daily_count IS NULL) AND (julianday(?) - julianday(last_reset)) >= 1
    """, (datetime.datetime.now().isoformat(), MAX_ATTEMPTS, datetime.datetime.now().isoformat()))

    conn.commit()
    conn.close()

# Maximum daily attempts
MAX_ATTEMPTS = 5

# Define keyboards
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Получить карту")],
        [KeyboardButton(text="\u2728 О картах"), KeyboardButton(text="\u2753 Задать вопрос тарологу")],
        [KeyboardButton(text="\u2605 Мой тариф")]
    ],
    resize_keyboard=True
)

# Define path for card images
CARD_IMAGES_PATH = "./card_images"

# Ensure the directory exists
if not os.path.exists(CARD_IMAGES_PATH):
    os.makedirs(CARD_IMAGES_PATH)

# Function to get random card images
def get_random_card_images(count=1):
    images = [f for f in os.listdir(CARD_IMAGES_PATH) if os.path.isfile(os.path.join(CARD_IMAGES_PATH, f))]
    if not images:
        raise FileNotFoundError("No card images found in the directory.")
    return random.sample(images, count)

# Function to send the daily card
async def send_daily_card():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, first_name FROM users")
    users = cursor.fetchall()
    conn.close()

    for user_id, username, first_name in users:
        try:
            display_name = first_name or username or "друг"  # Используйте first_name в первую очередь
            card_image = get_random_card_images(1)[0]
            image_path = os.path.join(CARD_IMAGES_PATH, card_image)
            await bot.send_photo(
                user_id,
                photo=FSInputFile(image_path),
                caption=f"Доброе утро, {display_name}! Это твоя карта дня:"
            )
        except FileNotFoundError:
            logging.error("No card images found. Cannot send daily card.")
        except Exception as e:
            logging.error(f"Ошибка отправки карты пользователю {user_id}: {e}")

# Command handlers
@router.message(Command(commands=['start']))
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "не указан"
    first_name = message.from_user.first_name or "друг"
    user_data = get_user_data(user_id)

    if user_data:
        set_user_data(user_id, user_data[0], user_data[1], username, first_name)
    else:
        set_user_data(user_id, 0, datetime.datetime.now().isoformat(), username, first_name)

    welcome_text = (
        f"{first_name}, привет! Добро пожаловать в уникальный бот с МАК картами от Алены Венгер ✨\n"
        "Здесь ты откроешь для себя огромный мир самопознания, где найдешь ответы на все свои вопросы 🥰\n\n"
        "МАК карты - метафорические карты, с помощью которых ты можешь заглянуть в свое подсознание без психологов и других специалистов.\n"
        "Можешь достать любую информацию, принять важное решение или провести самокоучинг."
    )
    await message.answer(welcome_text, reply_markup=main_menu)

@router.message(Command(commands=['last_user']))
async def get_last_user(message: types.Message):
    # Проверяем, что сообщение от администратора
    admin_id = 327308286  # Ваш Telegram ID
    if message.from_user.id != admin_id:
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users ORDER BY rowid DESC LIMIT 1")
    result = cursor.fetchone()
    conn.close()

    if result:
        await message.answer(f"Последний зарегистрированный пользователь: {result[0]}")
    else:
        await message.answer("Нет зарегистрированных пользователей.")

@router.message(Command(commands=['set_attempts']))
async def set_attempts(message: types.Message):
    admin_id = 327308286  # Ваш Telegram ID
    if message.from_user.id != admin_id:
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    try:
        _, user_id, attempts = message.text.split()
        user_id = int(user_id)
        attempts = int(attempts)

        user_data = get_user_data(user_id)
        if user_data:
            # Обновляем daily_count
            last_reset = user_data[1]
            set_user_data(user_id, MAX_ATTEMPTS - attempts, last_reset)
            await message.answer(f"Установлено {attempts} попыток для пользователя {user_id}. Осталось: {attempts}.")
        else:
            await message.answer(f"Пользователь с ID {user_id} не найден.")
    except ValueError:
        await message.answer("Используйте команду в формате: /set_attempts user_id attempts")

@router.message(Command(commands=['update_usernames']))
async def update_usernames(message: types.Message):
    admin_id = 327308286  # Ваш Telegram ID
    if message.from_user.id != admin_id:
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    updated_count = 0
    for user_id, in users:
        user = await bot.get_chat(user_id)
        username = user.username or "не указан"
        cursor.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
        updated_count += 1

    conn.commit()
    conn.close()

    await message.answer(f"Обновлено никнеймов для {updated_count} пользователей.")

@router.message(Command(commands=['user_count']))
async def user_count(message: types.Message):
    admin_id = 327308286  # Ваш Telegram ID
    if message.from_user.id != admin_id:
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()

    await message.answer(f"Количество пользователей бота: {count}")

@router.message(Command(commands=['list_users']))
async def list_users(message: types.Message):
    admin_id = 327308286  # Ваш Telegram ID
    if message.from_user.id != admin_id:
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username FROM users")
    users = cursor.fetchall()
    conn.close()

    if users:
        user_list = "\n".join([f"ID: {user[0]}, Username: @{user[1] or 'не указан'}" for user in users])
        await message.answer(f"Список пользователей:\n{user_list}")
    else:
        await message.answer("В базе данных пока нет пользователей.")

@router.message(Command(commands=['broadcast']))
async def broadcast(message: types.Message):
    admin_id = 327308286  # Ваш Telegram ID
    if message.from_user.id != admin_id:
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    if len(message.text.split()) < 2:
        await message.answer("Пожалуйста, укажите текст сообщения после команды. Например:\n/broadcast Ваш текст")
        return

    text = message.text.split(" ", 1)[1]

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()

    for user_id, in users:
        try:
            await bot.send_message(user_id, text)
            await asyncio.sleep(0.1)  # Задержка для предотвращения блокировок
        except Exception as e:
            logging.error(f"Ошибка отправки пользователю {user_id}: {e}")

    await message.answer("Сообщение отправлено всем пользователям.")

@router.message(lambda message: message.text == "Получить карту")
async def get_card_instruction(message: types.Message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    if not user_data:
        set_user_data(user_id, 0, datetime.datetime.now().isoformat())
        user_data = (0, datetime.datetime.now().isoformat())

    daily_count, last_reset = user_data
    last_reset_time = datetime.datetime.fromisoformat(last_reset)
    if (datetime.datetime.now() - last_reset_time).total_seconds() >= 86400:
        daily_count = 0
        last_reset_time = datetime.datetime.now()
        set_user_data(user_id, daily_count, last_reset_time.isoformat())

    if daily_count >= MAX_ATTEMPTS:
        await message.answer("Ваш лимит попыток на сегодня исчерпан. Возвращайтесь завтра!")
        return

    instruction = (
        "\U0001F4DA Как использовать карту:\n"
        "1️⃣ Задумайтесь над вопросом, на который хотите узнать ответ.\n"
        "2️⃣ Нажмите на кнопку ниже, чтобы получить карту."
    )
    button = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Получить карту", callback_data="get_single_card")]]
    )
    await message.answer(instruction, reply_markup=button)

@router.message(lambda message: message.text == "\u2728 О картах")
async def about_cards(message: types.Message):
    about_text = (
        "✨ О метафорических картах:\n"
        "Метафорические ассоциативные карты (МАК) — это инструмент для самопознания, позволяющий разобраться в своих эмоциях и мыслях.\n"
        "Карты не имеют фиксированных значений, а их интерпретация полностью зависит от вашего подсознания."
    )
    await message.answer(about_text)
    
@router.message(lambda message: message.text == "\u2753 Задать вопрос тарологу")
async def ask_tarologist(message: types.Message):
    await message.answer("Перейдите в чат с тарологом, нажав на ссылку: @alyona_venger")

@router.message(lambda message: message.text == "\u2605 Мой тариф")
async def my_tariff(message: types.Message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    if user_data:
        daily_count, last_reset = user_data
        # Определяем текущий лимит пользователя
        user_limit = MAX_ATTEMPTS if daily_count <= MAX_ATTEMPTS else daily_count
        remaining_attempts = max(0, user_limit - daily_count)
        await message.answer(f"★ Ваш тариф:\nОсталось попыток: {remaining_attempts}.")
    else:
        await message.answer("Вы еще не зарегистрированы.")



@router.callback_query(lambda c: c.data == "get_single_card")
async def send_single_card(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user_data = get_user_data(user_id)
    if not user_data:
        set_user_data(user_id, 0, datetime.datetime.now().isoformat())
        user_data = (0, datetime.datetime.now().isoformat())

    daily_count, last_reset = user_data
    last_reset_time = datetime.datetime.fromisoformat(last_reset)

    # Проверяем, нужно ли сбрасывать попытки
    if (datetime.datetime.now() - last_reset_time).total_seconds() >= 86400 and daily_count <= MAX_ATTEMPTS:
        daily_count = 0
        last_reset_time = datetime.datetime.now()

    # Получаем текущий лимит попыток
    user_limit = MAX_ATTEMPTS if daily_count <= MAX_ATTEMPTS else daily_count

    if daily_count >= user_limit:
        await bot.send_message(user_id, "Ваш лимит попыток на сегодня исчерпан. Возвращайтесь завтра!")
        await bot.answer_callback_query(callback_query.id)
        return

    daily_count += 1
    set_user_data(user_id, daily_count, last_reset_time.isoformat())

    remaining_attempts = max(0, user_limit - daily_count)

    try:
        card_image = get_random_card_images(1)[0]
        image_path = os.path.join(CARD_IMAGES_PATH, card_image)
        description = card_descriptions.get(card_image, "Описание отсутствует.")  # Добавлено получение описания

        await bot.send_photo(
            user_id,
            photo=FSInputFile(image_path),
            caption=f"\U0001F4C4 Ваша карта:\n\n{description}\n\nОсталось попыток: {remaining_attempts}."
        )
        mini_instruction = (
            "Внимательно посмотрите на карту, что вы на ней видите? Какой ответ вам приходит в голову? "
            "Не торопитесь, тщательно рассмотрите картинку и нужная вам мысль обязательно придет."
        )
        button = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Я закончил работу с картой", callback_data="end_single_card")]]
        )
        await bot.send_message(user_id, mini_instruction, reply_markup=button)
    except FileNotFoundError:
        await bot.send_message(user_id, "Ошибка: не найдены изображения карт. Пожалуйста, добавьте их в папку.")

    await bot.answer_callback_query(callback_query.id)

@router.callback_query(lambda c: c.data == "end_single_card")
async def end_single_card(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    first_name = callback_query.from_user.first_name or "друг"
    user_data = get_user_data(user_id)
    daily_count = user_data[0] if user_data else 0
    remaining_attempts = max(0, MAX_ATTEMPTS - daily_count)

    question_text = (
        f"{first_name}, удалось ли получить ответ на свой запрос?"
    )
    buttons = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="response_yes")],
            [InlineKeyboardButton(text="Нет", callback_data="response_no")]
        ]
    )
    await bot.send_message(user_id, question_text, reply_markup=buttons)
    await bot.answer_callback_query(callback_query.id)

@router.callback_query(lambda c: c.data == "response_yes")
async def response_yes(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user_data = get_user_data(user_id)
    daily_count = user_data[0] if user_data else 0
    remaining_attempts = max(0, MAX_ATTEMPTS - daily_count)
    await bot.send_message(user_id, f"Замечательно! Осталось попыток: {remaining_attempts}")
    await bot.answer_callback_query(callback_query.id)

@router.callback_query(lambda c: c.data == "response_no")
async def response_no(callback_query: types.CallbackQuery):
    await bot.send_message(
        callback_query.from_user.id,
        "Не расстраивайся, напиши свой вопрос тарологу @alyona_venger, Алёна точно сможет помочь тебе."
    )
    await bot.answer_callback_query(callback_query.id)
  
@router.message(Command(commands=['test_daily']))
async def test_daily(message: types.Message):
    admin_id = 327308286  # Ваш Telegram ID
    if message.from_user.id != admin_id:
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    await send_daily_card()
    await message.answer("Ежедневная рассылка протестирована.")

# Start the bot
async def main():
    dp.include_router(router)

    # Schedule the daily card sending at 09:00 Moscow time
    scheduler.add_job(send_daily_card, CronTrigger(hour=9, minute=0, timezone="Europe/Moscow"))
    scheduler.start()

    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
