from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message

# from handlers.addbook_handler import cmd_addbook
# from handlers.findbook_handler import cmd_findbook
# from handlers.mybooks_handler import my_books
# from handlers.rules_handler import cmd_rules
# from handlers.start_handler import cmd_start


async def reset_state(msg: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None and msg.text.startswith('/'):
        await state.reset_state()
        await state.finish()



#
# async def process_command(message: Message):
#     if message.text == '/start':
#         await cmd_start(message)
#     if message.text == '/findbook':
#         await cmd_findbook(message)
#     if message.text == '/addbook':
#         await cmd_addbook(message)
#     if message.text == '/mybooks':
#         await my_books(message)
#     if message.text == '/rules':
#         await cmd_rules(message)

#
# def register_cancel(dispatcher: Dispatcher):
#     dispatcher.register_message_handler(process_cancel_command_state, state='*')