import os
import typing as tp
import datetime

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
import aiohttp
import motor.motor_asyncio
from motor.motor_asyncio import AsyncIOMotorClient


bot = Bot(token=os.environ['BOT_TOKEN'])
dp = Dispatcher(bot)

client: AsyncIOMotorClient
db: motor.motor_asyncio.AsyncIOMotorDatabase


class MyError(RuntimeError):
    pass


@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer("Hi!\nI'm cinema bot!\nMade by iluhahahanich.")
    await db.users.update_one(
        {'_id': message['from']['id']},
        {'$setOnInsert': {'history': [], 'stats': {}}},
        upsert=True)


@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    await message.answer("/stats - show advised film counts for user\n"
                         "/history - show user's history\n")


def _format_hist(hist: list[tuple[datetime.datetime, str]]):
    return '\n'.join(date.strftime('%Y-%m-%d %H:%M') + " " + query for date, query in hist) \
           or 'history is empty'


@dp.message_handler(commands=['history'])
async def cmd_history(message: types.Message):
    hist = (await db.users.find_one({'_id': message['from']['id']}))['history']
    await message.answer('*History*', parse_mode='Markdown')
    await message.answer(_format_hist(hist))


def _format_stats(stats: dict[str, int]):
    return '\n'.join(query + ": " + str(count) for query, count in sorted(stats.items(), key=lambda x: x[1])) \
           or 'stats is empty'


@dp.message_handler(commands=['stats'])
async def cmd_stats(message: types.Message):
    stats = (await db.users.find_one({'_id': message['from']['id']}))['stats']
    await message.answer('*Stats*', parse_mode='Markdown')
    await message.answer(_format_stats(stats))


def create_film_description(json: dict[str, tp.Any], link: str):
    return f"*{json['fullTitle']}*\n" \
           f"Рейтинг: _{json['imDbRating']}_\n" \
           f"Длительность: _{json['runtimeStr']}_\n" \
           f"Описание: _{json['plotLocal']}_\n" \
           f"Смореть: {link}"


async def get_first_link(query: str, session: aiohttp.ClientSession):
    url = 'https://www.googleapis.com/customsearch/v1'
    params = {
        'key': os.environ['SE_KEY'],
        'cx': os.environ['SE_ID'],
        'q': query,
        'num': 1,
    }
    async with session.get(url=url, params=params) as resp:
        res = await resp.json()
        return res['items'][0]['link'] if 'items' in res else ''


async def search_title(text: str, session: aiohttp.ClientSession):
    async with session.get(f"https://imdb-api.com/ru/API/"
                           f"Search/{os.environ['IMDB_KEY']}/{text}") as search:
        if not search.ok:
            raise MyError("Something vent wrong")

        search_res = (await search.json())['results']

        if not search_res:
            raise MyError("Couldn't find :(")

        return search_res[0]


async def search_film_data(title: str, session: aiohttp.ClientSession):
    async with session.get(f"https://imdb-api.com/ru/API/"
                           f"Title/{os.environ['IMDB_KEY']}/"
                           f"{title}") as resp:
        if not resp.ok:
            raise MyError("Something vent wrong")

        return await resp.json()


@dp.message_handler()
async def echo(message: types.Message):
    await db.users.update_one({'_id': message['from']['id']},
                              {'$push': {'history': [datetime.datetime.now(), message.text]}},
                              upsert=True)

    try:
        async with aiohttp.ClientSession() as session:
            title = await search_title(message['text'], session)
            link = await get_first_link(title['title'] + (title.get('description', ' ') or ''), session)
            json = await search_film_data(title['id'], session)

            await message.answer_photo(json['image'],
                                       caption=create_film_description(json, link), parse_mode='Markdown')

            db.users.update_one({'_id': message['from']['id']},
                                {'$inc': {'stats.' + json['fullTitle']: 1}},
                                upsert=True)
    except MyError as err:
        await message.answer(str(err))


if __name__ == '__main__':
    client = AsyncIOMotorClient(os.environ['MONGO_KEY'])
    db = client.botdb

    executor.start_polling(dp)

