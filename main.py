import asyncio

from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
# from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import async_sessionmaker

from config_data.config import BOT_TOKEN
from database.database import close_database, connect_to_database, engine
from handlers.addbook_handler import register_addbook
from handlers.bot_commands import set_default_commands
# from handlers.cancel_handler import register_cancel
from handlers.findbook_handler import register_findbook
from handlers.mybooks_handler import notification_remaining_days_for_reading
from handlers.mybooks_handler import register_mybooks
from handlers.rules_handler import register_rules
from handlers.start_handler import register_start


async def on_startup(dp):
    dp.bot['db'] = await connect_to_database()
    await set_default_commands(dp)


async def on_shutdown(dp):
    async with dp.bot['db']() as session:
        await close_database(session)


def register_all_handlers(dp):
    # register_cancel(dp)
    register_rules(dp)
    register_start(dp)
    register_mybooks(dp)
    register_findbook(dp)
    register_addbook(dp)


if __name__ == '__main__':

    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()

    dp = Dispatcher(bot, storage=storage)

    register_all_handlers(dp)

    loop = asyncio.get_event_loop()
    loop.create_task(on_startup(dp))

    # scheduler = AsyncIOScheduler(timezone='Europe/Moscow')
    # scheduler.add_job(
    #     notification_remaining_days_for_reading,
    #     trigger='interval',
    #     hours=24,
    #     kwargs={'bot': bot},
    #     start_date='2023-04-20 10:00:00',
    # )
    # scheduler.start()

    dp.bot['db'] = async_sessionmaker(engine, expire_on_commit=False)

    executor.start_polling(dp, on_shutdown=on_shutdown, skip_updates=True)
