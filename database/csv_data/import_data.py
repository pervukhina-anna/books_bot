import asyncio
import csv

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import engine
from database.models import DictStatus, DictAction, Location, Genre


async def import_statuses():
    async with engine.begin() as conn:
        result = await conn.execute(
            select(func.count()).select_from(DictStatus)
        )
        count = result.scalar()
        if not count == 0:
            return 'В таблице dict_statuses уже есть данные!'
        await conn.run_sync(DictStatus.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            with open('status.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = [
                    DictStatus(id=int(row['id']), status=row['status'])
                    for row in reader
                ]
                session.add_all(rows)
                await session.commit()
                return 'Данные добавлены в таблицу dict_statuses!'


async def import_actions():
    async with engine.begin() as conn:
        result = await conn.execute(
            select(func.count()).select_from(DictAction)
        )
        count = result.scalar()
        if not count == 0:
            return 'В таблице dict_actions уже есть данные!'
        await conn.run_sync(DictAction.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            with open('action.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = [
                    DictAction(id=int(row['id']), action=row['action'])
                    for row in reader
                ]
                session.add_all(rows)
                await session.commit()
                return 'Данные добавлены в таблицу dict_actions!'


async def import_locations():
    async with engine.begin() as conn:
        result = await conn.execute(
            select(func.count()).select_from(Location)
        )
        count = result.scalar()
        if not count == 0:
            return 'В таблице locations уже есть данные!'
        await conn.run_sync(Location.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            with open('location.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = [
                    Location(
                        id=id + 1,
                        # country=row['country'],
                        region=row['region'],
                        city=row['city'],
                    )
                    for id, row in enumerate(reader)
                ]
                session.add_all(rows)
                await session.commit()
                return 'Данные добавлены в таблицу locations!'


async def import_genres():
    async with engine.begin() as conn:
        result = await conn.execute(
            select(func.count()).select_from(Genre)
        )
        count = result.scalar()
        if not count == 0:
            return 'В таблице genres уже есть данные!'
        await conn.run_sync(Genre.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            with open('genre.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = [
                    Genre(id=int(row['id']), genre=row['genre'])
                    for row in reader
                ]
                session.add_all(rows)
                await session.commit()
                return 'Данные добавлены в таблицу genres!'


async def main():
    statuses = await import_statuses()
    actions = await import_actions()
    locations = await import_locations()
    genres = await import_genres()
    print(statuses, actions, locations, genres, sep='\n')


asyncio.run(main())
