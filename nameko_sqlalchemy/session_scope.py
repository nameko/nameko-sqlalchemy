from contextlib import contextmanager

from nameko.extensions import DependencyProvider
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


DB_URIS_KEY = 'DB_URIS'


class DatabaseSessionScope(DependencyProvider):

    def __init__(self, declarative_base):
        self.declarative_base = declarative_base

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
        self.Session = sessionmaker(bind=self.engine)

    def stop(self):
        self.engine.dispose()
        del self.engine

    def get_dependency(self, worker_ctx):

        @contextmanager
        def get_session_scope():
            session = self.Session()
            try:
                yield session
            except:
                session.rollback()
            else:
                session.commit()
            finally:
                session.close()

        return get_session_scope
