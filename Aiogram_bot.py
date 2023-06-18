import logging
import requests
import json
import aioschedule
import asyncio
import psycopg2

from config import API_key, TOKEN_API_WebHook
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from parser import do_parse, remove_yesterday_table_data
from aiogram import Bot, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import Dispatcher
from aiogram.utils.executor import start_webhook



# webhook settings
WEBHOOK_HOST = 'https://7a7b-77-34-132-24.ngrok-free.app'
WEBHOOK_PATH = '/path/to/api'
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# webserver settings
WEBAPP_HOST = 'localhost'
WEBAPP_PORT = 3001

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN_API_WebHook)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

ikb = InlineKeyboardMarkup(resize_keyboard=True, row_width=2)
ibtn1 = InlineKeyboardButton(text='Хабр', url='https://habr.com')
ibtn2 = InlineKeyboardButton(text='Ютуб', url='https://www.youtube.com')
ibtn3 = InlineKeyboardButton(text='Google', url='https://www.google.com')
pull = InlineKeyboardButton(text='Выгрузить статьи', callback_data='get_news')
ikb.add(ibtn1, ibtn2, ibtn3, pull)


@dp.callback_query_handler(lambda c: c.data == 'get_news')
async def get_news(callback: types.CallbackQuery):
    con = psycopg2.connect(
        database="parse_news",
        user="postgres",
        password="admin",
        host="localhost",
        port="5432"
    )
    cur = con.cursor()
    cur.execute('SELECT title, url_href, text FROM ria_news_table ORDER BY add_date DESC LIMIT 5')
    rows = cur.fetchall()
    for row in rows:
        if len(row[2]) <= 4096:
            await callback.message.answer(
                text=f'<b>{row[0]}</b>\n\n{row[2]}\n\n <b>Ссылка  на источник:</b> <a href="{row[1]}">{row[1]}</a>',
                parse_mode='HTML', disable_web_page_preview=True)
            await asyncio.sleep(1)
        else:
            await callback.message.answer(
                text=f'<b>{row[0]}</b>\n\n{row[2][0:4096]} . . .\n\n <b>Ссылка  на источник:</b> <a href="{row[1]}">{row[1]}</a>',
                parse_mode='HTML', disable_web_page_preview=True)
            await asyncio.sleep(1)

    cur.close()
    con.close()


@dp.message_handler(commands=['start'])
async def help_commands(message: types.message):
    await message.answer(
        text=f'Добро пожаловать в чат бот, {message["from"]["first_name"]} {message["from"]["last_name"]}')
    await message.delete()
    await message.answer(text='Вы можете посетить один из указанных сайтов или ознакомится с новостной лентой на'
                              ' "РИА Новости"', reply_markup=ikb)


@dp.message_handler(commands=['keyboard'])
async def get_ikb(message: types.message):
    await message.answer(text='Выберите сайт...', reply_markup=ikb)
    await message.delete()


@dp.message_handler(content_types=['text'])
async def get_weather(message: types.Message):
    city = message.text.strip().lower()
    res = requests.get(f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_key}&units=metric&lang=ru')
    data = json.loads(res.text)
    if data['cod'] == 200:
        await bot.send_message(message.chat.id,
                               f'Температура: {data["main"]["temp"]} C;\n Небо: {data["weather"][0]["description"]};\n Влажность: {data["main"]["humidity"]} %;')


async def scheduler():
    aioschedule.every().day.at('00:05').do(remove_yesterday_table_data)
    aioschedule.every(15).minutes.do(do_parse)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(scheduler())


async def on_shutdown(dp):
    logging.warning('Shutting down..')

    await bot.delete_webhook()

    await dp.storage.close()
    await dp.storage.wait_closed()

    logging.warning('Bye!')


if __name__ == '__main__':
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )

