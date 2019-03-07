import multiprocessing
import os
from datetime import datetime


__all__ = ['AutoCleanConfig', 'ForkingConfig', 'TimeBufferConfig', 'time_buffer']


"""
These classes add functionality to existing IConfig classes.
Example:

    class MyYamlConfig(TimeBufferConfig, ForkingConfig, YamlConfig):
        saved_since_seconds = 42

The recommended order is TimeBufferConfig, AutoCleanConfig, ForkingConfig, and then the
actual storage class.
"""


class AutoCleanConfig(object):
    """
    Removes config file if it has no values.
    """
    def save(self):
        if self.values:
            super(AutoCleanConfig, self).save()
        elif os.path.exists(self.path):
            os.remove(self.path)


class ForkingConfig(object):
    """
    Runs the actual save in a forked processes, making save non-blocking.
    It prevents two save() from being called at once by blocking on the previous one
    if it is not finished.
    It is also possible to call join() to wait for the save to complete.
    """
    process = None

    def __init__(self, *args, **kwargs):
        self.lock = multiprocessing.RLock()
        super(ForkingConfig, self).__init__(*args, **kwargs)

    def join(self):
        with self.lock:
            if self.process:
                self.process.join()
            self.process = None

    def save(self):
        # if a save is already in progress, wait for it to finish
        self.join()

        parent_save = super(ForkingConfig, self).save
        with self.lock:
            self.process = multiprocessing.Process(target=parent_save, name=u'save %s' % self.path)
            self.process.start()

    def __exit__(self, t, v, tb):
        self.join()
        super(ForkingConfig, self).__exit__(t, v, tb)


def time_buffer(since_seconds=None, last_run=True, logger=False):
    def decorator_time_buffer(func):
        def wrapper_time_buffer(*args, **kwargs):
            since_seconds = kwargs.pop('since_seconds', None)
            if since_seconds is None:
                since_seconds = decorator_time_buffer.since_seconds
            if logger:
                logger.debug('Time buffer for %s of %s. Last run %s.'
                             % (repr(func), since_seconds, decorator_time_buffer.last_run))
            if since_seconds and decorator_time_buffer.last_run:
                if (datetime.now() - decorator_time_buffer.last_run).seconds < since_seconds:
                    if logger:
                        logger.debug('Too soon to run %s, ignore.' % repr(func))
                    return
            if logger:
                logger.debug('Run %s and record' % repr(func))
            res = func(*args, **kwargs)
            decorator_time_buffer.last_run = datetime.now()
            return res

        decorator_time_buffer.since_seconds = since_seconds
        decorator_time_buffer.last_run = datetime.now() if last_run is True else last_run

        return wrapper_time_buffer
    return decorator_time_buffer


class TimeBufferConfig(object):
    """
    Really saves only every saved_since_seconds seconds.
    It is possible to force save (e.g. at exit) with force_save().
    """
    saved_since_seconds = None

    def __init__(self, path, saved_since_seconds=None, *args, **kwargs):
        super(TimeBufferConfig, self).__init__(path, *args, **kwargs)
        if saved_since_seconds:
            self.saved_since_seconds = saved_since_seconds

        self.save = time_buffer(since_seconds=self.saved_since_seconds)(self.save)

    def force_save(self):
        self.save(since_seconds=False)

    def __exit__(self, t, v, tb):
        self.force_save()
        super(TimeBufferConfig, self).__exit__(t, v, tb)
