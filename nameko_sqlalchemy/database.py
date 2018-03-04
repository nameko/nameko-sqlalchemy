from weakref import WeakKeyDictionary

from nameko.extensions import DependencyProvider
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as BaseSession
from sqlalchemy.orm import sessionmaker


DB_URIS_KEY = 'DB_URIS'


class Session(BaseSession):

    def __init__(self, *args, **kwargs):
        self.close_on_exit = kwargs.pop('close_on_exit', False)
        super(Session, self).__init__(*args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                self.rollback()
            else:
                try:
                    self.commit()
                except Exception:
                    self.rollback()
                    raise
        finally:
            if self.close_on_exit:
                self.close()


class DatabaseWrapper(object):

    def __init__(self, Session):
        self.Session = Session
        self._worker_session = None
        self._context_sessions = []

    def get_session(self, close_on_exit=False):
        session = self.Session(close_on_exit=close_on_exit)
        self._context_sessions.append(session)
        return session

    @property
    def session(self):
        if self._worker_session is None:
            self._worker_session = self.Session()
        return self._worker_session

    def close(self):
        if self._worker_session:
            self._worker_session.close()
        for session in self._context_sessions:
            session.close()


class Database(DependencyProvider):

    def __init__(self, declarative_base):
        self.declarative_base = declarative_base
        self.dbs = WeakKeyDictionary()

    def setup(self):
        service_name = self.container.service_name
        declarative_base_name = self.declarative_base.__name__
        uri_key = '{}:{}'.format(service_name, declarative_base_name)

        db_uris = self.container.config[DB_URIS_KEY]
        self.db_uri = db_uris[uri_key].format({
            'service_name': service_name,
            'declarative_base_name': declarative_base_name,
        })

        self.engine = create_engine(self.db_uri)
        self.Session = sessionmaker(bind=self.engine, class_=Session)

    def stop(self):
        self.engine.dispose()
        del self.engine

    def kill(self):
        self.engine.dispose()
        del self.engine

    def worker_teardown(self, worker_ctx):
        db = self.dbs.pop(worker_ctx)
        db.close()

    def get_dependency(self, worker_ctx):
        db = DatabaseWrapper(self.Session)
        self.dbs[worker_ctx] = db
        return db
