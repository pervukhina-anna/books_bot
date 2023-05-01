# bookshare

## Описание
...

## Технологии:
Python, Aiogram, Postgres, SQLAlchemy

<details>
<summary><h2>Как запустить проект локально:</h2></summary>

### *Клонируйте репозиторий:*
```
git clone git@github.com:pakalnis/bookshare.git
```

### *Установите и активируйте виртуальное окружение:*
Win:
```
python -m venv venv
venv/Scripts/activate
```

Mac:
```
python3 -m venv venv
source venv/bin/activate
```

### *Установите зависимости из файла requirements.txt:*
```
pip install -r requirements.txt
```

### *В папке `config_data` создайте файл `.env` и укажите значения согласно файлу `env_example`:*
```
BOT_TOKEN=123456789:abcdefghijklmnopqrstuvwxyz - токен телеграм-бота
DB_USER=user - юзернейм базы данных
DB_PORT=port (example - 5432) - порт базы данных, обычно 5432 для postgres
DB_HOST=localhost - хост базы данных
DB_PASSWORD=password - пароль для доступа к базе данных
DB_NAME=mydatabase - имя базы данных
```

### *В папке `database/csv_data/` запустите скрипт `import_data.py` для загрузки данных в базу:*
Из корневой директории проекта:
```
python database/csv_data/import_data.py
```
Либо перейдя в директорию со скриптом:
```
cd database/csv_data/
python import_data.py
```
### *Запустите бота:*
```
python main.py
```
</details>

## Разработчики:
owner

[Дмитрий](https://github.com/pakalnis)

developers

[Первухина Анна](https://github.com/pervukhina-anna)

[Гузелик Виктор](https://github.com/Guzelik-Victor)
