import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def pytest_addoption(parser):
    parser.addoption(
        '--test-db-url',
        action='store',
        dest='TEST_DB_URL',
        default='sqlite://',
        help=(
            'DB url for testing (e.g. '
            '"postgresql://username:password@localhost/test")'
        )
    )
    parser.addoption(
        '--toxiproxy-api-url',
        action='store',
        dest='TOXIPROXY_API_URL',
        help=(
            'Toxiproxy HTTP API address for simulating network errors '
            '(e.g. "127.0.0.1:8474")'
        )
    )
    parser.addoption(
        '--toxiproxy-db-url',
        action='store',
        dest='TOXIPROXY_DB_URL',
        help=(
            'Toxiproxy database url (e.g. "127.0.0.1:3306")'
        )
    )


@pytest.fixture(scope='session')
def db_url(request):
    """ Database URL used in sqlalchemy.create_engine

    Use ``--test-db-url`` pytest parameter or override this fixture
    in your test to provide your desired test database url.
    For valid urls see: http://docs.sqlalchemy.org/en/latest/core/engines.html
    Defaults to SQLite memory database.

    .. warning::

        Ensure you are providing test database url since
        data will be deleted for each test function
        and schema will be recreated on each test run.
    """
    return request.config.getoption('TEST_DB_URL')


@pytest.fixture(scope='session')
def toxiproxy_api_url(request):
    """ The url to use to connect to Toxiproxy API.

    """
    return request.config.getoption('TOXIPROXY_API_URL')


@pytest.fixture(scope='session')
def toxiproxy_db_url(request):
    """ The url to use to connect to the database through Toxiproxy.

    """
    return request.config.getoption('TOXIPROXY_DB_URL')


@pytest.fixture(scope='session')
def db_engine_options():
    """Additional keyword arguments used in sqlalchemy.create_engine.

    http://docs.sqlalchemy.org/en/latest/core/engines.html

    Override this fixture to return a dictionary containing the keyword
    arguments to be passed to sqlalchemy.create_engine.

    .. code-block:: python

        @pytest.fixture(scope='session')
        def db_engine_options():
            return dict(client_encoding='utf8')
    """
    return {}


@pytest.fixture(scope='session')
def model_base():
    """Override this fixture to return declarative base of your model

    http://docs.sqlalchemy.org/en/latest/orm/extensions/declarative/api.html

    .. code-block:: python

        from sqlalchemy.ext.declarative import declarative_base

        class Base(object):
            pass

        DeclarativeBase = declarative_base(cls=Base)

        class User(DeclarativeBase):
            __tablename__ = "users"

            id = Column(Integer, primary_key=True)

        @pytest.fixture(scope='session')
        def model_base():
            return DeclarativeBase
    """
    raise NotImplementedError("Fixture `model_base` has to be overwritten")


@pytest.yield_fixture(scope='session')
def db_connection(db_url, model_base, db_engine_options):
    engine = create_engine(db_url, **db_engine_options)
    model_base.metadata.create_all(engine)
    connection = engine.connect()
    model_base.metadata.bind = engine

    yield connection

    model_base.metadata.drop_all()
    engine.dispose()


@pytest.yield_fixture
def db_session(db_connection, model_base):
    session = sessionmaker(bind=db_connection)
    db_session = session()

    yield db_session

    db_session.rollback()

    for table in reversed(model_base.metadata.sorted_tables):
        db_session.execute(table.delete())

    db_session.commit()
    db_session.close()
