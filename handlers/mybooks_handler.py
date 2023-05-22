from __future__ import annotations

from datetime import datetime

from aiogram import Bot
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Update
)
from aiogram.utils.exceptions import BotBlocked
from sqlalchemy import select

from database.database import async_sessionmaker
from database.db_requests import (
    get_book_data,
    select_book,
    select_user,
    select_users_books,
    update_book,
    update_book_transfer,
    update_book_transfer_by_candidate,
    update_remain_time, update_book_canceling_transfer,
)
from database.models import Book, BookData
from handlers.lexicon import declensions


# todo return_to_booklist repeats in every handler

async def cmd_mybooks(msg: Message | CallbackQuery, state: FSMContext):
    await state.reset_state()
    await state.finish()
    user_id = (int(msg.data.split('_')[1]) if isinstance(msg, CallbackQuery)
               else msg.from_user.id)
    books = await select_users_books(user_id)

    if not books:
        return await msg.answer(
            'Сейчас у тебя нет книг.\n\nДобавь свою книгу для обмена '
            'с помощью команды /addbook или поищи книгу для чтения '
            'командой /findbook.'
        )

    keyboard = InlineKeyboardMarkup()
    for book in books:
        title, author, genre = await get_book_data(book)
        keyboard.add(
            InlineKeyboardButton(
                f'"{title}", {author}, {book.status}',
                callback_data=f'detailed-book_{book.id}',
            )
        )

    text = ('Выбери нужную книгу, чтобы узнать подробную информацию '
            'или изменить её статус.')
    return (await msg.answer(text, reply_markup=keyboard)
            if isinstance(msg, Message)
            else (await msg.message.answer(text, reply_markup=keyboard))
            )


async def info_book(callback: CallbackQuery):
    book_id = int(callback.data.split('_')[1])
    book = await select_book(book_id)

    keyboard = InlineKeyboardMarkup(row_width=1)
    return_book_list = InlineKeyboardButton(
        'Вернуться к списку книг',
        callback_data=f'user-books_{callback.from_user.id}',
    )

    # if book.status == 'Свободна':
    if book.status_id == 1:
        keyboard.add(
            InlineKeyboardButton(
                'Начать читать (90 дней)',
                callback_data=f'status-own-read_{book_id}_3',
            ),
            return_book_list
        )

    # elif book.status == 'Забронирована':
    elif book.status_id == 2:
        cancel_booking = InlineKeyboardButton(
            'Отменить бронь', callback_data=f'status-free_{book_id}_1'
        )
        transfer_book = InlineKeyboardButton(
            'Передать книгу', callback_data=f'transfer-book_{book_id}'
        )
        cancel_transferring = InlineKeyboardButton(
            'Отменить передачу книги',
            callback_data=f'status-free_{book_id}_1',
        )

        if not book.is_transferred:
            keyboard.add(cancel_booking, transfer_book, return_book_list)
        else:
            keyboard.add(cancel_transferring, return_book_list)
    # elif book.status == 'Читается':
    elif book.status_id == 3:
        keyboard.add(
            InlineKeyboardButton(
                'Закончить чтение',
                callback_data=f'status-own-free_{book_id}_1'
            ),
            return_book_list
        )

    remain_text = '\n' # todo move this block to lexicon file?
    if book.remain_time:
        remain_time = (book.remain_time - datetime.now()).days
        if remain_time % 10 == 1 and remain_time not in range(5, 21):
            remain_text = f'(остался {remain_time} день)\n'
        elif remain_time % 10 in (2, 3, 4) and remain_time not in range(5, 21):
            remain_text = f'(осталось {remain_time} дня)\n'
        else:
            remain_text = f'(осталось {remain_time} дней)\n'

    title, author, genre = await get_book_data(book)

    text = (f'Книга: {title}\n'
            f'{declensions[0][len(author) > 1]}: {author}\n'
            f'{declensions[1][len(genre) > 1]}: {genre}\n'
            f'Статус: {book.status.lower()} ' + remain_text +
            f'Город: {book.city}'
            )
    if book.candidate_telegram_id:
        candidate = await select_user(book.candidate_telegram_id)
        url = (f'@{candidate.username}' if candidate.username is not None
               else f'<a href="tg://user?id={candidate.telegram_id}">'
                    f'Пользователь</a>'
               )
        text += f'\n\nЭту книгу хочет взять {url}'
    await callback.message.delete()
    await callback.message.answer(
        text=text,
        reply_markup=keyboard,
        parse_mode='HTML'
    )


