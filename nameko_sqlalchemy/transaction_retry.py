
import eventlet
import functools
import operator

import wrapt
from sqlalchemy import exc


def transaction_retry(wrapped=None, session=None, retries=1, backoff_factor=0):

    if wrapped is None:
        return functools.partial(
            transaction_retry, session=session,
            retries=retries, backoff_factor=backoff_factor)

    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):

        @retry(retries, backoff_factor, exc.OperationalError)
        def run_or_rollback():
            try:
                return wrapped(*args, **kwargs)
            except exc.OperationalError as exception:
                if exception.connection_invalidated:
                    if isinstance(session, operator.attrgetter):
                        session(instance).rollback()
                    elif session:
                        session.rollback()
                raise

        return run_or_rollback()

    return wrapper(wrapped)  # pylint: disable=E1120


def retry(retries, backoff_factor, exceptions):

    retries = max(retries, 1)
    backoff_factor = max(backoff_factor, 0)

    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        errors = 0
        while True:
            try:
                return wrapped(*args, **kwargs)
            except exceptions:
                errors += 1

                if errors > retries:
                    raise

                if errors >= 2:
                    backoff_value = backoff_factor * (2 ** (errors - 2))
                else:
                    backoff_value = 0

                eventlet.sleep(backoff_value)

    return wrapper
