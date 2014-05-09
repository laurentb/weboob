# -*- coding: utf-8 -*-

# Copyright(C) 2014      Roger Philibert
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


from weboob.capabilities.dating import ICapDating, Optimization
from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword
from weboob.tools.log import getLogger

from .browser import TinderBrowser, FacebookBrowser


__all__ = ['TinderBackend']


class ProfilesWalker(Optimization):
    def __init__(self, sched, storage, browser):
        self.sched = sched
        self.storage = storage
        self.browser = browser
        self.logger = getLogger('walker', browser.logger)

        self.view_cron = None

    def start(self):
        self.view_cron = self.sched.schedule(1, self.view_profile)
        return True

    def stop(self):
        self.sched.cancel(self.view_cron)
        self.view_cron = None
        return True

    def set_config(self, params):
        pass

    def is_running(self):
        return self.view_cron is not None

    def view_profile(self):
        try:
            self.browser.like_profile()
        finally:
            if self.view_cron is not None:
                self.view_cron = self.sched.schedule(1, self.view_profile)


class TinderBackend(BaseBackend, ICapDating):
    NAME = 'tinder'
    DESCRIPTION = u'Tinder dating mobile application'
    MAINTAINER = u'Roger Philibert'
    EMAIL = 'roger.philibert@gmail.com'
    LICENSE = 'AGPLv3+'
    VERSION = '0.i'
    CONFIG = BackendConfig(Value('username',                label='Facebook email'),
                           ValueBackendPassword('password', label='Facebook password'))

    BROWSER = TinderBrowser

    def create_default_browser(self):
        facebook = FacebookBrowser()
        facebook.login(self.config['username'].get(),
                       self.config['password'].get())
        return TinderBrowser(facebook)

    def init_optimizations(self):
        self.add_optimization('PROFILE_WALKER', ProfilesWalker(self.weboob.scheduler, self.storage, self.browser))
