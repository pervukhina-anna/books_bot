from datetime import datetime, timedelta
from typing import Dict

from sqlalchemy import select, func, update, or_, and_
from sqlalchemy.dialects.postgresql import array_agg

from database.database import async_sessionmaker
from database.models import (
    Author,
    Book,
    BookData,
    DictStatus,
    Genre,
    Location,
    User,
    book_author,
    book_genre
)


async def select_user(user_id):
    async with async_sessionmaker() as session:
        user = await session.get(User, user_id)
    return user


async def insert_user(user_id, first_name, last_name, username):
    async with async_sessionmaker() as session:
        user = User(
            telegram_id=user_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
        )
        session.add(user)
        await session.commit()


async def select_location(user_input):
    async with async_sessionmaker() as session:
        locations = await session.execute(
            select(
                Location.id,
                Location.city,
                Location.region
            ).select_from(Location
                          ).where(Location.city.ilike(f'%{user_input}%')
                                  ).order_by(Location.city)
        )
        locations = locations.fetchall()
    return locations


async def insert_location(location_id, user_id):
    async with async_sessionmaker() as session:
        location = await session.get(Location, location_id)
        user = await session.get(User, user_id)
        user.location_id = location_id
        await session.commit()
    return location.city, location.region


async def select_books_by_title(user_input):
    async with async_sessionmaker() as session:
        books = await session.execute(select(
            BookData.id,
            BookData.title,
            array_agg(Author.author).label('authors'),
            array_agg(Genre.genre).label('genres'),
        ).select_from(BookData
                      ).outerjoin(book_author
                                  ).outerjoin(Author
                                              ).outerjoin(book_genre
                                                          ).outerjoin(Genre
        ).where(BookData.title.ilike(f'%{user_input}%')
                ).group_by(BookData.id, BookData.title)
                                      )
        return books.fetchall()


async def select_bookdata_by_id(book_id):
    async with async_sessionmaker() as session:
        book = await session.execute(select(
            Book.id,
            BookData.id.label('book_id'),
            BookData.title,
            array_agg(func.distinct(Author.author)).label('authors'),
            array_agg(func.distinct(Genre.genre)).label('genres'),
            DictStatus.status,
            Location.city,
            Book.status_id,
            Book.remain_time,
            Book.candidate_telegram_id,
            Book.is_transferred,
            Book.telegram_id,
        ).select_from(Book
                      ).join(BookData
                      ).outerjoin(DictStatus
                      ).outerjoin(Location
                      ).outerjoin(book_author
                      ).outerjoin(Author
                      ).outerjoin(book_genre
                      ).outerjoin(Genre
                                  ).where(BookData.id == book_id
                                          ).group_by(Book.id,
                                                     BookData.id,
                                                     DictStatus.id,
                                                     Location.city)
                                     )
        return book.fetchone()


async def insert_existing_book_instance(book_id, user_id):
    user = await select_user(user_id)
    async with async_sessionmaker() as session:
        session.add(
            Book(
                book_id=book_id,
                telegram_id=user.telegram_id,
                location_id=user.location_id,
            )
        )
        await session.commit()


async def select_author_by_keyword(user_input):
    async with async_sessionmaker() as session:
        author = await session.execute(
            select(Author.id, Author.author
                   ).where(Author.author == user_input)
            )
    return author.fetchone()


async def insert_new_book_instance(user_id, book_data):
    user = await select_user(user_id)
    async with async_sessionmaker() as session:
        book = BookData(title=book_data.get('book'))
        session.add(book)
        existing_authors = []
        for author in book_data['authors']:
            db_author = await select_author_by_keyword(author)
            if db_author is None:
                session.add(Author(author=author))
            existing_authors.append(author)
        await session.commit()
        for author in existing_authors:
            db_id, db_name = await select_author_by_keyword(author)
            await session.execute(
                book_author.insert().values(
                    book_id=book.id,
                    author_id=db_id,
                )
            )
        genre_ids = book_data.get('genres_id')
        if genre_ids is not None:
            for genre_id in genre_ids:
                await session.execute(
                    book_genre.insert().values(
                        book_id=book.id,
                        genre_id=genre_id,
                    )
                )
        session.add(
            Book(
                book_id=book.id,
                telegram_id=user.telegram_id,
                location_id=user.location_id,
            )
        )
        await session.commit()


async def get_book_data(book_data):
    if isinstance(book_data, Dict):
        title = book_data.get('book')
        author = ', '.join(a for a in [*book_data.get('authors')])
        genre = ', '.join(g for g in [*book_data.get('genres', '')])
    else:
        title = book_data.title
        author = ', '.join(a.title() for a in set(book_data.authors))
        genre = ', '.join(g for g in set(book_data.genres) if g is not None)
    return title, author, genre


