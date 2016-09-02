from weakref import WeakKeyDictionary

from nameko.extensions import DependencyProvider
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DB_URIS_KEY = 'DB_URIS'


class DatabaseSession(DependencyProvider):
    def __init__(self, declarative_base):
        self.declarative_base = declarative_base
        self.sessions = WeakKeyDictionary()

    def setup(self):
        service_name = self.container.service_name
        decl_base_name = self.declarative_base.__name__
        uri_key = '{}:{}'.format(service_name, decl_base_name)

        db_uris = self.container.config[DB_URIS_KEY]
        self.db_uri = db_uris[uri_key].format({
            'service_name': service_name,
            'declarative_base_name': decl_base_name,
        })
        self.engine = create_engine(self.db_uri)

    def stop(self):
        self.engine.dispose()
        del self.engine

    def get_dependency(self, worker_ctx):

        session_cls = sessionmaker(bind=self.engine)
        session = session_cls()

        self.sessions[worker_ctx] = session
        return session

    def worker_teardown(self, worker_ctx):
        session = self.sessions.pop(worker_ctx)
        session.close()

# backwards compat
Session = DatabaseSession
