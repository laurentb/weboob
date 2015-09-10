# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Christophe Benz
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

import logging
import time

__all__ = ['retry']


def retry(ExceptionToCheck, tries=4, delay=3, backoff=2):
    """
    Retry decorator
    from http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from http://wiki.python.org/moin/PythonDecoratorLibrary#Retry
    """
    def deco_retry(f):
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            mtries = kwargs.pop('_tries', mtries)
            mdelay = kwargs.pop('_delay', mdelay)
            try_one_last_time = True
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                    try_one_last_time = False
                    break
                except ExceptionToCheck as e:
                    try:
                        logging.debug(u'%s, Retrying in %d seconds...' % (e, mdelay))
                    except UnicodeDecodeError:
                        logging.debug(u'%s, Retrying in %d seconds...' % (repr(e), mdelay))
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            if try_one_last_time:
                return f(*args, **kwargs)
            return
        return f_retry  # true decorator
    return deco_retry
