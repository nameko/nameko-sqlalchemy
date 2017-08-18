import pytest

from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

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
