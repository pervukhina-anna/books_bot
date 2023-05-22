from __future__ import annotations

from datetime import datetime

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
    get_book_data,
    select_book,
    select_books_by_keyword,
    select_user,
    update_book, select_books_by_home_location,
)
from handlers.lexicon import declensions


# TODO - вынести кейборд в отдельный метод-файл?
# TODO - вынести все стейты в отдельный файл?
# TODO - поиск по другим городам (доработать ввод города + поиск)
# todo check for code duplicate!!!


class FSMFindBook(StatesGroup):
    by_keyword = State()
    by_keyword_detail = State()
    by_keyword_return = State()

    by_location = State()


async def cmd_findbook(msg: Message, state: FSMContext):
    await state.reset_state()
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(
        'Поиск по ключевым словам', callback_data='search-keyword'
    )
    )
    keyboard.add(InlineKeyboardButton(
        'Все книги в твоём городе', callback_data='search-location'
    )
    )
    await msg.answer(
        'Сейчас доступно два вида поиска:',
        reply_markup=keyboard
    )


async def search_by_keyword(callback: CallbackQuery):
    await callback.message.delete()
    if callback.data == 'search-keyword':
        await FSMFindBook.by_keyword.set()
        return await callback.message.answer(
            'Для поиска по ключевым словам введи название '
            'книги, её автора или жанр!'
        )
    return await FSMFindBook.by_location.set()


async def result_by_keyword(msg: Message | CallbackQuery, state: FSMContext):
    if not isinstance(msg, CallbackQuery):
        await state.update_data(by_keyword=msg.text)
    data = await state.get_data()
    by_keyword = data.get('by_keyword')
    books = await select_books_by_keyword(msg.from_user.id, by_keyword)

    # if books is None:
    if len(books) == 0:
        await msg.answer(
            'По твоему запросу ничего не найдено, попробуй ввести его '
            'по-другому. Или поищи другую книгу для чтения.'
            )
        return

    keyboard = InlineKeyboardMarkup()
    for book in books:
        title, author, genre = await get_book_data(book)
        keyboard.add(
            InlineKeyboardButton(
                f'"{title}", {author}, {book.status}',
                callback_data=f'search_{book.id}'
            )
        )
    text = 'Вот что могу предложить из книг для обмена:'
    await FSMFindBook.by_keyword_detail.set()
    return (await msg.answer(text, reply_markup=keyboard)
            if isinstance(msg, Message)
            else (await msg.message.delete()
                  and await msg.message.answer(text, reply_markup=keyboard)
                  )
            )


async def detail_by_keyword(callback: CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split('_')[1])
    async with state.proxy() as data:
        data['by_keyword_detail'] = callback.data
    data = await state.get_data()
    by_keyword = data.get('by_keyword')

    book = await select_book(book_id)
    title, author, genre = await get_book_data(book)
    detail_keyboard = InlineKeyboardMarkup()
    detail_keyboard.add(
        InlineKeyboardButton(
            'Хочу взять', callback_data=f'want_{book.id}'
        ),
        InlineKeyboardButton(
            'Вернуться к списку книг', callback_data=f'return_{by_keyword}'
        )
    )
    await callback.message.delete()
    await callback.message.answer(
        f'Книга: {title}\n'
        f'{declensions[0][len(author) > 1]}: {author}\n'
        f'{declensions[1][len(genre) > 1]}: {genre}\n'
        f'Статус: {book.status}\n'
        f'Город: {book.city}',
        reply_markup=detail_keyboard,
    )
    await FSMFindBook.by_keyword_return.set()


async def want_take(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    by_keyword = data.get('by_keyword')
    book_id = int(callback.data.split('_')[1])

    book = await select_book(book_id)
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(
            'Вернуться к списку книг', callback_data=f'return_{by_keyword}'
        )
    )

    if book.status_id == 3:

        remain_text = '\n'  # todo move this block to lexicon file or dif function? defenitely yes
        if book.remain_time:
            remain_time = (book.remain_time - datetime.now()).days
            if remain_time % 10 == 1 and remain_time not in range(5, 21):
                remain_text = f'(остался {remain_time} день).\n'
            elif (remain_time % 10 in (2, 3, 4)
                  and remain_time not in range(5, 21)):
                remain_text = f'(осталось {remain_time} дня).\n'
            else:
                remain_text = f'(осталось {remain_time} дней).\n'

        await callback.message.delete()
        await callback.message.answer(
            f'Сейчас книгу читает другой пользователь {remain_text}'
            f'Попробуй позднее повторить поиск.',
            reply_markup=keyboard
        )
        return

    elif book.status_id == 2:
        await callback.message.delete()
        await callback.message.answer(
            f'Сейчас книгу забронировал другой пользователь. '
            f'Попробуй позднее повторить поиск.',
            reply_markup=keyboard
        )
        return

    username = callback.from_user.username
    url = (
        f'@{username}' if username is not None
        else f'<a href="tg://user?id={callback.from_user.id}">Пользователь</a>'
    )

    await callback.message.delete()
    await callback.message.answer(
        'Я отправил твой запрос владельцу книги. Он сможет связаться с '
        'тобой, чтобы вы договорились о передаче книги.'
    )

    book = await select_book(book_id)
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(
            f'Забронировать',
            callback_data=f'status-booked_{book.id}_{callback.from_user.id}',
        )
    )

    title, author, genre = await get_book_data(book)
    await callback.bot.send_message(
        chat_id=book.telegram_id,
        text='Привет!\n'
             f'{url} хочет взять у тебя книгу:\n'
             f'Книга: "{title}"\n'
             f'Автор(ы): {author}\n'
             f'Статус: {book.status}\n'
             f'Город: {book.city}\n'
             'Ты можешь написать ему, чтобы обсудить детали '
             'передачи книги. Не забудь потом сообщить мне, '
             'что ты отдал эту книгу.',
        reply_markup=keyboard,
        parse_mode='HTML'
    )
    await state.finish()


