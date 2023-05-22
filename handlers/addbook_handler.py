from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message
)
from magic_filter import F
from sqlalchemy import select

from database.database import async_sessionmaker
from database.db_requests import (
    get_book_data,
    insert_existing_book_instance,
    insert_new_book_instance,
    select_author_by_keyword,
    select_books_by_title,
    select_bookdata_by_id,
    select_user
)
from database.models import Genre
from handlers.findbook_handler import cmd_findbook
from handlers.lexicon import comma, declensions, genres_keyboard
from handlers.mybooks_handler import cmd_mybooks
from handlers.rules_handler import cmd_rules
from handlers.start_handler import FSMLocation, cmd_start


# todo fsm into separate file?
# todo do we need commands list in fsm?
# todo keyboards into separate file?

class FSMAddBook(StatesGroup):
    book = State()
    author = State()
    genre_id = State()
    genre = State()
    commands = {
        '/start': cmd_start,
        '/findbook': cmd_findbook,
        '/rules': cmd_rules,
        '/mybooks': cmd_mybooks,
        '/profile': cmd_mybooks,  # временно!
    }


async def genre_keyboard_without_db(genres_list): # todo chose best way to get genre inline keyboard
    buttons = []
    keyboard = InlineKeyboardMarkup(row_width=3)
    for index, genre in enumerate(genres_list):
        buttons.append(InlineKeyboardButton(
            genre, callback_data=f'{genre}_{index+1}'
        )
        )
    keyboard.add(*buttons)
    keyboard.add(InlineKeyboardButton('Подтвердить', callback_data='accept'))
    return keyboard


async def genre_keyboard():  # TODO возравщить только жанры
    async with async_sessionmaker() as session:
        genres = await session.execute(select(Genre))
        genres = genres.scalars().all()
    keyboard = InlineKeyboardMarkup(row_width=3)
    buttons = []
    for genre in genres:
        buttons.append(InlineKeyboardButton(
            genre.genre, callback_data=f'{genre.genre}_{genre.id}'
        )
        )
    keyboard.add(*buttons)
    keyboard.add(InlineKeyboardButton('Подтвердить', callback_data='accept'))
    return keyboard


async def cmd_addbook(msg: Message, state: FSMContext):
    await state.reset_state()
    user = await select_user(msg.from_user.id)

    if user.location_id is None:
        await msg.answer(
            f'Привет, {user.first_name}!\nЕсли ты хочешь добавить книгу, '  # todo do we need greetings here?
            f'я должен знать город, в котором ты проживаешь. Это нужно мне, '
            'чтобы пользователи могли находить для себя книги из '
            'своих городов.'
        )
        return await FSMLocation.user_location.set()

    await msg.answer(
        'Хочешь поделиться книгой?\n'
        'Тогда мне нужно кое-что о ней узнать. Как она называется?'
    )
    await FSMAddBook.book.set()


async def get_book(msg: Message, state: FSMContext):
    book_title = msg.text.replace('"', '').replace("'", '')
    books = await select_books_by_title(book_title)

    if not books:
        async with state.proxy() as data:
            data['book'] = book_title
        await msg.answer(
            'А кто автор? Введи его имя полностью в формате '
            'Имя Отчество Фамилия.\n'
            'Если авторов несколько, введи имена полностью, '
            'разделив их запятой.'
        )
        return await FSMAddBook.author.set()

    keyboard = InlineKeyboardMarkup()
    for book in books:
        author = (', '.join(a.title() for a in set(book.authors)
                            if a is not None))
        genre = ', '.join(g for g in set(book.genres) if g is not None)
        button = InlineKeyboardButton(
            f'"{book.title}", {author}, {genre}',
            callback_data=f'add-instance_{book.id}',
        )
        keyboard.add(button)
    keyboard.add(InlineKeyboardButton(
        'Продолжить ввод', callback_data=f'continue_{book_title}'
    )
    )
    await msg.answer(
        'Выбери книгу из списка. Если подходящей нет, нажми "Продолжить ввод"',
        reply_markup=keyboard
    )
    await FSMAddBook.book.set()


async def save_existing_book(callback: CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split('_')[1])
    book = await select_bookdata_by_id(book_id)
    await insert_existing_book_instance(book_id, callback.from_user.id)
    await callback.message.delete()
    title, author, genre = await get_book_data(book)

    await callback.message.answer(
        f'Отлично!\n'
        f'Книга: "{title}"\n'
        f'{declensions[0][len(author) > 1]}: {author}\n'
        f'{declensions[1][len(genre) > 1]}: {genre}\n'
        f'добавлена в список твоих книг, ты можешь посмотреть '
        f'это в разделе /mybooks.\n'
        f'Когда кто-то захочет её взять, я сразу сообщу тебе '
        f'и дам возможность связаться с этим человеком.\n\n'
        f'Если хочешь добавить ещё одну книгу, используй команду /addbook.'
    )
    await state.finish()


