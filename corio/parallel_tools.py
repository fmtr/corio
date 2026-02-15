import dask
import dask.bag as db
from contextlib import nullcontext as NullContext
from dask.diagnostics import ProgressBar
from multiprocessing import cpu_count
from typing import List, Callable, Any, Union

from corio.iterator_tools import dict_records_to_lists
from corio.logging_tools import logger
from corio.path_tools import Path


class ParallelConfig:
    """

    Configuration values.

    """
    THREADS = 'threads'
    PROCESSES = 'processes'
    SINGLE = 'single-threaded'


def get_nullary_wrapper(func: Callable):
    """

    Dask cannot map a nullary function, as its argument list is empty. Hence this wrapper to force the function to take one dummy argument.

    """

    def wrap_nullary(dummy: None, **kwargs):
        """

        Ignore the dummy argument and run the function.

        """
        return func(**kwargs)

    return wrap_nullary


def apply(func: Callable, data: Union[List[Any], int], *args, num_workers: int = cpu_count(),
          scheduler: str = ParallelConfig.PROCESSES,
          parallelize: bool = True, show_progress: bool = False, return_future: bool = False, **kwargs) -> \
        List[Any]:
    """

    Helper function for a one-off, intensive parallel computation task.

    """

    if not parallelize and scheduler != ParallelConfig.SINGLE:
        msg = f'Scheduler is set to "{scheduler}" but parallelization has been manually disabled.'
        logger.warning(msg)
        scheduler = ParallelConfig.SINGLE

    data_kwargs = {}
    if type(data) is int:  # If data is an integer, assume the function is nullary and just run it the specified number of times.
        data_args = [[None] * data]
        func = get_nullary_wrapper(func)
    else:
        data_args = []
        is_data_lists = all(isinstance(datum, (tuple, list)) for datum in data)
        is_data_dicts = all(isinstance(datum, dict) for datum in data)
        if is_data_lists:  # If the data is a list of tuples/lists of arguments.
            data_args += list(zip(*data))
        elif is_data_dicts:  # If the data is a list of dictionaries of keyword arguments.
            data_kwargs = dict_records_to_lists(data)
        else:
            data_args.append(data)  # Otherwise treat the data as a simple list of arguments.

    dask.config.set({'temporary-directory': Path.temp()})

    data_args = [db.from_sequence(value) for value in data_args]
    data_kwargs = {key: db.from_sequence(values) for key, values in data_kwargs.items()}
    future = db.map(func, *data_args, *args, **data_kwargs, **kwargs)

    def get_results():
        """

        Function to compute results with the specified configuration.

        """
        if show_progress:
            context = ProgressBar
        else:
            context = NullContext

        with context():
            return future.compute(scheduler=scheduler, num_workers=num_workers)

    if return_future:  # Return a delayed function.
        return get_results
    else:
        results = get_results()  # Compute and return results.
        return results
