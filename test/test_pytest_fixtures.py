import pytest

from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

pytest_plugins = "pytester"


class Base(object):
    pass


DeclarativeBase = declarative_base(cls=Base)


class User(DeclarativeBase):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)


@pytest.fixture(scope='session')
def model_base():
    return DeclarativeBase


def test_can_save_model(db_session):
    user = User(id=1, name='Joe')
    db_session.add(user)
    db_session.commit()
    saved_user = db_session.query(User).get(user.id)
    assert saved_user.id > 0
    assert saved_user.name == 'Joe'


def test_db_is_empty(db_session):
    assert not db_session.query(User).all()


def test_requires_override_model_base(testdir):

    testdir.makepyfile(
        """
        def test_model_base(model_base):
            pass
        """
    )
    result = testdir.runpytest()
    assert result.ret == 1
    result.stdout.fnmatch_lines(
        ["*NotImplementedError*"]
    )