async def change_status_booked(callback: CallbackQuery):
    callback_data = callback.data.split('_')
    book_id = int(callback_data[1])
    book = await select_book(book_id)
    title, author, genre = await get_book_data(book)

    if book.status == 'Забронирована':
        await callback.message.answer(
            f'Книга: "{title}"\n'
            f'{declensions[0][len(author) > 1]}: {author}\n'
            f'{declensions[1][len(genre) > 1]}: {genre}\n'
            f'забронирована за другим пользователем. '
        )
        return

    user_id = int(callback_data[2])
    user = await select_user(user_id)
    url = (
        f'@{user.username}' if user.username is not None
        else f'<a href="tg://user?id={user_id}">пользователем</a>'
    )

    await update_book(book_id, 2, user_id)
    # book = await select_book(book_id)
    # title, author, genre = await get_book_data(book)

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(
            'Отменить бронь', callback_data=f'status-free_{book_id}_1'
        ),
        InlineKeyboardButton(
            'Передать книгу', callback_data=f'transfer-book_{book_id}'
        ),
    )

    await callback.message.delete()
    await callback.message.answer(
        f'Статус книги\n'
        f'Книга: {title}\n'
        f'{declensions[0][len(author) > 1]}: {author}\n'
        f'{declensions[1][len(genre) > 1]}: {genre}\n'
        f'изменён на: "Забронирована".\n\n'
        f'Не забудь связаться с {url} и договориться о передаче книги!',
        parse_mode='HTML',
        reply_markup=keyboard,
    )


async def return_keyword_results(callback: CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['by_keyword_return'] = data.get('by_keyword')
    await result_by_keyword(callback, state)


async def search_by_home_location(callback: CallbackQuery, state: FSMContext):
    await FSMFindBook.by_location.set()
    books, location_id = await select_books_by_home_location(
        callback.from_user.id
    )

    if len(books) == 0:
        await callback.message.delete()
        await callback.message.answer(
            'К сожалению, в твоем городе ничего не найдено.\n'
            'Хочешь поискать в других городах?'  # TODO доработать поиск как по ключевым словам но по городам?
            )
        return

    keyboard = InlineKeyboardMarkup()
    for book in books:
        title, author, genre = await get_book_data(book)
        keyboard.add(
            InlineKeyboardButton(
                f'"{title}", {author}, {book.status}',
                callback_data=f'detail_{book.id}'
            )
        )
    text = 'Вот что могу предложить из книг в твоём городе:'
    await callback.message.delete()
    await callback.message.answer(text, reply_markup=keyboard)
    async with state.proxy() as data:
        data['by_location'] = location_id


async def detail_by_location(callback: CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split('_')[1])
    data = await state.get_data()
    by_location = data.get('by_location')
    book = await select_book(book_id)
    title, author, genre = await get_book_data(book)
    location_keyboard = InlineKeyboardMarkup()
    location_keyboard.add(
        InlineKeyboardButton(
            'Хочу взять', callback_data=f'want_{book.id}'
        ),
        InlineKeyboardButton(
            'Вернуться к списку книг', callback_data=f'searchloc_{by_location}'
        )
    )
    await callback.message.delete()
    await callback.message.answer(
        f'Книга: {title}\n'
        f'{declensions[0][len(author) > 1]}: {author}\n'
        f'{declensions[1][len(genre) > 1]}: {genre}\n'
        f'Статус: {book.status}\n'
        f'Город: {book.city}',
        reply_markup=location_keyboard,
    )


async def return_location_result(callback: CallbackQuery, state: FSMContext):
    await search_by_home_location(callback, state)


def register_findbook(dispatcher: Dispatcher):
    dispatcher.register_message_handler(
        cmd_findbook, commands='findbook', state='*'
    )
    dispatcher.register_callback_query_handler(
        return_keyword_results,
        Text(startswith='return_'),
        state=FSMFindBook.by_keyword_return
        # отдельно обработать возврат списка книг по локации, можно в этом же хэндлере
    )
    dispatcher.register_callback_query_handler(
        search_by_keyword,
        lambda callback: callback.data == 'search-keyword',
        Text(equals='search-keyword')
    )
    dispatcher.register_callback_query_handler(
        search_by_home_location,
        lambda callback: callback.data == 'search-location',
        Text(equals='search-location')
    )
    dispatcher.register_callback_query_handler(
        return_location_result,
        Text(startswith='searchloc_'),
        state=FSMFindBook.by_location
    )
    dispatcher.register_message_handler(
        result_by_keyword,
        state=FSMFindBook.by_keyword,
    )
    dispatcher.register_callback_query_handler(
        detail_by_keyword,
        Text(startswith='search_'),
        state=FSMFindBook.by_keyword_detail
    )
    dispatcher.register_callback_query_handler(
        detail_by_location,
        Text(startswith='detail_'),
        state=FSMFindBook.by_location
    )

    dispatcher.register_callback_query_handler(
        want_take,
        Text(startswith='want_'),
        state='*'
    )
    dispatcher.register_callback_query_handler(
        change_status_booked,
        Text(startswith='status-booked_'),
    )
