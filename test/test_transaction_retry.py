import operator
import sys

import pytest
from mock import Mock
from nameko.exceptions import ExtensionNotFound
from nameko.testing.services import entrypoint_hook
from nameko.testing.services import dummy
from sqlalchemy import create_engine
from sqlalchemy.exc import StatementError, OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from nameko_sqlalchemy import (
    Database, DatabaseSession, DB_URIS_KEY, transaction_retry
)
from test.conftest import DeclarativeBase, ExampleModel


DeclBase = declarative_base(name='examplebase')


@pytest.yield_fixture
def toxiproxy_db_session(toxiproxy_db_url):
    engine = create_engine(toxiproxy_db_url)
    Session = sessionmaker(bind=engine)
    toxiproxy_db_session = Session()

    yield toxiproxy_db_session

    toxiproxy_db_session.close()


@pytest.fixture(scope='session')
def model_base():
    return DeclarativeBase


@pytest.fixture(autouse=True)
def example_table(db_session):
    ExampleModel.metadata.create_all(db_session.get_bind().engine)


@pytest.fixture()
def disconnect(toxiproxy):
    def _disconnect(reconnect=True):
        toxiproxy.disable()
        if reconnect:
            toxiproxy.enable()

    return _disconnect


def test_reconnects_during_transaction(
    toxiproxy_db_session, toxiproxy, disconnect
):
    if not toxiproxy:
        pytest.skip('Toxiproxy not installed')

    @transaction_retry(session=toxiproxy_db_session)
    def get_model_count():
        return toxiproxy_db_session.query(ExampleModel).count()

    toxiproxy_db_session.add(ExampleModel(data='hello1'))
    toxiproxy_db_session.add(ExampleModel(data='hello2'))
    toxiproxy_db_session.commit()

    disconnect(reconnect=True)

    model_count = get_model_count()

    assert model_count == 2

    toxiproxy_db_session.close()
    assert toxiproxy_db_session.query(ExampleModel).count() == 2


def test_raises_without_using_transaction_retry(
    toxiproxy_db_session, toxiproxy, disconnect
):
    if not toxiproxy:
        pytest.skip('Toxiproxy not installed')

    def get_model_count():
        return toxiproxy_db_session.query(ExampleModel).count()

    toxiproxy_db_session.add(ExampleModel(data='hello1'))
    toxiproxy_db_session.add(ExampleModel(data='hello2'))
    toxiproxy_db_session.commit()

    disconnect(reconnect=True)

    with pytest.raises(OperationalError):
        get_model_count()


def test_raises_error_if_cannot_reconnect(
    toxiproxy_db_session, disconnect, toxiproxy
):
    if not toxiproxy:
        pytest.skip('Toxiproxy not installed')

    toxiproxy_db_session.add(ExampleModel(data='hello1'))
    toxiproxy_db_session.add(ExampleModel(data='hello2'))
    toxiproxy_db_session.commit()

    disconnect(reconnect=False)

    @transaction_retry
    def get_model_count():
        return toxiproxy_db_session.query(ExampleModel).count()

    with pytest.raises(StatementError):
        get_model_count()


def test_raises_if_connection_is_not_invalidated():

    @transaction_retry
    def raise_error():
        raise OperationalError(None, None, None, connection_invalidated=False)

    with pytest.raises(OperationalError):
        raise_error()


