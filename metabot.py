from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
import random
import datetime
import asyncio
import logging
import os

# Replace with your actual Telegram bot token
API_TOKEN = '7854106709:AAHeIIyM3aUH8cxzIX68MgOxzA-XgKQ4-r0'

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()

# User data storage (mock database)
user_data = {}

# Maximum daily attempts
MAX_ATTEMPTS = 5

# Define keyboards
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Получить карту")],
        [KeyboardButton(text="Анализ прошлое-настоящее")],
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

# Helper function to initialize user data
def initialize_user_data(user_id):
    if user_id not in user_data:
        user_data[user_id] = {
            'daily_count': 0,
            'last_reset': datetime.date.today(),
            'custom_limit': None
        }

# Command handlers
@router.message(Command(commands=['start']))
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    initialize_user_data(user_id)
    welcome_text = (
        "Привет! Добро пожаловать в уникальный бот с МАК картами от Алены Венгер ✨\n"
        "Здесь ты откроешь для себя огромный мир самопознания, где найдешь ответы на все свои вопросы 🥰\n\n"
        "МАК карты - метафорические карты, с помощью которых ты можешь заглянуть в свое подсознание без психологов и других специалистов.\n"
        "Можешь достать любую информацию, принять важное решение или провести самокоучинг."
    )
    await message.answer(welcome_text, reply_markup=main_menu)

@router.message(lambda message: message.text == "Получить карту")
async def get_card_instruction(message: types.Message):
    user_id = message.from_user.id
    initialize_user_data(user_id)
    instruction = (
        "\U0001F4DA Как использовать карту:\n"
        "1️⃣ Задумайтесь над вопросом, на который хотите узнать ответ.\n"
        "2️⃣ Нажмите на кнопку ниже, чтобы получить карту."
    )
    button = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Получить карту", callback_data="get_single_card")]]
    )
    await message.answer(instruction, reply_markup=button)

@router.callback_query(lambda c: c.data == "get_single_card")
async def send_single_card(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    initialize_user_data(user_id)
    user_limit = user_data[user_id].get('custom_limit', MAX_ATTEMPTS)

    if user_data[user_id]['daily_count'] >= user_limit:
        await bot.send_message(user_id, "Ваш лимит попыток на сегодня исчерпан. Возвращайтесь завтра!")
        await bot.answer_callback_query(callback_query.id)
        return

    user_data[user_id]['daily_count'] += 1

    try:
        card_image = get_random_card_images(1)[0]
        image_path = os.path.join(CARD_IMAGES_PATH, card_image)
        await bot.send_photo(user_id, photo=FSInputFile(image_path), caption="\U0001F4C4 Ваша карта")
    except FileNotFoundError:
        await bot.send_message(user_id, "Ошибка: не найдены изображения карт. Пожалуйста, добавьте их в папку.")

    await bot.answer_callback_query(callback_query.id)

@router.message(lambda message: message.text == "Анализ прошлое-настоящее")
async def analysis_instruction_1(message: types.Message):
    user_id = message.from_user.id
    initialize_user_data(user_id)
    instruction = (
        "1️⃣ Сделай глубокий вдох, можно закрыть глаза. Подумай о вопросе или ситуации, которая тебя волнует.\n"
        "Когда почувствуешь, что готов/а, нажимай на кнопку ниже, чтобы получить карту."
    )
    button = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Получить карту", callback_data="analysis_past")]]
    )
    await message.answer(instruction, reply_markup=button)

@router.callback_query(lambda c: c.data == "analysis_past")
async def analysis_past(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    initialize_user_data(user_id)
    user_limit = user_data[user_id].get('custom_limit', MAX_ATTEMPTS)

    if user_data[user_id]['daily_count'] >= user_limit:
        await bot.send_message(user_id, "Ваш лимит попыток на сегодня исчерпан. Возвращайтесь завтра!")
        await bot.answer_callback_query(callback_query.id)
        return

    user_data[user_id]['daily_count'] += 1

    try:
        card_image = get_random_card_images(1)[0]
        image_path = os.path.join(CARD_IMAGES_PATH, card_image)
        await bot.send_photo(user_id, photo=FSInputFile(image_path), caption="\U0001F4C4 Карта: Прошлое")
    except FileNotFoundError:
        await bot.send_message(user_id, "Ошибка: не найдены изображения карт. Пожалуйста, добавьте их в папку.")

    await bot.answer_callback_query(callback_query.id)

@router.message(Command(commands=['set_limit']))
async def set_custom_limit(message: types.Message):
    try:
        user_id, limit = map(int, message.text.split()[1:])
        if user_id in user_data:
            user_data[user_id]['custom_limit'] = limit
            await message.reply(f"Персональный лимит для пользователя {user_id} установлен на {limit} попыток.")
        else:
            await message.reply("Пользователь не найден.")
    except (ValueError, IndexError):
        await message.reply("Используйте: /set_limit <user_id> <limit>")

# Start the bot
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
