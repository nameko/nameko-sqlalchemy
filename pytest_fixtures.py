import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope='module')
def db_url():
    """ Database URL used in sqlalchemy.create_engine

    Override this in your test to provide your desired url.
    For valid urls see: http://docs.sqlalchemy.org/en/latest/core/engines.html
    Defaults to SQLite memory database.
    """
    return 'sqlite://'


@pytest.fixture(scope='module')
def base():
    error = """
    Override this fixture in your tests to return
    `sqlalchemy.ext.declarative.declarative_base` e.g.

    from sqlalchemy.ext.declarative import declarative_base

    class Base:
        pass

    Base = declarative_base(cls=Base)

    @pytest.fixture(scope='module')
    def base():
        return Base
    """
    raise NotImplementedError(error)


@pytest.yield_fixture(scope="module")
def connection(db_url, base):
    engine = create_engine(db_url)
    base.metadata.create_all(engine)
    connection = engine.connect()
    base.metadata.bind = engine
    yield connection
    base.metadata.drop_all()
    engine.dispose()


@pytest.yield_fixture
def session(connection, base):
    session = sessionmaker(bind=connection)
    db_session = session()

    yield db_session

    db_session.rollback()

    for table in reversed(base.metadata.sorted_tables):
        db_session.execute(table.delete())

    db_session.commit()
    db_session.close()