class TestTransactionRetryWithDependencyProviders:
    """ Testing transaction_retry decorator with both `Database``` and
        ``DatabaseSession`` dependency providers.
    """

    class ExampleServiceWithDatabase:
        name = 'exampleservice'

        db = Database(DeclBase)

        @dummy
        def create_record(self):
            with self.db.get_session() as session:
                session.add(ExampleModel(data='hello'))

        @dummy
        @transaction_retry
        def get_record_count(self):
            with self.db.get_session() as session:
                return session.query(ExampleModel).count()

        @dummy
        def get_record_count_retry_inside(self):
            with self.db.get_session() as session:
                @transaction_retry(session=session)
                def foo():
                    return session.query(ExampleModel).count()

                return foo()

        @dummy
        def get_record_count_no_retry(self):
            with self.db.get_session() as session:
                return session.query(ExampleModel).count()

        @dummy
        @transaction_retry
        def create_without_context_manager(self):
            session = self.db.get_session()
            session.add(ExampleModel(data='created without context manager'))
            session.commit()

        @dummy
        @transaction_retry(session=operator.attrgetter('db.session'))
        def create_with_worker_scoped_session(self):
            self.db.session.add(ExampleModel(data='created in worker scope'))
            self.db.session.commit()

    class ExampleServiceWithDatabaseSession:
        name = 'exampleservice'

        session = DatabaseSession(DeclBase)

        @dummy
        def create_record(self):
            self.session.add(ExampleModel(data='hello'))
            self.session.commit()

        @dummy
        @transaction_retry(session=operator.attrgetter('session'))
        def get_record_count(self):
            return self.session.query(ExampleModel).count()

        @dummy
        def get_record_count_retry_inside(self):
            session = self.session

            @transaction_retry(session=session)
            def foo():
                return session.query(ExampleModel).count()

            return foo()

        @dummy
        def get_record_count_no_retry(self):
            return self.session.query(ExampleModel).count()

    @pytest.fixture(params=['Database', 'DatabaseSession'])
    def service_cls(self, request):
        if request.param == 'Database':
            return self.ExampleServiceWithDatabase
        elif request.param == 'DatabaseSession':
            return self.ExampleServiceWithDatabaseSession

    @pytest.fixture
    def container(self, container_factory, toxiproxy_db_url, service_cls):
        config = {
            DB_URIS_KEY: {
                'exampleservice:examplebase': toxiproxy_db_url
            }
        }

        container = container_factory(service_cls, config)
        container.start()

        return container

    def test_retries(self, toxiproxy, disconnect, container):
        if not toxiproxy:
            pytest.skip('Toxiproxy not installed')

        with entrypoint_hook(container, 'create_record') as create_record:
            create_record()

        disconnect(reconnect=True)

        with entrypoint_hook(container, 'get_record_count') as hook:
            assert hook() == 1

    def test_with_retry_inside(self, toxiproxy, disconnect, container):
        if not toxiproxy:
            pytest.skip('Toxiproxy not installed')

        with entrypoint_hook(container, 'create_record') as create_record:
            create_record()

        disconnect(reconnect=True)

        with entrypoint_hook(
            container, 'get_record_count_retry_inside'
        ) as hook:
            assert hook() == 1

    def test_raises_without_retry(self, toxiproxy, disconnect, container):
        if not toxiproxy:
            pytest.skip('Toxiproxy not installed')

        with entrypoint_hook(container, 'create_record') as create_record:
            create_record()

        disconnect(reconnect=True)

        with entrypoint_hook(container, 'get_record_count_no_retry') as hook:
            with pytest.raises(OperationalError):
                hook()

    def test_create_without_context_manager(
        self, toxiproxy, disconnect, container, db_session
    ):
        if not toxiproxy:
            pytest.skip('Toxiproxy not installed')

        with entrypoint_hook(container, 'create_record') as create_record:
            create_record()

        disconnect(reconnect=True)

        try:
            with entrypoint_hook(
                container, 'create_without_context_manager'
            ) as hook:
                hook()
        except ExtensionNotFound:
            pass  # not implemented in ExampleServiceWithDatabaseSession
        else:
            assert db_session.query(ExampleModel).count() == 2

    def test_create_with_worker_scoped_session(
        self, toxiproxy, disconnect, container, db_session
    ):
        if not toxiproxy:
            pytest.skip('Toxiproxy not installed')

        with entrypoint_hook(container, 'create_record') as create_record:
            create_record()

        disconnect(reconnect=True)

        try:
            with entrypoint_hook(
                container, 'create_with_worker_scoped_session'
            ) as hook:
                hook()
        except ExtensionNotFound:
            pass  # not implemented in ExampleServiceWithDatabaseSession
        else:
            assert db_session.query(ExampleModel).count() == 2


