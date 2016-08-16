import pytest

from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base


class Base:
    pass


Base = declarative_base(cls=Base)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)


@pytest.fixture(scope='session')
def base():
    return Base


def test_fixtures(db_session):
    user = User(id=1, name='Joe')
    db_session.add(user)
    db_session.commit()
    saved_user = db_session.query(User).get(user.id)
    assert saved_user.id > 0
    assert saved_user.name == 'Joe'

