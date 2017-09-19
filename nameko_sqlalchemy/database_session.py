from weakref import WeakKeyDictionary

from nameko.extensions import DependencyProvider
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQL_ALCHEMY_KEY = 'SQLALCHEMY'
DB_URIS_KEY = 'DB_URIS'
ENGINE_OPTIONS_KEY = 'ENGINE_OPTIONS'


class DatabaseSession(DependencyProvider):
    def __init__(self, declarative_base, **session_options):
        self.declarative_base = declarative_base
        self.sessions = WeakKeyDictionary()
        self.session_options = session_options

        self.db_uri = None
        self.engine = None

    def setup(self):
        service_name = self.container.service_name
        declarative_base_name = self.declarative_base.__name__
        uri_key = '{}:{}'.format(service_name, declarative_base_name)
        config = self.container.config

        db_uris = config[SQL_ALCHEMY_KEY][DB_URIS_KEY] if SQL_ALCHEMY_KEY in config else config[DB_URIS_KEY]
        self.db_uri = db_uris[uri_key].format({
            'service_name': service_name,
            'declarative_base_name': declarative_base_name,
        })
        self.engine = create_engine(self.db_uri, **config.get(SQL_ALCHEMY_KEY, {}).get(ENGINE_OPTIONS_KEY, {}))

    def stop(self):
        self.engine.dispose()
        del self.engine

    def get_dependency(self, worker_ctx):
        session_cls = sessionmaker(bind=self.engine, **self.session_options)
        session = session_cls()

        self.sessions[worker_ctx] = session
        return session

    def worker_teardown(self, worker_ctx):
        session = self.sessions.pop(worker_ctx)
        session.close()


# backwards compat
Session = DatabaseSession
