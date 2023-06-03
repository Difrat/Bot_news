from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import TOKEN_API, API_key
from parser import do_parse
from datetime import datetime
import requests
import json
import aioschedule
import asyncio
import psycopg2


now = datetime.now()
current_time = now.strftime("%H:%M:%S")

bot = Bot(TOKEN_API)
dp = Dispatcher(bot)


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
        await callback.message.answer(
            text=f'<b>{row[0]}</b>\n\n{row[2]}\n\n <b>Ссылка  на источник:</b> <a href="{row[1]}">{row[1]}</a>',
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
async def get_wether(message: types.Message):
    city = message.text.strip().lower()
    res = requests.get(f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_key}&units=metric&lang=ru')
    data = json.loads(res.text)
    if data['cod'] == 200:
        await bot.send_message(message.chat.id,
                               f'Температура: {data["main"]["temp"]} C;\n Небо: {data["weather"][0]["description"]};\n Влажность: {data["main"]["humidity"]} %;')


async def scheduler():
    aioschedule.every(15).minutes.do(do_parse)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def on_startup(_):
    asyncio.create_task(scheduler())


executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