async def select_users_books(user_id):
    async with async_sessionmaker() as session:
        book = await session.execute(select(
            Book.id,
            BookData.id.label('book_id'),
            BookData.title,
            array_agg(func.distinct(Author.author)).label('authors'),
            array_agg(func.distinct(Genre.genre)).label('genres'),
            DictStatus.status,
            Location.city,
            Book.remain_time,
        ).select_from(Book
                      ).join(BookData
                      ).outerjoin(DictStatus
                      ).outerjoin(Location
                      ).outerjoin(book_author
                      ).outerjoin(Author
                      ).outerjoin(book_genre
                      ).outerjoin(Genre
                                  ).filter(Book.telegram_id == user_id
                                           ).group_by(Book.id,
                                                      BookData.id,
                                                      DictStatus.id,
                                                      Location.city,
                                                      # Author.author,
                                                      # Genre.genre
                                                      ).order_by(DictStatus.id)
                                     )
        return book.fetchall()


async def select_book(book_id):
    async with async_sessionmaker() as session:
        book = await session.execute(select(
            Book.id,
            BookData.id.label('book_id'),
            BookData.title,
            array_agg(func.distinct(Author.author)).label('authors'),
            array_agg(func.distinct(Genre.genre)).label('genres'),
            DictStatus.status,
            Location.city,
            Book.status_id,
            Book.remain_time,
            Book.candidate_telegram_id,
            Book.is_transferred,
            Book.telegram_id
        ).select_from(Book
                      ).join(BookData
                      ).outerjoin(DictStatus
                      ).outerjoin(Location
                      ).outerjoin(book_author
                      ).outerjoin(Author
                      ).outerjoin(book_genre
                      ).outerjoin(Genre
                                  ).filter(Book.id == book_id
                                           ).group_by(Book.id,
                                                      BookData.id,
                                                      DictStatus.id,
                                                      Location.city,
                                                      # Author.author,
                                                      # Genre.genre
                                                      ).order_by(DictStatus.id)
                                     )
        return book.fetchone()


async def update_book(book_id, book_status, candidate_id=None):
    async with async_sessionmaker() as session:
        book = await select_book(book_id)
        remain_time = (datetime.now() + timedelta(days=90) if book_status == 3
                       else None)
        candidate_telegram_id = ( # TODO check if all correct with diff statuses!!!
            None if book_status == 1
            else book.candidate_telegram_id if book_status == 3
            else candidate_id
        )

        is_transferred = False if book_status == 1 else book.is_transferred
        await session.execute(
            update(Book
                   ).where(Book.id == book_id
                           ).values(
                status_id=book_status,
                remain_time=remain_time,
                candidate_telegram_id=candidate_telegram_id,
                is_transferred=is_transferred
            )
        )
        await session.commit()


async def update_book_transfer_by_candidate(book_id, candidate_id):
    async with async_sessionmaker() as session:
        remain_time = datetime.now() + timedelta(days=90)
        await session.execute(
            update(Book
                   ).where(Book.id == book_id
                           ).values(
                status_id=3,
                remain_time=remain_time,
                telegram_id=candidate_id,
                candidate_telegram_id=None,
                is_transferred=False
            )
        )
        await session.commit()


async def update_book_transfer(book_id):
    async with async_sessionmaker() as session:

        await session.execute(
            update(Book
                   ).where(Book.id == book_id
                           ).values(is_transferred=True))
        await session.commit()


async def update_remain_time(book_id):
    async with async_sessionmaker() as session:
        book = await select_book(book_id)
        remain_time = book.remain_time + timedelta(days=15)
        await session.execute(
            update(Book
                   ).where(Book.id == book_id
                           ).values(remain_time=remain_time)
        )
        await session.commit()


async def select_books_by_keyword(user_id, user_input):
    async with async_sessionmaker() as session:
        book = await session.execute(select(
            Book.id,
            BookData.id.label('book_id'),
            BookData.title,
            array_agg(func.distinct(Author.author)).label('authors'),
            array_agg(func.distinct(Genre.genre)).label('genres'),
            DictStatus.status,
            Location.city,
            Book.status_id,
            Book.remain_time,
            Book.candidate_telegram_id,
            Book.is_transferred,
        ).select_from(Book
                      ).join(BookData
                      ).outerjoin(DictStatus
                      ).outerjoin(Location
                      ).outerjoin(book_author
                      ).outerjoin(Author
                      ).outerjoin(book_genre
                      ).outerjoin(Genre
                      ).where(or_(BookData.title.ilike(f'%{user_input}%'),
                                  Author.author.ilike(f'%{user_input}%'),
                                  Genre.genre.ilike(f'%{user_input}%')),
                              and_(Book.telegram_id != user_id,
                                   # Book.location_id == location
                                   )).group_by(Book.id,
                                               BookData.id,
                                               DictStatus.id,
                                               Location.city,
                                               # Author.author,
                                               # Genre.genre
                                               ).order_by(DictStatus.id,
                                                          Location.city)
                                     )
        return book.fetchall()
