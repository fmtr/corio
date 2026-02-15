import time
from multiprocessing import Queue, Process

from corio.logging_tools import logger


class ContextProcess:
    """

    Start/stop a function in a process using a context manager

    """

    def __init__(self, func, restart_delay=5, **kwargs):
        """

        Set up queue etc.

        """
        self.func = func
        self.func_args = kwargs
        self.queue = Queue()
        self.restart_delay = restart_delay
        self.process = None

    def start(self):
        """

        Start processes.

        """

        msg = f'Starting process {self.func.__name__}...'
        logger.warning(msg)

        self.process = Process(target=self.func, kwargs=self.func_args)
        self.process.start()

    def stop(self):
        """

        Stop all processes.

        """

        msg = f'Stopping training processes...'
        logger.warning(msg)
        self.process.terminate()
        self.process = None

    def restart(self):
        """

        Restart the process.

        """
        self.stop()
        time.sleep(self.restart_delay)
        self.start()

    def __enter__(self):
        """

        Start processes in context manager.

        """
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """

        Stop processes when the context manager exits.

        """
        if self.process:
            self.stop()
