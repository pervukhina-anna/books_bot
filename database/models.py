from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, ForeignKey,
    Integer, String, Table, Text,
)
from sqlalchemy import func

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


Base = declarative_base()


class DictStatus(Base):
    __tablename__ = 'dict_statuses'

    id = Column(Integer, primary_key=True)
    status = Column(String, unique=True)


class DictAction(Base):
    __tablename__ = 'dict_actions'

    id = Column(Integer, primary_key=True)
    action = Column(String, unique=True)


class Location(Base):
    __tablename__ = 'locations'

    id = Column(Integer, primary_key=True)
    country = Column(String, nullable=True)
    region = Column(String, nullable=True)
    city = Column(String)


book_author = Table(
    'book_author',
    Base.metadata,
    Column('book_id', Integer, ForeignKey('books_data.id'), primary_key=True),
    Column('author_id', Integer, ForeignKey('authors.id'), primary_key=True)
)

book_genre = Table(
    'book_genre',
    Base.metadata,
    Column('book_id', Integer, ForeignKey('books_data.id'), primary_key=True),
    Column('genre_id', Integer, ForeignKey('genres.id'), primary_key=True)
)


class Author(Base):
    __tablename__ = 'authors'

    id = Column(Integer, primary_key=True)
    author = Column(String, unique=True, nullable=True)

    books = relationship(
        'BookData',
        secondary=book_author,
        back_populates='authors',
        overlaps='authors'
    )


class Genre(Base):
    __tablename__ = 'genres'

    id = Column(Integer, primary_key=True)
    genre = Column(String, unique=True)

    books = relationship(
        'BookData',
        secondary=book_genre,
        back_populates='genres',
        overlaps='genres'
    )


class BookData(Base):
    __tablename__ = 'books_data'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    description = Column(Text, nullable=True)
    age_limit = Column(String, nullable=True)
    year = Column(String, nullable=True)  # год издания конкретного экземпляра? тогда логичнее к таблице экземпляра

    authors = relationship('Author', secondary=book_author)
    genres = relationship('Genre', secondary=book_genre)


class User(Base):
    __tablename__ = 'users'

    telegram_id = Column(BigInteger, primary_key=True)
    first_name = Column(String(32))
    last_name = Column(String(32), nullable=True)
    username = Column(String(32), nullable=True)
    reading_amount = Column(Integer, nullable=True, default=0)
    location_id = Column(Integer, ForeignKey('locations.id'), nullable=True)

    location = relationship('Location')


class Book(Base):
    __tablename__ = 'books'

    id = Column(Integer, primary_key=True)
    book_id = Column(Integer, ForeignKey('books_data.id'))
    telegram_id = Column(BigInteger, ForeignKey('users.telegram_id'))
    status_id = Column(Integer, ForeignKey('dict_statuses.id'), default=1)
    location_id = Column(Integer, ForeignKey('locations.id'))
    image = Column(String, nullable=True)
    condition = Column(String, nullable=True)
    pub_date = Column(DateTime, server_default=func.now())
    remain_time = Column(DateTime, server_default=None)
    candidate_telegram_id = Column(
        BigInteger, nullable=True, default=None
    )
    is_transferred = Column(Boolean, default=False)
    # year = Column(String, nullable=True)  # год издания конкретного экземпляра?

    location = relationship('Location')
    user = relationship('User')
    status = relationship('DictStatus')
    book = relationship('BookData')
    # location = relationship('Location')


class Action(Base):
    __tablename__ = 'actions'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, ForeignKey('users.telegram_id'))
    book_id = Column(Integer, ForeignKey('books.id'))
    action_id = Column(Integer, ForeignKey('dict_actions.id'))
    ctime = Column(DateTime, server_default=func.now())

    user = relationship('User')
    book = relationship('Book')
    action = relationship('DictAction')


class UserMessage(Base):
    __tablename__ = 'user_messages'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, ForeignKey('users.telegram_id'))
    msg_dt = Column(DateTime, server_default=func.now())
    msg_text = Column(String)

    user = relationship('User')


# class ProcessLog(Base):
#     __tablename__ = 'process_log'
#
#     id = Column(Integer, primary_key=True, index=True)
#     message_id = Column(Integer, ForeignKey('fct_messages.id'))
#     ctime = Column(DateTime, default=datetime.now)
#     proc_status = Column(Integer, ForeignKey('dict_statuses.unid'))
#
#     message = relationship('FctMessage', back_populates='process_log')
