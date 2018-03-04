from weakref import WeakKeyDictionary

import pytest
from mock import Mock, patch
from nameko.containers import ServiceContainer, WorkerContext
from nameko.testing.services import dummy, entrypoint_hook
from nameko_sqlalchemy.database import (
    DB_URIS_KEY,
    Database,
    Session,
)
from sqlalchemy import Column, String, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base


DeclBase = declarative_base(name='examplebase')


class ExampleModel(DeclBase):
    __tablename__ = 'example'
    key = Column(String, primary_key=True)
    value = Column(String)


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
    return Database(DeclBase).bind(container, 'database')


def test_setup(dependency_provider):
    dependency_provider.setup()

    assert dependency_provider.db_uri == 'sqlite:///:memory:'
    assert isinstance(dependency_provider.engine, Engine)


def test_stop(dependency_provider):
    dependency_provider.setup()
    assert dependency_provider.engine

    dependency_provider.stop()
    assert not hasattr(dependency_provider, 'engine')


def test_kill(dependency_provider):
    dependency_provider.setup()
    assert dependency_provider.engine

    dependency_provider.kill()
    assert not hasattr(dependency_provider, 'engine')


class TestWorkerScopeSessionUnit:

    def test_get_dependency(self, dependency_provider):

        dependency_provider.setup()
        worker_ctx = Mock(spec=WorkerContext)

        db = dependency_provider.get_dependency(worker_ctx)
        assert dependency_provider.dbs[worker_ctx] is db
        assert db._worker_session is None
        session = db.session
        assert isinstance(session, Session)
        assert db._worker_session is session

    def test_multiple_workers(self, dependency_provider):

        dependency_provider.setup()

        worker_ctx_1 = Mock(spec=WorkerContext)
        db_1 = dependency_provider.get_dependency(worker_ctx_1)
        assert isinstance(db_1.session, Session)
        assert dependency_provider.dbs[worker_ctx_1].session is db_1.session

        worker_ctx_2 = Mock(spec=WorkerContext)
        db_2 = dependency_provider.get_dependency(worker_ctx_2)
        assert isinstance(db_2.session, Session)
        assert dependency_provider.dbs[worker_ctx_2].session is db_2.session

        assert dependency_provider.dbs == WeakKeyDictionary({
            worker_ctx_1: db_1,
            worker_ctx_2: db_2
        })

    def test_weakref(self, dependency_provider):

        dependency_provider.setup()
        worker_ctx = Mock(spec=WorkerContext)

        db = dependency_provider.get_dependency(worker_ctx)
        assert isinstance(db.session, Session)
        assert dependency_provider.dbs[worker_ctx].session is db.session

        del worker_ctx
        assert dependency_provider.dbs == WeakKeyDictionary({})

    def test_worker_teardown(self, dependency_provider):
        dependency_provider.setup()

        worker_ctx = Mock(spec=WorkerContext)
        db = dependency_provider.get_dependency(worker_ctx)
        assert isinstance(db.session, Session)
        assert dependency_provider.dbs[worker_ctx].session is db.session

        db.session.add(ExampleModel())
        assert db.session.new
        dependency_provider.worker_teardown(worker_ctx)
        assert worker_ctx not in dependency_provider.dbs
        assert not db.session.new  # session.close() rolls back new objects


