nameko-sqlalchemy
=================

A SQLAlchemy dependency for `nameko <http://nameko.readthedocs.org>`_, enabling services to interface with a relational database.

Usage
-----

.. code-block:: python

    from nameko_sqlalchemy import Session

    from .models import Model, DeclarativeBase

    class Service(object):

        session = Session(DeclarativeBase)

        @entrypoint
        def write_to_db(self):
            model = Model(...)
            self.session.add(model)
            self.session.commit()

        @entrypoint
        def query_db(self):
            queryset = self.session.query(Model).filter(...)
            ...


Database drivers
----------------

You may use any database `driver compatible with SQLAlchemy <http://docs.sqlalchemy.org/en/rel_0_9/dialects/index.html>`_ provided it is safe to use with `eventlet <http://eventlet.net>`_. This will include all pure-python drivers. Known safe drivers are:

* `pysqlite <http://docs.sqlalchemy.org/en/rel_0_9/dialects/sqlite.html#module-sqlalchemy.dialects.sqlite.pysqlite>`_
* `pymysql <http://docs.sqlalchemy.org/en/rel_0_9/dialects/mysql.html#module-sqlalchemy.dialects.mysql.pymysql>`_


Pytest fixtures
---------------

Pytest fixtures to allow for easy testing are available.

* ``db_session`` fixture (which depends on ``db_connection`` fixture) will instantiate test database and tear it down at the end of each test.
* ``model_base`` fixture can be overridden to provide custom ``declarative_base``.
* ``db_engine_options`` fixture can be overriden to provide additional keyword arguments to ``sqlalchemy.create_engine``.

.. code-block:: python

    import pytest

    from sqlalchemy import Column, Integer, String
    from sqlalchemy.ext.declarative import declarative_base


    class Base(object):
        pass


    DeclarativeBase = declarative_base(cls=Base)


    class User(DeclarativeBase):
        __tablename__ = "users"

        id = Column(Integer, primary_key=True)
        name = Column(String)


    @pytest.fixture(scope='session')
    def model_base():
        return DeclarativeBase


    @pytest.fixture(scope='session')
    def db_engine_options():
        return dict(client_encoding='utf8')


    def test_users(db_session):
        user = User(id=1, name='Joe')
        db_session.add(user)
        db_session.commit()
        saved_user = db_session.query(User).get(user.id)
        assert saved_user.id > 0
        assert saved_user.name == 'Joe'

When running tests you can pass database test url with ``--test-db-url`` parameter or override ``db_url`` fixture.
By default SQLite memory database will be used.

.. code-block:: shell

    py.test test --test-db-url=sqlite:///test_db.sql
    py.test test --test-db-url=mysql+mysqlconnector://root:password@localhost:3306/nameko_sqlalchemy_test

Helper functions
----------------

run_query
^^^^^^^^^
This function provides a way to protect against losing uncommitted changes when a database connection error occur.

Usage
"""""

.. code-block:: python

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from nameko_sqlalchemy import run_query


    engine = create_engine('postgresql://username:password@localhost/test')
    Session = sessionmaker(bind=engine)
    db_session = Session()


    def get_example_data():
        return db_session.query(ExampleModel).all()

    example_data = run_query(db_session, query)

This function handles sqlalchemy database connection errors that are raised during the execution of the passed query and makes sure that the current transaction is rolled back so that sqlalchemy will replay them when it manages to connect to the database again.

Running the tests
-----------------

Prerequisites
^^^^^^^^^^^^^

Some of the tests use `toxiproxy <https://github.com/Shopify/toxiproxy>`_ to simulate network errors. In order to be able to run those tests you need a toxiproxy server to be in place. You may install it manually or by running the following command (docker is required):

.. code-block:: shell

    make setup-containers

This will setup a mysql and a toxiproxy server with a proxy set up to the database.


Running tests by using docker
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Once the containers have been set up the tests can be run by running the following command:

.. code-block:: shell

    make test


Running tests by using py.test command
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Two extra parameters may be passed to `py.test`:

* ``test-db-url``: The database URL
* ``toxiproxy-api-url``: The url of the Toxiproxy HTTP API

If ``toxiproxy-api-url`` parameter is provided the tests assume that the connection to the provided ``test-db-url`` points to a toxiproxy endpoint that is already set up to a database upstream and this proxy can be disabled and enabled via the HTTP API of toxiproxy.

.. code-block:: shell

    py.test test \
        --test-db-url="mysql+pymysql://test_user:password@database_host:3306/nameko_sqlalchemy_test" \
        --toxiproxy-api-url="http://toxiproxy_server:8474"

if no ``toxiproxy-api-url`` parameter was provided the tests that require toxiproxy will be skipped.
