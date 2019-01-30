import functools
import operator

import wrapt
from sqlalchemy import exc
from nameko.utils.retry import retry


def transaction_retry(wrapped=None, session=None,
                      max_attempts=1, delay=0, backoff=1, max_delay=None):

    if wrapped is None:
        return functools.partial(
            transaction_retry, session=session, max_attempts=max_attempts,
            delay=delay, backoff=backoff, max_delay=max_delay)

    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):

        @retry(for_exceptions=exc.OperationalError, max_attempts=max_attempts,
               delay=delay, backoff=backoff, max_delay=max_delay)
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
