# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.exceptions import BrowserUnavailable
from weboob.capabilities.dating import Optimization


class Visibility(Optimization):
    def __init__(self, sched, browser):
        super(Visibility, self).__init__()
        self._sched = sched
        self._browser = browser
        self._cron = None

    def start(self):
        self._cron = self._sched.repeat(60*5, self.reconnect)
        return True

    def stop(self):
        self._sched.cancel(self._cron)
        self._cron = None
        return True

    def is_running(self):
        return self._cron is not None

    def reconnect(self):
        try:
            self._browser.login()
        except BrowserUnavailable:
            pass
