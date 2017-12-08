import operator

import pytest
from sqlalchemy.exc import OperationalError

from nameko_sqlalchemy import transaction_retry
from test.conftest import DeclarativeBase, ExampleModel


@pytest.fixture(scope='session')
def model_base():
    return DeclarativeBase


@pytest.fixture()
def example_table(db_session):
    ExampleModel.metadata.create_all(db_session.get_bind().engine)


@pytest.mark.usefixtures('example_table')
def test_reconnects_during_transaction(db_session, toxiproxy):
    if not toxiproxy:
        pytest.skip('Toxiproxy not installed')

    @transaction_retry(db_session)
    def get_model_count():
        return db_session.query(ExampleModel).count()

    db_session.add(ExampleModel(data='hello1'))
    db_session.add(ExampleModel(data='hello2'))
    db_session.commit()

    # simulating temporary network issue
    toxiproxy.disable()
    toxiproxy.enable()

    model_count = get_model_count()

    assert model_count == 2

    db_session.close()
    assert db_session.query(ExampleModel).count() == 2


def test_works_in_an_object(db_session, toxiproxy):
    if not toxiproxy:
        pytest.skip('Toxiproxy not installed')

    class ExampleStorage:
        def __init__(self, session):
            self.session = session

        @transaction_retry(operator.attrgetter('session'))
        def get_model_count(self):
            return self.session.query(ExampleModel).count()

    db_session.add(ExampleModel(data='hello1'))
    db_session.add(ExampleModel(data='hello2'))
    db_session.commit()

    # simulating temporary network issue
    toxiproxy.disable()
    toxiproxy.enable()

    example_storage = ExampleStorage(db_session)
    assert 2 == example_storage.get_model_count()


@pytest.mark.usefixtures('example_table')
def test_raises_without_using_transaction_retry(db_session, toxiproxy):
    if not toxiproxy:
        pytest.skip('Toxiproxy not installed')

    def get_model_count():
        return db_session.query(ExampleModel).count()

    db_session.add(ExampleModel(data='hello1'))
    db_session.add(ExampleModel(data='hello2'))
    db_session.commit()

    # simulating temporary network issue
    toxiproxy.disable()
    toxiproxy.enable()

    with pytest.raises(OperationalError):
        db_session.query(ExampleModel).count()


@pytest.mark.usefixtures('example_table')
def test_raises_error_if_cannot_reconnect(db_session, toxiproxy):
    if not toxiproxy:
        pytest.skip('Toxiproxy not installed')

    db_session.add(ExampleModel(data='hello1'))
    db_session.add(ExampleModel(data='hello2'))
    db_session.commit()

    toxiproxy.disable()

    @transaction_retry(db_session)
    def get_model_count():
        return db_session.query(ExampleModel).count()

    with pytest.raises(OperationalError):
        get_model_count()