async def return_my_books(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await cmd_mybooks(callback, state)


async def change_own_status(callback: CallbackQuery):
    book_id = int(callback.data.split('_')[1])
    book_status = int(callback.data.split('_')[2])
    book = await select_book(book_id)
    title, author, genre = await get_book_data(book)
    book_data_text = f'"{title}", {author}'
    await update_book(book_id, book_status)
    await callback.message.delete()
    text = (f'Статус книги {book_data_text} изменён на: "Свободна".'
            if book_status == 1
            else (f'Статус книги {book_data_text} изменён на: "Читается".\n'
                  f'На чтение книги отводится до 90 дней, но в случае '
                  f'необходимости ты сможешь продлить чтение.')
            )
    await callback.message.answer(text)


async def change_status(callback: CallbackQuery):
    book_id = int(callback.data.split('_')[1])
    book_status = int(callback.data.split('_')[2])
    book = await select_book(book_id)
    title, author, genre = await get_book_data(book)
    candidate_id = book.candidate_telegram_id
    await update_book_canceling_transfer(book_id)
    # await update_book(book_id, book_status)

    book_data_text = f'"{title}", {author}'
    initiator = callback.from_user.id
    owner = book.telegram_id
    if initiator == candidate_id:
        user_url = (
            f'@{callback.from_user.username}'
            if callback.from_user.username is not None
            else f'<a href="tg://user?id={callback.from_user.id}">'
                 f'Пользователь</a>'
        )
    else:
        user_url = (
            f'@{callback.from_user.username}'
            if callback.from_user.username is not None
            else f'<a href="tg://user?id={callback.from_user.id}">'
                 f'Владелец книги</a>'
        )
    await callback.bot.send_message(
        chat_id=candidate_id if initiator == owner else owner,
        text=f'{user_url} отменил передачу книги {book_data_text}.',
        parse_mode='HTML'
    )


    # owner_url = (
    #     f'@{callback.from_user.username}'
    #     if callback.from_user.username is not None
    #     else f'<a href="tg://user?id={callback.from_user.id}">'
    #          f'Владелец книги</a>'
    # )

    # await callback.bot.send_message(
    #     chat_id=candidate_id,
    #     text=f'{owner_url} отменил передачу книги {book_data_text}.',
    #     parse_mode='HTML'
    # )

    await callback.message.delete()
    text = (f'Статус книги {book_data_text} изменён на: "Свободна".'
            if any([book_status == 1, book_status == 2])
            else (f'Статус книги {book_data_text} изменён на: "Читается".\n'
                  f'На чтение книги отводится до 90 дней, но в случае '
                  f'необходимости ты сможешь продлить чтение.')
            )
    # await callback.message.answer(text)
    await (
        callback.message.answer(text) if initiator == owner
        else callback.bot.send_message(chat_id=owner, text=text)
    )


async def increase_reading_time(callback: CallbackQuery):
    book_id = int(callback.data.split('_')[1])
    await update_remain_time(book_id)
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(
            'Вернуться списку книг',
            callback_data=f'user-books_{callback.from_user.id}',
        )
    )
    await callback.message.delete()
    await callback.message.answer(
        text=f'Статус "Читается" продлён на 15 дней.\n',
        reply_markup=keyboard,
    )


async def transfer_book(callback: CallbackQuery):
    book_id = int(callback.data.split('_')[1])
    book = await select_book(book_id)
    await update_book_transfer(book_id)
    candidate = await select_user(book.candidate_telegram_id)
    if not candidate:
        await callback.message.delete()
        await callback.message.answer(
            f'Невозможно передать книгу.\n'
        )
    url = (f'@{candidate.username}' if candidate.username is not None
           else f'<a href="tg://user?id={candidate.telegram_id}">'
                f'пользователь</a>'
           )
    title, author, genre = await get_book_data(book)
    book_data_text = f'"{title}", {author}'
    await callback.message.delete()
    await callback.message.answer(
        f'Делиться книгами круто!\n'
        f'Как только {url} подтвердит получение книги {book_data_text}, '
        f'она пропадёт из твоего списка книг',
        parse_mode='HTML'
    )

    keyboard_for_candidate = InlineKeyboardMarkup(row_width=1)
    keyboard_for_candidate.add(
        InlineKeyboardButton(
            'Подтвердить получение книги',
            callback_data=f'confirmation-book-transfer_{book_id}',
        ),
        InlineKeyboardButton(
            'Отменить передачу книги',
            callback_data=f'status-free_{book_id}_{book.status_id}',
        )
    )
    url_owner = (f'@{callback.from_user.username}'
                 if callback.from_user.username is not None
                 else f'<a href="tg://user?id={callback.from_user.id}">'
                      f'пользователь</a>'
           )
    await callback.bot.send_message(
        chat_id=candidate.telegram_id,
        text=f'Привет!\n{url_owner} хочет передать тебе книгу '
             f'{book_data_text}.\n\n'
             f'Пожалуйста, когда получишь её, не забудь сообщить мне об этом!',
        reply_markup=keyboard_for_candidate,
        parse_mode='HTML'
    )