async def continue_input(callback: CallbackQuery, state: FSMContext):
    book_title = callback.data.split('_')[1]
    async with state.proxy() as data:
        data['book'] = book_title
    await callback.message.answer(
        'А кто автор? Введи его имя полностью в формате '
        'Имя Отчество Фамилия.\n'
        'Если авторов несколько, введи имена полностью, разделив их запятой.'
    )
    await FSMAddBook.author.set()


async def get_author(msg: Message, state: FSMContext):
    async with state.proxy() as data:
        if comma not in msg.text:
            data['authors'] = msg.text
        data['authors'] = msg.text.strip().split(',')
    keyboard = await genre_keyboard_without_db(genres_keyboard)
    await msg.answer(
        'Выберите жанр произведения и нажмите "Подтвердить":',
        reply_markup=keyboard
    )
    await FSMAddBook.genre_id.set()


async def get_genres(callback: CallbackQuery, state: FSMContext):
    # TODO принимать только ввод и инлайн клавы, сделать доп хэндлер для обработки исключений
    data = await state.get_data()
    if callback.data != 'accept':
        genre, genre_id = callback.data.split('_')
        genres = data.get('genres')
        keyboard = callback.message.reply_markup
        async with state.proxy() as data_update:
            if genres is None or genre not in genres:
                data_update.setdefault('genres_id', []).append(int(genre_id))
                data_update.setdefault('genres', []).append(genre)
                chosen = False
                for row in keyboard.inline_keyboard:
                    for button in row:
                        if button.text == genre:
                            button.text = f'✅{genre}'
                            chosen = True
                    if chosen:
                        break
            else:
                data_update['genres'].remove(genre)
                data_update['genres_id'].remove(int(genre_id))
                chosen = False
                for row in keyboard.inline_keyboard:
                    for button in row:
                        if button.text == f'✅{genre}':
                            button.text = f'{genre}'
                            chosen = True
                        if chosen:
                            break
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await FSMAddBook.genre_id.set()


async def author_exists(author_list):
    for author in author_list:
        if select_author_by_keyword(author) is not None:
            return author.id, author.author


async def save_new_book(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await insert_new_book_instance(callback.from_user.id, data)
    title, author, genre = await get_book_data(data)
    # if not genre:
    #     genre = 'Другое'

    await callback.message.answer(
        f'Отлично!\n'
        f'Книга: "{title}"\n'
        f'{declensions[0][len(author) > 1]}: {author}\n'
        f'{declensions[1][len(genre) > 1]}: {genre}\n'
        f'добавлена в список твоих книг, ты можешь посмотреть '
        f'это в разделе /mybooks.\n'
        f'Когда кто-то захочет её взять, я сразу сообщу тебе '
        f'и дам возможность связаться с этим человеком.\n\n'
        f'Если хочешь добавить ещё одну книгу, используй команду /addbook.',
    )
    await callback.message.delete()
    await state.finish()


# async def cancel(msg: Message, state: FSMContext):
#     current_state = await state.get_state()
#     if current_state is None:
#         return
#
#     await msg.reply('❌ Ввод отменен.')
#     await state.finish()
#
#
# async def invalid(msg: Message, state: FSMContext):
#     current_state = await state.get_state()
#     if current_state is None:
#         return
#     await msg.reply(
#         f'❌ Отмена ввода, некорректные данные, выполняю команду {msg.text}'
#     )
#     await state.finish()
#     await FSMAddBook.commands[msg.text](msg)


def register_addbook(dispatcher: Dispatcher):
    FSMAddBook.commands.update({'/addbook': cmd_addbook})
    dispatcher.register_message_handler(
        cmd_addbook,
        commands='addbook',
        state='*'
    )
    # dp.register_message_handler(
    #     cmd_addbook, Text(equals='Добавить книгу', ignore_case=True)
    # )
    # dispatcher.register_message_handler(
    #     cancel,
    #     commands='cancel',
    #     state=FSMAddBook.states
    # )
    # dp.register_message_handler(
    #     cancel, Text(equals='Отмена', ignore_case=True),
    #     state=FSMAddBook.states
    # )
    # dispatcher.register_message_handler(
    #     invalid,
    #     F.text.in_(FSMAddBook.commands.keys()),
    #     state=FSMAddBook.states,
    # )
    dispatcher.register_callback_query_handler(
        save_existing_book,
        Text(startswith='add-instance_'),
        state=FSMAddBook.book,
    )
    dispatcher.register_callback_query_handler(
        continue_input,
        Text(startswith='continue_'),
        state=FSMAddBook.book,
    )
    dispatcher.register_message_handler(
        get_book, state=FSMAddBook.book
    )
    dispatcher.register_message_handler(
        get_author,
        state=FSMAddBook.author
    )
    dispatcher.register_callback_query_handler(
        save_new_book,
        Text(equals='accept'),
        state=FSMAddBook.genre_id,
    )
    dispatcher.register_callback_query_handler(
        get_genres,
        state=FSMAddBook.genre_id,
    )
