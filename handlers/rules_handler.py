from aiogram import types
from aiogram.dispatcher import FSMContext


async def cmd_rules(message: types.Message, state: FSMContext):
    await state.reset_state()
    await message.answer('0. Робот не может причинить вред человечеству или '
                         'своим бездействием допустить, чтобы человечеству '
                         'был причинён вред.\n'
                         '1. Робот не может причинить вред человеку или своим '
                         'бездействием допустить, чтобы человеку был причинён '
                         'вред.\n2. Робот должен повиноваться всем приказам, '
                         'которые даёт человек, кроме тех случаев, когда эти '
                         'приказы противоречат Первому Закону.\n3. Робот '
                         'должен заботиться о своей безопасности в той мере, '
                         'в которой это не противоречит Первому или Второму '
                         'Законам.')


def register_rules(dp):
    dp.register_message_handler(cmd_rules, commands='rules', state='*')
