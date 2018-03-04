# Nameko relies on eventlet
# You should monkey patch the standard library as early as possible to avoid
# importing anything before the patch is applied.
# See http://eventlet.net/doc/patching.html#monkeypatching-the-standard-library
import eventlet
import json
eventlet.monkey_patch()  # noqa (code before rest of imports)

import pytest
import requests
from nameko.containers import ServiceContainer
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base


TOXIPROXY_PROXY_NAME = 'nameko_sqlalchemy_test_mysql'


DeclarativeBase = declarative_base(name='examplebase')


class ExampleModel(DeclarativeBase):
    __tablename__ = 'example'
    id = Column(Integer, primary_key=True)
    data = Column(String(100))


@pytest.yield_fixture
def container_factory():

    all_containers = []

    def make_container(service_cls, config):
        container = ServiceContainer(service_cls, config)
        all_containers.append(container)
        return container

    yield make_container

    for c in all_containers:
        try:
            c.stop()
        except:
            pass


@pytest.yield_fixture
def toxiproxy(toxiproxy_api_url, toxiproxy_db_url):

    class Controller(object):
        def __init__(self, api_url):
            self.api_url = api_url

        def enable(self):
            resource = 'http://{}/reset'.format(
                self.api_url, TOXIPROXY_PROXY_NAME
            )
            requests.post(resource)

        def disable(self):
            resource = 'http://{}/proxies/{}'.format(
                self.api_url, TOXIPROXY_PROXY_NAME
            )
            data = {
                'enabled': False
            }
            requests.post(resource, json.dumps(data))

        def reset(self):
            self.enable()

    if toxiproxy_api_url and toxiproxy_db_url:
        controller = Controller(toxiproxy_api_url)
        controller.reset()

        yield controller

        controller.reset()
    else:
        yield
