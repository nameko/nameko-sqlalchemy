import pytest
from mock import call, Mock, patch
from nameko.containers import ServiceContainer
from nameko.testing.services import dummy, entrypoint_hook
from nameko_sqlalchemy import DB_URIS_KEY, DatabaseSessionScope
from sqlalchemy import Column, String, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base


DeclBase = declarative_base(name='examplebase')


class ExampleModel(DeclBase):
    __tablename__ = 'example'
    key = Column(String, primary_key=True)
    value = Column(String)


class ExampleService(object):
    name = 'exampleservice'

    db_session_scope = DatabaseSessionScope(DeclBase)

    @dummy
    def write(self, key, value):
        with self.db_session_scope() as session:
            obj = ExampleModel(key=key, value=value)
            session.add(obj)

    @dummy
    def read(self, key):
        with self.db_session_scope() as session:
            return session.query(ExampleModel).get(key).value


@pytest.fixture
def config():
    return {
        DB_URIS_KEY: {
            'exampleservice:examplebase': 'sqlite:///:memory:'
        }
    }


@pytest.fixture
def container(config):
    return Mock(
        spec=ServiceContainer, config=config, service_name='exampleservice'
    )


@pytest.fixture
def dependency_provider(container):
    return DatabaseSessionScope(DeclBase).bind(container, 'db_session_scope')


def test_setup(dependency_provider):
    dependency_provider.setup()

    assert dependency_provider.db_uri == 'sqlite:///:memory:'
    assert isinstance(dependency_provider.engine, Engine)


def test_stop(dependency_provider):
    dependency_provider.setup()
    assert dependency_provider.engine

    dependency_provider.stop()
    assert not hasattr(dependency_provider, 'engine')


class TestUnit:

    @pytest.yield_fixture
    def session(self):
        with patch(
            'nameko_sqlalchemy.database_session.sessionmaker'
        ) as sessionmaker:
            Session = sessionmaker.return_value
            yield Session.return_value

    @pytest.fixture
    def db_session_scope(self, session, dependency_provider):
        dependency_provider.setup()
        return dependency_provider.get_dependency(worker_ctx={})

    def test_comits_and_closes_on_exit(self, db_session_scope, session):

        with db_session_scope() as session:
            pass

        assert session.mock_calls == [call.commit(), call.close()]

    def test_rolls_back_and_closes_on_error(self, db_session_scope, session):

        with db_session_scope() as session:
            raise Exception('Whoops!')

        assert session.mock_calls == [call.rollback(), call.close()]


class TestEndToEnd:

    @pytest.fixture
    def db_uri(self, tmpdir):
        return 'sqlite:///{}'.format(tmpdir.join("db").strpath)

    @pytest.fixture
    def container(self, container_factory, db_uri):

        engine = create_engine(db_uri)
        ExampleModel.metadata.create_all(engine)

        config = {
            DB_URIS_KEY: {
                'exampleservice:examplebase': db_uri
            }
        }

        container = container_factory(ExampleService, config)
        container.start()

        return container

    def test_successful_write_and_read(slf, container, db_uri):

        # write through the service
        with entrypoint_hook(container, 'write') as write:
            write(key='spam', value='ham')

        # verify changes written to disk
        entries = list(
            create_engine(db_uri).execute(
                'SELECT key, value FROM example LIMIT 1'))
        assert entries == [('spam', 'ham',)]

        # read through the service
        with entrypoint_hook(container, 'read') as read:
            assert read('spam') == 'ham'
