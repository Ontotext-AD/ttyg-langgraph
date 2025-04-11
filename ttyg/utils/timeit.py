import logging
import time
from functools import wraps


def timeit(func):
    """
    Decorator function, which measures the elapsed time for calling the wrapped function and logs it.
    :param func: the wrapped function
    :return: the value returned from the wrapped function
    """

    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = (end_time - start_time) * 1000
        logging.debug(f"Finished {func.__qualname__} in {total_time:.2f} millis")
        return result

    return timeit_wrapper
