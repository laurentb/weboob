# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon, Christophe Benz
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

from random import randint

from weboob.deprecated.browser import BrowserUnavailable
from weboob.capabilities.dating import Optimization
from weboob.tools.log import getLogger
from weboob.tools.value import Value, ValuesDict


class ProfilesWalker(Optimization):
    CONFIG = ValuesDict(Value('first_message', label='First message to send to matched profiles', default=''))

    def __init__(self, sched, storage, browser):
        self._sched = sched
        self._storage = storage
        self._browser = browser
        self._logger = getLogger('walker', browser.logger)

        self._config = storage.get('profile_walker', 'config', default=None)
        if self._config == {}:
            self._config = None

        self._view_cron = None
        self._visited_profiles = set(storage.get('profiles_walker', 'viewed'))
        self._logger.info(u'Loaded %d already visited profiles from storage.' % len(self._visited_profiles))
        self._profiles_queue = set()

    def save(self):
        if self._config is None:
            return False

        self._storage.set('profiles_walker', 'viewed', list(self._visited_profiles))
        self._storage.save()

    def start(self):
        self._view_cron = self._sched.schedule(randint(5, 10), self.view_profile)
        return True

    def stop(self):
        self._sched.cancel(self._view_cron)
        self._view_cron = None
        return True

    def is_running(self):
        return self._view_cron is not None

    def set_config(self, params):
        self._config = params
        self._storage.set('profile_walker', 'config', self._config)
        self._storage.save()

    def get_config(self):
        return self._config

    def view_profile(self):
        try:
            id = self._browser.find_match_profile()
            if id in self._visited_profiles:
                return

            try:
                with self._browser:
                    self._browser.do_rate(id)
                    self._browser.visit_profile(id)
                    if self._config['first_message'] != '':
                        self._browser.post_mail(id, unicode(self._config['first_message']))
                self._logger.info(u'Visited profile %s ' % (id))

                # do not forget that we visited this profile, to avoid re-visiting it.
                self._visited_profiles.add(id)
                self.save()

            except BrowserUnavailable:
                # We consider this profil hasn't been [correctly] analysed
                self._profiles_queue.add(id)
                return
            except Exception as e:
                self._logger.exception(e)
        finally:
            if self._view_cron is not None:
                self._view_cron = self._sched.schedule(randint(5, 10), self.view_profile)
