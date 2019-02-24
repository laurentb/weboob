# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon, Christophe Benz
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

from random import randint

from weboob.exceptions import BrowserUnavailable
from weboob.capabilities.dating import Optimization
from weboob.tools.log import getLogger


class ProfilesWalker(Optimization):
    def __init__(self, sched, storage, browser):
        super(ProfilesWalker, self).__init__()
        self._sched = sched
        self._storage = storage
        self._browser = browser
        self._logger = getLogger('walker', browser.logger)

        self._walk_cron = None
        self._view_cron = None
        self._visited_profiles = set(storage.get('profiles_walker', 'viewed'))
        self._logger.info(u'Loaded %d already visited profiles from storage.' % len(self._visited_profiles))
        self._profiles_queue = set()

    def save(self):
        self._storage.set('profiles_walker', 'viewed', list(self._visited_profiles))
        self._storage.save()

    def start(self):
        self._walk_cron = self._sched.repeat(60, self.enqueue_profiles)
        self._view_cron = self._sched.schedule(randint(5, 10), self.view_profile)
        return True

    def stop(self):
        self._sched.cancel(self._walk_cron)
        self._sched.cancel(self._view_cron)
        self._walk_cron = None
        self._view_cron = None
        return True

    def is_running(self):
        return self._walk_cron is not None

    def enqueue_profiles(self):
        try:
            profiles_to_visit = self._browser.search_profiles().difference(self._visited_profiles)
            self._logger.info(u'Enqueuing profiles to visit: %s' % profiles_to_visit)
            self._profiles_queue = set(profiles_to_visit)
            self.save()
        except BrowserUnavailable:
            return

    def view_profile(self):
        try:
            try:
                id = self._profiles_queue.pop()
            except KeyError:
                return  # empty queue

            try:
                profile = self._browser.get_profile(id)
                self._logger.info(u'Visited profile %s (%s)' % (profile['pseudo'], id))

                # Get score from the aum_score module
                #d = self.nucentral_core.callService(context.Context.fromComponent(self), 'aum_score', 'score', profile)
                # d.addCallback(self.score_cb, profile.getID())
                # deferredlist.append(d)

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
