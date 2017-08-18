import pytest

from sqlalchemy.exc import OperationalError

from nameko_sqlalchemy import run_query
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

    def get_model_count():
        return db_session.query(ExampleModel).count()

    db_session.add(ExampleModel(data='hello1'))
    db_session.add(ExampleModel(data='hello2'))
    db_session.commit()

    toxiproxy.disable()
    toxiproxy.enable()

    model_count = run_query(db_session, get_model_count)

    # The following would raise "MySQL Connection not available." exception
    # model_count = db_session.query(ExampleModel).count()

    assert model_count == 2

    db_session.close()
    assert db_session.query(ExampleModel).count() == 2


@pytest.mark.usefixtures('example_table')
def test_raises_error_if_cannot_reconnect(db_session, toxiproxy):
    if not toxiproxy:
        pytest.skip('Toxiproxy not installed')

    db_session.add(ExampleModel(data='hello1'))
    db_session.add(ExampleModel(data='hello2'))
    db_session.commit()

    toxiproxy.disable()

    def get_model_count():
        return db_session.query(ExampleModel).count()

    with pytest.raises(OperationalError):
        run_query(db_session, get_model_count)
