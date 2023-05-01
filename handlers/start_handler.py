from __future__ import annotations

import asyncio

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message
)

from database.db_requests import (
    insert_location,
    insert_user,
    select_location,
    select_user
)
from database.models import Location


# TODO - прописать отмену для каждого шага с возвратом в меню старт -
# TODO при повторной отправке города - новый поиск
# TODO - выдача городов с пагинацией?? -
# todo вынести клавиатуры и машины состояний в отдельные файлы?


class FSMLocation(StatesGroup):
    user_location = State()
    check_msg_type = State()
    db_location = State()


async def cmd_start(msg: Message, state: FSMContext):
    await state.reset_state()
    user_id = msg.from_user.id
    name = msg.from_user.first_name
    user = await select_user(user_id)
    if user is not None:
        await msg.answer(f'Привет, {name}! Смотри, что могу:\n'
                         f'Список команд (с описанием...):\n'
                         f'/start\n/addbook\n/rules\n/mybooks\n'
                         f'/findbook\n/profile')
        return
    await insert_user(
        user_id,
        name,
        msg.from_user.last_name,
        msg.from_user.username
    )
    await msg.answer(
        f'Привет, {name}!\nЯ бот для обмена книгами.\n'
        f'С моей помощью ты можешь поделиться своими книгами, чтобы они '
        f'обрели вторую жизнь, или сам взять книгу у кого-то, кому она '
        f'больше не нужна.\n'
        f'Все это безвозмездно, но есть некоторые ограничения, с которыми '
        f'ты можешь ознакомиться в разделе /rules.'
    )
    await asyncio.sleep(0.7)
    await msg.answer(
        'Для успешной работы мне нужно кое-что о тебе знать. Пожалуйста, '
        'напиши название города, в котором ты проживаешь!\n'
        'Это нужно мне, чтобы находить для тебя книги из твоего города.'
    )
    await FSMLocation.user_location.set()


async def location_keyboard(locations: Location):
    keyboard = InlineKeyboardMarkup()
    for location in locations:
        keyboard.add(
            InlineKeyboardButton(
                f'{location.city}, {location.region}',
                callback_data=f'location_{location.id}'
            )
        )
    return keyboard


async def get_location(msg: Message | CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['user_location'] = msg.text
    locations = await select_location(msg.text)
    if not locations:
        await msg.answer(
            'Извини, город не найден. Пожалуйста, попробуй еще раз:'
        )
        return
    keyboard = await location_keyboard(locations)
    await msg.answer('Выбери город из списка ниже:', reply_markup=keyboard)
    await FSMLocation.db_location.set()


async def save_location(callback: CallbackQuery, state: FSMContext):
    location_id = int(callback.data.split('_')[1])
    async with state.proxy() as data:
        data['db_location'] = location_id
    city, region = await insert_location(location_id, callback.from_user.id)
    await callback.message.delete()
    await callback.message.answer(
        f'Записал!\nГород: {city}, ({region})\n'
        f'Изменить местоположение при необходимости можно в меню /profile.\n\n'
        f'Желаю приятного чтения!')
    await state.finish()


def register_start(dispatcher: Dispatcher):
    dispatcher.register_message_handler(cmd_start, commands='start', state='*')
    dispatcher.register_message_handler(
        get_location, state=FSMLocation.user_location
    )
    dispatcher.register_callback_query_handler(
        save_location,
        Text(startswith='location_'),
        state=FSMLocation.db_location,
    )
