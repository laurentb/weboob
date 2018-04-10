import multiprocessing
import os
from datetime import datetime


__all__ = ['AutoCleanConfig', 'ForkingConfig', 'TimeBufferConfig']


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


class TimeBufferConfig(object):
    """
    Really saves only every saved_since_seconds seconds.
    It is possible to force save (e.g. at exit) with force_save().
    """
    last_save = None
    saved_since_seconds = None

    def __init__(self, path, saved_since_seconds=None):
        super(TimeBufferConfig, self).__init__(path)
        self.saved_since_seconds = saved_since_seconds

    def load(self, default={}):
        super(TimeBufferConfig, self).load(default)
        self.last_save = datetime.now()

    def save(self, saved_since_seconds=None):
        if saved_since_seconds is None:
            saved_since_seconds = self.saved_since_seconds
        if saved_since_seconds and self.last_save:
            if (datetime.now() - self.last_save).seconds < saved_since_seconds:
                return
        super(TimeBufferConfig, self).save()
        self.last_save = datetime.now()

    def force_save(self):
        self.save(False)

    def __exit__(self, t, v, tb):
        self.force_save()
        super(TimeBufferConfig, self).__exit__(t, v, tb)
