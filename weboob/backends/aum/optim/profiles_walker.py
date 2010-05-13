# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon, Christophe Benz
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


from __future__ import with_statement

from logging import info
from random import randint

from weboob.tools.browser import BrowserUnavailable


__all__ = ['ProfilesWalker']


class ProfilesWalker(object):
    def __init__(self, sched, storage, browser):
        self.sched = sched
        self.storage = storage
        self.browser = browser

        self.visited_profiles = set(storage.get('profiles_walker', 'viewed'))
        info(u'Loaded %d already visited profiles from storage.' % len(self.visited_profiles))
        self.profiles_queue = set()
        self.walk_cron = sched.repeat(60, self.enqueue_profiles)
        self.view_cron = sched.schedule(randint(10,40), self.view_profile)

    def save(self):
        self.storage.set('profiles_walker', 'viewed', list(self.visited_profiles))
        self.storage.save()

    def stop(self):
        self.event.cancel(self.event)
        self.event = None

    def enqueue_profiles(self):
        with self.browser:
            profiles_to_visit = self.browser.search_profiles().difference(self.visited_profiles)
            info(u'Enqueuing profiles to visit: %s' % profiles_to_visit)
            self.profiles_queue.update(profiles_to_visit)
        self.save()

    def view_profile(self):
        try:
            try:
                id = self.profiles_queue.pop()
            except KeyError:
                return # empty queue

            try:
                with self.browser:
                    profile = self.browser.get_profile(id)
                info(u'Visited profile %s (%s)' % (profile.get_name(), id))

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
            except Exception, e:
                print e
        finally:
            self.sched.schedule(randint(10,40), self.view_profile)