def _op_exc(connection_invalidated=False):
    return OperationalError(
        None, None, None, connection_invalidated=connection_invalidated)


@pytest.mark.parametrize(
    'retry_kwargs,'
    'call_results,'
    'expected_result,expected_sleeps',
    [
        # success on first try
        ({'total': 0, 'backoff_factor': 0.5}, [1], 1, []),
        # success on first try
        ({'total': 1, 'backoff_factor': 0.5}, [1], 1, []),
        # single retry + success
        ({'total': 1, 'backoff_factor': 0.5}, [_op_exc(), 2], 2, [0]),
        # single retry + success, same even if more retries would have been
        # possible
        ({'total': 2, 'backoff_factor': 0.5}, [_op_exc(), 2], 2, [0]),
        # Unspecified exception
        (
            {'total': 1, 'backoff_factor': 0.5},
            [ValueError()],
            ValueError,
            []
        ),
        # Specified exception, then unspecified exception
        (
            {'total': 10, 'backoff_factor': 0.5},
            [_op_exc(), ValueError(), 3],
            ValueError,
            [0]
        ),
        # Multiple specified exception, then success
        (
            {'total': 10, 'backoff_factor': 0.5},
            [_op_exc() for _ in range(4)] + [5],
            5,
            [0.0, 1.0, 2.0, 4.0]
        ),
        # Multiple specified exception with max backoff, then success
        (
            {'total': 10, 'backoff_factor': 0.5, 'backoff_max': 1.2},
            [_op_exc() for _ in range(4)] + [5],
            5,
            [0.0, 1.0, 1.2, 1.2]
        ),
        # Multiple specified exception without delay, then success
        (
            {'total': 10, 'backoff_factor': 0},
            [_op_exc() for _ in range(4)] + [5],
            5,
            [0, 0, 0, 0]
        ),
        # Max retries exceeded
        (
            {'total': 3, 'backoff_factor': 0.5},
            [_op_exc() for _ in range(4)],
            OperationalError, [0, 1.0, 2.0]
        ),
    ])
def test_retry_configuration(retry_kwargs, call_results,
                             expected_result, expected_sleeps,
                             monkeypatch):
    sleeps = []

    mocked_sleep = Mock(side_effect=lambda delay: sleeps.append(delay))
    monkeypatch.setattr(sys.modules['nameko_sqlalchemy.transaction_retry'],
                        'sleep', mocked_sleep)

    mocked_fcn = Mock()
    mocked_fcn.side_effect = call_results

    decorator = transaction_retry(**retry_kwargs)
    decorated = decorator(mocked_fcn)

    if (
            isinstance(expected_result, type) and
            issubclass(expected_result, Exception)
    ):
        with pytest.raises(expected_result):
            decorated()

    else:
        result = decorated()
        assert expected_result == result

    assert expected_sleeps == sleeps


def test_multiple_retries_with_disabled_connection(
    toxiproxy_db_session, toxiproxy, disconnect
):
    if not toxiproxy:
        pytest.skip('Toxiproxy not installed')

    state = {'calls': 0}

    @transaction_retry(session=toxiproxy_db_session, total=3)
    def get_model_count():
        state['calls'] += 1
        if state['calls'] >= 3:
            toxiproxy.enable()
        return toxiproxy_db_session.query(ExampleModel).count()

    toxiproxy_db_session.add(ExampleModel(data='hello1'))
    toxiproxy_db_session.add(ExampleModel(data='hello2'))
    toxiproxy_db_session.commit()

    toxiproxy.disable()
    assert get_model_count() == 2
    assert state['calls'] == 3