async def confirmation_book_transfer(callback: CallbackQuery):
    book_id = int(callback.data.split('_')[1])
    book = await select_book(book_id)
    title, author, genre = await get_book_data(book)
    book_data_text = f'"{title}", {author}'
    await update_book_transfer_by_candidate(
        book_id,
        book.candidate_telegram_id
    )

    # todo move this block to lexicon file?
    remain_text = '\n'
    if book.remain_time:
        remain_time = (book.remain_time - datetime.now()).days
        if remain_time % 10 == 1 and remain_time not in range(5, 21):
            remain_text = f'(остался {remain_time} день).'
        elif remain_time % 10 in (2, 3, 4) and remain_time not in range(5, 21):
            remain_text = f'(осталось {remain_time} дня).'
        else:
            remain_text = f'(осталось {remain_time} дней).'

    await callback.message.delete()
    await callback.message.answer(
            text=f'Книга {book_data_text} добавлена в список твоих книг.\n'
                 f'Статус: "Читается" {remain_text}'
        )


async def notification_remaining_days_for_reading(bot: Bot):
    ...
    # # TODO булево значение в таблицу экзмепляров книг,
    # #  для установления флага продлевалось чтение или нет
    # day_now = datetime.now()
    # async with async_sessionmaker() as session:
    #     result = await session.execute(select(Book))
    #     books = result.scalars().all()
    #     for book in books:
    #         book_data = await session.get(BookData, book.book_id)
    #         if book.status_id != 3:
    #             continue
    #         else:
    #             if book.remain_time <= day_now:
    #                 book.status_id = 1
    #                 book.remain_time = None
    #                 await session.commit()
    #                 await bot.send_message(
    #                     book.telegram_id,
    #                     f'Привет!\n'
    #                     f'Ты читаешь книгу "{book_data.title.capitalize()}" уже 90 дней,\n'
    #                     f'статус книги автоматически изменен на: "Свободна".'
    #                 )
    #             elif (book.remain_time - day_now).days == 7:
    #                 inlines_btn = InlineKeyboardMarkup(row_width=1)
    #                 inlines_btn.add(
    #                     InlineKeyboardButton(
    #                         'Продлить чтение',
    #                         callback_data=f'extension reading_{book.id}',
    #                     ),
    #                     InlineKeyboardButton(
    #                         'Закончить чтение',
    #                         callback_data=f'status free_{book.id}',
    #                     ),
    #                 )
    #                 await bot.send_message(
    #                     book.telegram_id,
    #                     text=f'Привет!\n'
    #                          f'Ты читаешь книгу "{book_data.title.capitalize()}" уже 83 дня.\n'
    #                          f'Будешь ли продлевать статус "Читается"?\n '
    #                          f'Если его не продлить, то через 7 дней\n '
    #                          f'он автоматически изменится на "Свободна".',
    #                     reply_markup=inlines_btn
    #
    #                 )


async def error_bot_blocked_handler(update: Update, exception: BotBlocked): # todo exceptions after main logic
    print('Бот заблокирован пользователем, залогировать?? обработать?')
    return True


def register_mybooks(dispatcher):
    dispatcher.register_message_handler(
        cmd_mybooks, commands='mybooks', state='*'
    )
    # dp.register_message_handler(
    #     my_books,
    #     Text(equals='Мои книги'),
    # )
    dispatcher.register_callback_query_handler(
        return_my_books,
        Text(startswith='user-books_'),
    )
    dispatcher.register_callback_query_handler(
        info_book,
        Text(startswith='detailed-book_'),
    )
    dispatcher.register_callback_query_handler(
        change_status,
        Text(startswith='status-read_'),
    )
    dispatcher.register_callback_query_handler(
        change_own_status,
        Text(startswith='status-own-read_')
    )
    dispatcher.register_callback_query_handler(
        change_own_status,
        Text(startswith='status-own-free_')
    )
    dispatcher.register_callback_query_handler(
        change_status,
        Text(startswith='status-free_'),
    )
    # dispatcher.register_callback_query_handler(
    #     change_status_booked,
    #     Text(startswith='status-booked_'),
    # )
    dispatcher.register_callback_query_handler(
        transfer_book,
        Text(startswith='transfer-book_'),
    )
    dispatcher.register_callback_query_handler(
        confirmation_book_transfer,
        Text(startswith='confirmation-book-transfer_'),
    )
    dispatcher.register_callback_query_handler(
        increase_reading_time,
        Text(startswith='extension-reading'),
    )
    dispatcher.register_errors_handler(
        error_bot_blocked_handler,
        exception=BotBlocked,
    )
