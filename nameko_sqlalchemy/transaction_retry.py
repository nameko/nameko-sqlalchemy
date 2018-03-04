import functools
import operator

import wrapt
from sqlalchemy import exc


def transaction_retry(wrapped=None, session=None):

    if wrapped is None:
        return functools.partial(transaction_retry, session=session)

    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):

        try:
            return wrapped(*args, **kwargs)
        except exc.OperationalError as exception:
            if exception.connection_invalidated:
                if isinstance(session, operator.attrgetter):
                    session(instance).rollback()
                elif session:
                    session.rollback()
                return wrapped(*args, **kwargs)
            else:
                raise

    return wrapper(wrapped)  # pylint: disable=E1120
