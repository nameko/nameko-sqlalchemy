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

* `pysqlite <http://docs.sqlalchemy.org/en/rel_0_9/dialects/sqlite.html#module-sqlalchemy.dialects.sqlite.pysqlite>`_ (tested in this repo)
* `pymysql <http://docs.sqlalchemy.org/en/rel_0_9/dialects/mysql.html#module-sqlalchemy.dialects.mysql.pymysql>`_


Pytest fixtures
---------------

Pytest fixtures to allow for easy testing are available.

* `db_session` fixture (which depends on `db_connection` fixture) will instantiate test database and tear it down at the end of each test.
* `db_url` fixture can be overridden to provide custom test database url
* `base` fixture can be overridden to provide custom `declarative_base`

.. code-block:: python

    import pytest

    from sqlalchemy import Column, Integer, String
    from sqlalchemy.ext.declarative import declarative_base


    class Base:
        pass


    Base = declarative_base(cls=Base)


    class User(Base):
        __tablename__ = "users"

        id = Column(Integer, primary_key=True)
        name = Column(String)


    @pytest.fixture(scope='session')
    def base():
        return Base


    def test_fixtures(db_session):
        user = User(id=1, name='Joe')
        db_session.add(user)
        db_session.commit()
        saved_user = db_session.query(User).get(user.id)
        assert saved_user.id > 0
        assert saved_user.name == 'Joe'
