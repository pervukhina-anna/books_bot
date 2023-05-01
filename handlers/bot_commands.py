from aiogram import types


async def set_default_commands(dp):
    await dp.bot.set_my_commands(
        [
            types.BotCommand('start', 'Запустить бота'),
            types.BotCommand('addbook', 'Добавить книгу'),
            types.BotCommand('findbook', 'Найти книгу'),
            types.BotCommand('rules', 'Правила использования'),
            types.BotCommand('mybooks', 'Список моих книг'),
            types.BotCommand('profile', 'Информация и настройки профиля')
            # types.BotCommand('')
        ]
    )