class TestGetSessionContextManagerUnit:

    @pytest.fixture
    def db(self, dependency_provider):
        dependency_provider.setup()
        worker_ctx = Mock(spec=WorkerContext)
        return dependency_provider.get_dependency(worker_ctx=worker_ctx)

    @patch.object(Session, 'rollback')
    @patch.object(Session, 'commit')
    @patch.object(Session, 'close')
    def test_comits(self, close, commit, rollback, db):

        with db.get_session() as session:
            assert isinstance(session, Session)

        assert commit.called
        assert not rollback.called
        assert not close.called

    @patch.object(Session, 'rollback')
    @patch.object(Session, 'commit')
    @patch.object(Session, 'close')
    def test_comits_and_closes(self, close, commit, rollback, db):

        with db.get_session(close_on_exit=True) as session:
            assert isinstance(session, Session)

        assert commit.called
        assert not rollback.called
        assert close.called

    @patch.object(Session, 'rollback')
    @patch.object(Session, 'commit')
    @patch.object(Session, 'close')
    def test_rolls_back(self, close, commit, rollback, db):

        with pytest.raises(Exception):
            with db.get_session():
                raise Exception('Yo!')

        assert not commit.called
        assert rollback.called
        assert not close.called

    @patch.object(Session, 'rollback')
    @patch.object(Session, 'commit')
    @patch.object(Session, 'close')
    def test_rolls_back_and_closes(self, close, commit, rollback, db):

        with pytest.raises(Exception):
            with db.get_session(close_on_exit=True):
                raise Exception('Yo!')

        assert not commit.called
        assert rollback.called
        assert close.called

    @patch.object(Session, 'rollback')
    @patch.object(Session, 'commit')
    @patch.object(Session, 'close')
    def test_rolls_back_on_commit_error(
        self, close, commit, rollback, db
    ):

        commit.side_effect = Exception('Yo!')

        with pytest.raises(Exception):
            with db.get_session():
                pass

        assert rollback.called
        assert not close.called

    @patch.object(Session, 'rollback')
    @patch.object(Session, 'commit')
    @patch.object(Session, 'close')
    def test_rolls_back_and_closes_on_commit_error(
        self, close, commit, rollback, db
    ):

        commit.side_effect = Exception('Yo!')

        with pytest.raises(Exception):
            with db.get_session(close_on_exit=True):
                pass

        assert rollback.called
        assert close.called

    @patch.object(Session, 'rollback')
    @patch.object(Session, 'commit')
    @patch.object(Session, 'close')
    def test_no_close_on_exit(
        self, close, commit, rollback, db
    ):

        with db.get_session() as session_one:
            assert isinstance(session_one, Session)

        assert commit.called
        assert not rollback.called
        assert not close.called

        with db.get_session(close_on_exit=True) as session_two:
            assert isinstance(session_two, Session)

        assert commit.call_count == 2
        assert not rollback.called
        assert close.called

        assert db._context_sessions == [session_one, session_two]

        assert close.call_count == 1
        db.close()
        assert close.call_count == 3

    def test_worker_teardown(self, dependency_provider):
        dependency_provider.setup()

        worker_ctx = Mock(spec=WorkerContext)
        db = dependency_provider.get_dependency(worker_ctx)

        with db.get_session(close_on_exit=True) as session_one:
            assert isinstance(session_one, Session)

        with db.get_session(close_on_exit=False) as session_two:
            assert isinstance(session_two, Session)

        session_one.add(ExampleModel())
        session_two.add(ExampleModel())
        assert session_one.new
        assert session_two.new
        dependency_provider.worker_teardown(worker_ctx)
        assert worker_ctx not in dependency_provider.dbs
        assert not session_one.new  # session.close() rolls back new objects
        assert not session_two.new  # session.close() rolls back new objects


class BaseTestEndToEnd:

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

        container = container_factory(self.ExampleService, config)
        container.start()

        return container


class TestGetSessionEndToEnd(BaseTestEndToEnd):

    class ExampleService(object):
        name = 'exampleservice'

        db = Database(DeclBase)

        @dummy
        def write(self, key, value):
            obj = ExampleModel(key=key, value=value)
            session = self.db.get_session()
            session.add(obj)
            session.commit()
            session.close()

        @dummy
        def read(self, key):
            session = self.db.get_session()
            value = session.query(ExampleModel).get(key).value
            session.close()
            return value

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


class TestGetSessionContextManagerEndToEnd(BaseTestEndToEnd):

    class ExampleService(object):
        name = 'exampleservice'

        db = Database(DeclBase)

        @dummy
        def write(self, key, value):
            with self.db.get_session() as session:
                obj = ExampleModel(key=key, value=value)
                session.add(obj)

        @dummy
        def read(self, key):
            with self.db.get_session() as session:
                return session.query(ExampleModel).get(key).value

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


class TestWorkerScopeSessionEndToEnd(BaseTestEndToEnd):

    class ExampleService(object):
        name = 'exampleservice'

        db = Database(DeclBase)

        @dummy
        def write(self, key, value):
            obj = ExampleModel(key=key, value=value)
            self.db.session.add(obj)
            self.db.session.commit()

        @dummy
        def read(self, key):
            return self.db.session.query(ExampleModel).get(key).value

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


class TestWorkerScopeSessionInContextEndToEnd(BaseTestEndToEnd):

    class ExampleService(object):
        name = 'exampleservice'

        db = Database(DeclBase)

        @dummy
        def write(self, key, value):
            with self.db.session as session:
                obj = ExampleModel(key=key, value=value)
                session.add(obj)

        @dummy
        def read(self, key):
            with self.db.session as session:
                return session.query(ExampleModel).get(key).value

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
