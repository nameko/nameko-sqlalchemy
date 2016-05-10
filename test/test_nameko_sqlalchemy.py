from weakref import WeakKeyDictionary

import pytest
from mock import Mock
from nameko.containers import ServiceContainer, WorkerContext
from nameko.testing.services import dummy, entrypoint_hook
from nameko_sqlalchemy import DB_URIS_KEY, DatabaseSession
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.session import Session

DeclBase = declarative_base(name='examplebase')


class ExampleModel(DeclBase):
    __tablename__ = 'example'
    id = Column(Integer, primary_key=True)
    data = Column(String)


class ExampleService(object):
    name = "exampleservice"

    session = DatabaseSession(DeclBase)

    @dummy
    def write(self, value):
        obj = ExampleModel(data=value)
        self.session.add(obj)
        self.session.commit()
        return obj.id

    @dummy
    def read(self, id):
        return self.session.query(ExampleModel).get(id).data


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
        spec=ServiceContainer, config=config, service_name="exampleservice"
    )


@pytest.fixture
def db_session(container):
    return DatabaseSession(DeclBase).bind(container, "session")


def test_setup(db_session):
    db_session.setup()

    assert db_session.db_uri == "sqlite:///:memory:"
    assert isinstance(db_session.engine, Engine)


def test_stop(db_session):
    db_session.setup()
    assert db_session.engine

    db_session.stop()
    assert not hasattr(db_session, 'engine')


def test_get_dependency(db_session):
    db_session.setup()

    worker_ctx = Mock(spec=WorkerContext)
    session = db_session.get_dependency(worker_ctx)
    assert isinstance(session, Session)
    assert db_session.sessions[worker_ctx] is session


def test_multiple_workers(db_session):
    db_session.setup()

    worker_ctx_1 = Mock(spec=WorkerContext)
    session_1 = db_session.get_dependency(worker_ctx_1)
    assert isinstance(session_1, Session)
    assert db_session.sessions[worker_ctx_1] is session_1

    worker_ctx_2 = Mock(spec=WorkerContext)
    session_2 = db_session.get_dependency(worker_ctx_2)
    assert isinstance(session_2, Session)
    assert db_session.sessions[worker_ctx_2] is session_2

    assert db_session.sessions == WeakKeyDictionary({
        worker_ctx_1: session_1,
        worker_ctx_2: session_2
    })


def test_weakref(db_session):
    db_session.setup()

    worker_ctx = Mock(spec=WorkerContext)
    session = db_session.get_dependency(worker_ctx)
    assert isinstance(session, Session)
    assert db_session.sessions[worker_ctx] is session

    del worker_ctx
    assert db_session.sessions == WeakKeyDictionary({})


def test_worker_teardown(db_session):
    db_session.setup()

    worker_ctx = Mock(spec=WorkerContext)
    session = db_session.get_dependency(worker_ctx)
    assert isinstance(session, Session)
    assert db_session.sessions[worker_ctx] is session

    session.add(ExampleModel())
    assert session.new
    db_session.worker_teardown(worker_ctx)
    assert worker_ctx not in db_session.sessions
    assert not session.new  # session.close() rolls back new objects


def test_end_to_end(container_factory, tmpdir):

    # create a temporary database
    db_uri = 'sqlite:///{}'.format(tmpdir.join("db").strpath)
    engine = create_engine(db_uri)
    ExampleModel.metadata.create_all(engine)

    config = {
        DB_URIS_KEY: {
            'exampleservice:examplebase': db_uri
        }
    }

    container = container_factory(ExampleService, config)
    container.start()

    # write through the service
    with entrypoint_hook(container, "write") as write:
        pk = write("foobar")

    # verify changes written to disk
    entries = list(engine.execute('SELECT data FROM example LIMIT 1'))
    assert entries == [('foobar',)]

    # read through the service
    with entrypoint_hook(container, "read") as read:
        assert read(pk) == "foobar"
