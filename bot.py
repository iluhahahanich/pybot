import os
import typing as tp

import motor.motor_asyncio
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
import aiohttp
import datetime
from motor.motor_asyncio import AsyncIOMotorClient


bot = Bot(token=os.environ['BOT_TOKEN'])
dp = Dispatcher(bot)

client: AsyncIOMotorClient
db: motor.motor_asyncio.AsyncIOMotorDatabase


@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer("Hi!\nI'm cinema bot!\nMade by iluhahahanich.")
    await db.users.update_one(
        {'_id': message['from']['id']},
        {'$setOnInsert': {'history': [], 'stats': {}}},
        upsert=True)


@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    await message.answer("I can only do things from task")


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


def create_film_description(json: dict[str, tp.Any]):
    return f"*{json['fullTitle']}*\n" \
           f"Рейтинг: _{json['imDbRating']}_\n" \
           f"Длительность: _{json['runtimeStr']}_\n" \
           f"Описание: _{json['plotLocal']}_\n" \
           f"Смореть: https://www.imdb.com/title/{json['id']}"


@dp.message_handler()
async def echo(message: types.Message):
    await db.users.update_one({'_id': message['from']['id']},
                              {'$push': {'history': [datetime.datetime.now(), message.text]}},
                              upsert=True)
    await message.answer('updated')
    req_res = message.text
    # async with aiohttp.ClientSession() as session:
    #     # print(message)
    #     async with session.get(f"https://imdb-api.com/ru/API/"
    #                            f"Search/{os.environ['IMDB_KEY']}/{message['text']}") as search:
    #         if search.ok:
    #             json = await search.json()
    #             # print(json)
    #             search_res = json['results']
    ##             search_res = (await search.json())['results']

    #
    #             if not search_res:
    #                 await message.answer("Couldn't find")
    #                 return
    #
    #             title_id = search_res[0]['id']
    #
    #             async with session.get(f"https://imdb-api.com/ru/API/"
    #                                    f"Title/{os.environ['IMDB_KEY']}/{title_id}") as resp:
    #
    #                 if resp.ok:
    #                     json = await resp.json()
    #                     # print(json)
    #                     await message.answer_photo(
    #                         json['image'], caption=create_film_description(json), parse_mode='Markdown')
    #
    #                     # db.upadate_one({'_id': message['from']['id']}, {'$inc': {json['fullTitle']: 1}})
    #
    #                 else:
    #                     await message.answer("Something vent wrong")
    #         else:
    #             await message.answer("Something vent wrong")
    db.users.update_one({'_id': message['from']['id']},
                        {'$inc': {'stats.' + req_res: 1}},
                        upsert=True)


if __name__ == '__main__':
    client = AsyncIOMotorClient('localhost', 27017)
    db = client.botdb

    executor.start_polling(dp)


# {"message_id": 130, "from": {"id": 831442399, "is_bot": false, "first_name": "Илья", "last_name": "Угрин", "username": "iluhahahanich", "language_code": "en"}, "chat": {"id": 831442399, "first_name": "Илья", "last_name": "Угрин", "username": "iluhahahanich", "type": "private"}, "date": 1639684763, "text": "io"}
