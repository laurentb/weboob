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

from weboob.tools.browser import BrowserUnavailable
from weboob.capabilities.dating import Optimization
from weboob.tools.log import getLogger


__all__ = ['ProfilesWalker']


class ProfilesWalker(Optimization):
    def __init__(self, sched, storage, browser):
        self.sched = sched
        self.storage = storage
        self.browser = browser
        self.logger = getLogger('walker', browser.logger)

        self.walk_cron = None
        self.view_cron = None
        self.visited_profiles = set(storage.get('profiles_walker', 'viewed'))
        self.logger.info(u'Loaded %d already visited profiles from storage.' % len(self.visited_profiles))
        self.profiles_queue = set()

    def save(self):
        self.storage.set('profiles_walker', 'viewed', list(self.visited_profiles))
        self.storage.save()

    def start(self):
        self.walk_cron = self.sched.repeat(60, self.enqueue_profiles)
        self.view_cron = self.sched.schedule(randint(5, 10), self.view_profile)
        return True

    def stop(self):
        self.sched.cancel(self.walk_cron)
        self.sched.cancel(self.view_cron)
        self.walk_cron = None
        self.view_cron = None
        return True

    def is_running(self):
        return self.walk_cron is not None

    def enqueue_profiles(self):
        try:
            with self.browser:
                profiles_to_visit = self.browser.search_profiles().difference(self.visited_profiles)
                self.logger.info(u'Enqueuing profiles to visit: %s' % profiles_to_visit)
                self.profiles_queue = set(profiles_to_visit)
            self.save()
        except BrowserUnavailable:
            return

    def view_profile(self):
        try:
            try:
                id = self.profiles_queue.pop()
            except KeyError:
                return  # empty queue

            try:
                with self.browser:
                    profile = self.browser.get_profile(id)
                self.logger.info(u'Visited profile %s (%s)' % (profile['pseudo'], id))

                # Get score from the aum_score module
                #d = self.nucentral_core.callService(context.Context.fromComponent(self), 'aum_score', 'score', profile)
                # d.addCallback(self.score_cb, profile.getID())
                # deferredlist.append(d)

                # do not forget that we visited this profile, to avoid re-visiting it.
                self.visited_profiles.add(id)
                self.save()

            except BrowserUnavailable:
                # We consider this profil hasn't been [correctly] analysed
                self.profiles_queue.add(id)
                return
            except Exception as e:
                print e
        finally:
            if self.view_cron is not None:
                self.view_cron = self.sched.schedule(randint(5, 10), self.view_profile)
