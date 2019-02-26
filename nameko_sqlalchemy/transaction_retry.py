from time import sleep
import functools
import operator

import wrapt
from sqlalchemy import exc


def transaction_retry(wrapped=None, session=None, total=1,
                      backoff_factor=0, backoff_max=None):

    if wrapped is None:
        return functools.partial(
            transaction_retry, session=session,
            total=total,
            backoff_factor=backoff_factor,
            backoff_max=backoff_max)

    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):

        @retry(total, backoff_factor, backoff_max, exc.OperationalError)
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


def retry(total, backoff_factor, backoff_max, exceptions):

    total = max(total, 1)
    backoff_factor = max(backoff_factor, 0)
    backoff_max = float('inf') if backoff_max is None else max(0, backoff_max)

    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        errors = 0
        while True:
            try:
                return wrapped(*args, **kwargs)
            except exceptions:
                errors += 1

                if errors > total:
                    raise

                if errors >= 2:
                    backoff_value = backoff_factor * (2 ** (errors - 1))
                else:
                    backoff_value = 0
                backoff_value = min(backoff_value, backoff_max)

                sleep(backoff_value)

    return wrapper
