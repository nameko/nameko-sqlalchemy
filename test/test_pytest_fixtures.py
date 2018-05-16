import pytest

from nameko.testing.services import dummy, worker_factory
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

from nameko_sqlalchemy import Database


pytest_plugins = "pytester"


class Base(object):
    pass


DeclarativeBase = declarative_base(cls=Base)


class User(DeclarativeBase):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))


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


class TestDbEngineOptions(object):

    def test_default_db_engine_options(self, db_engine_options):
        assert db_engine_options == {}

    def test_create_engine_with_default_options(self, testdir, db_session):
        testdir.makepyfile(
            """
            import pytest
            from mock import Mock, patch

            @pytest.yield_fixture
            def create_engine_mock():
                with patch(
                    'nameko_sqlalchemy.pytest_fixtures.create_engine'
                ) as m:
                    yield m

            @pytest.fixture(scope='session')
            def model_base():
                return Mock()

            def test_create_engine_with_default_options(
                create_engine_mock, db_connection
            ):
                kwargs = create_engine_mock.call_args_list[0][1]
                assert kwargs == {}
            """
        )
        result = testdir.runpytest()
        assert result.ret == 0

    def test_create_engine_with_provided_options(self, testdir, db_session):
        testdir.makepyfile(
            """
            import pytest
            from mock import Mock, patch

            @pytest.yield_fixture
            def create_engine_mock():
                with patch(
                    'nameko_sqlalchemy.pytest_fixtures.create_engine'
                ) as m:
                    yield m

            @pytest.fixture(scope='session')
            def model_base():
                return Mock()

            @pytest.fixture(scope='session')
            def db_engine_options():
                return dict(client_encoding='utf8')

            def test_create_engine_with_provided_options(
                create_engine_mock, db_connection
            ):
                kwargs = create_engine_mock.call_args_list[0][1]
                assert kwargs == dict(client_encoding='utf8')
            """
        )
        result = testdir.runpytest()
        assert result.ret == 0


class TestGetSession:

    class ExampleService(object):
        name = 'exampleservice'

        db = Database(DeclarativeBase)

        @dummy
        def write(self, id_, name):
            obj = User(id=id_, name=name)
            session = self.db.get_session()
            session.add(obj)
            session.commit()
            session.close()

        @dummy
        def read(self, id_):
            session = self.db.get_session()
            name = session.query(User).get(id_).name
            session.close()
            return name

    def test_database_fixture(self, database):

        service = worker_factory(self.ExampleService, db=database)

        service.write(11, 'ham')
        assert service.read(11) == 'ham'


class TestGetSessionContextManager:

    class ExampleService(object):
        name = 'exampleservice'

        db = Database(DeclarativeBase)

        @dummy
        def write(self, id_, name):
            with self.db.get_session() as session:
                obj = User(id=id_, name=name)
                session.add(obj)

        @dummy
        def read(self, id_):
            with self.db.get_session() as session:
                return session.query(User).get(id_).name

    def test_database_fixture(self, database):

        service = worker_factory(self.ExampleService, db=database)

        service.write(11, 'ham')
        assert service.read(11) == 'ham'


class TestWorkerScopeSession:

    class ExampleService(object):
        name = 'exampleservice'

        db = Database(DeclarativeBase)

        @dummy
        def write(self, id_, name):
            obj = User(id=id_, name=name)
            self.db.session.add(obj)
            self.db.session.commit()

        @dummy
        def read(self, id_):
            return self.db.session.query(User).get(id_).name

    def test_database_fixture(self, database):

        service = worker_factory(self.ExampleService, db=database)

        service.write(11, 'ham')
        assert service.read(11) == 'ham'


class TestWorkerScopeSessionInContext:

    class ExampleService(object):
        name = 'exampleservice'

        db = Database(DeclarativeBase)

        @dummy
        def write(self, id_, name):
            with self.db.session as session:
                obj = User(id=id_, name=name)
                session.add(obj)

        @dummy
        def read(self, id_):
            with self.db.session as session:
                return session.query(User).get(id_).name

    def test_database_fixture(self, database):

        service = worker_factory(self.ExampleService, db=database)

        service.write(11, 'ham')
        assert service.read(11) == 'ham'
