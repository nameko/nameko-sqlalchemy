import pytest

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope='session')
def db_url():
    """ Database URL used in sqlalchemy.create_engine

    Override this in your test to provide your desired test database url.
    For valid urls see: http://docs.sqlalchemy.org/en/latest/core/engines.html
    Defaults to SQLite memory database.

    .. warning::

        Ensure you are providing test database url since
        data will be deleted for each test function
        and schema will be recreated on each test run.
    """
    return 'sqlite://'


@pytest.fixture(scope='session')
def base():
    """ Returns `sqlalchemy.ext.declarative.declarative_base` used
    for declarative database definitions

    http://docs.sqlalchemy.org/en/latest/orm/extensions/declarative/api.html

    You can override this fixture to return base of your model:

    .. code-block:: python

        from sqlalchemy.ext.declarative import declarative_base

        class Base:
            pass

        class User(Base):
            id = Column(Integer, primary_key=True)

        Base = declarative_base(cls=Base)

        @pytest.fixture(scope='module')
        def base():
            return Base
    """
    return declarative_base()


@pytest.yield_fixture(scope='session')
def db_connection(db_url, base):
    engine = create_engine(db_url)
    base.metadata.create_all(engine)
    connection = engine.connect()
    base.metadata.bind = engine
    yield connection
    base.metadata.drop_all()
    engine.dispose()


@pytest.yield_fixture
def db_session(db_connection, base):
    session = sessionmaker(bind=db_connection)
    db_session = session()

    yield db_session

    db_session.rollback()

    for table in reversed(base.metadata.sorted_tables):
        db_session.execute(table.delete())

    db_session.commit()
    db_session.close()
