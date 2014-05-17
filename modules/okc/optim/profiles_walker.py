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
from weboob.tools.value import Value, ValuesDict


__all__ = ['ProfilesWalker']


class ProfilesWalker(Optimization):
    CONFIG = ValuesDict(Value('first_message', label='First message to send to matched profiles', default=''))

    def __init__(self, sched, storage, browser):
        self.sched = sched
        self.storage = storage
        self.browser = browser
        self.logger = getLogger('walker', browser.logger)

        self.config = storage.get('profile_walker', 'config', default=None)
        if self.config == {}:
            self.config = None

        self.view_cron = None
        self.visited_profiles = set(storage.get('profiles_walker', 'viewed'))
        self.logger.info(u'Loaded %d already visited profiles from storage.' % len(self.visited_profiles))
        self.profiles_queue = set()

    def save(self):
        if self.config is None:
            return False

        self.storage.set('profiles_walker', 'viewed', list(self.visited_profiles))
        self.storage.save()

    def start(self):
        self.view_cron = self.sched.schedule(randint(5, 10), self.view_profile)
        return True

    def stop(self):
        self.sched.cancel(self.view_cron)
        self.view_cron = None
        return True

    def is_running(self):
        return self.view_cron is not None

    def set_config(self, params):
        self.config = params
        self.storage.set('profile_walker', 'config', self.config)
        self.storage.save()

    def get_config(self):
        return self.config


    def view_profile(self):
        try:
            id = self.browser.find_match_profile()
            if id in self.visited_profiles:
                return

            try:
                with self.browser:
                    # profile = self.browser.get_profile(id)
                    self.browser.do_rate(id)
                    self.browser.visit_profile(id)
                    if self.config['first_message'] != '':
                        self.browser.post_mail(id, unicode(self.config['first_message']))
                self.logger.info(u'Visited profile %s ' % (id))

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
