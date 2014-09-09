# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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


import random

from weboob.tools.browser import BrowserUnavailable, BrowserIncorrectPassword
from weboob.capabilities.dating import Optimization
from weboob.capabilities.account import AccountRegisterError
from weboob.tools.log import getLogger
from weboob.tools.value import Value, ValuesDict, ValueInt

from aum.captcha import CaptchaError
from aum.exceptions import AdopteWait, AdopteBanned
from aum.browser import AuMBrowser


class PriorityConnection(Optimization):
    CONFIG = ValuesDict(ValueInt('minimal', label='Minimal of godchilds', default=5),
                        Value('domain', label='Domain to use for fake accounts emails', default='aum.example.com'),
                        ValueInt('interval', label='Interval of checks (seconds)', default=3600)
                       )

    def __init__(self, sched, storage, browser):
        self.sched = sched
        self.storage = storage
        self.browser = browser
        self.logger = getLogger('priorityconn', browser.logger)

        self.config = storage.get('priority_connection', 'config', default=None)
        if self.config == {}:
            self.config = None

        self.check_cron = None
        self.activity_cron = None

    def start(self):
        if self.config is None:
            return False

        self.check_cron = self.sched.repeat(int(self.config['interval']), self.check_godchilds)
        self.activity_cron = self.sched.repeat(600, self.activity_fakes)
        return True

    def stop(self):
        self.sched.cancel(self.check_cron)
        self.check_cron = None
        self.sched.cancel(self.activity_cron)
        self.activity_cron = None
        return True

    def is_running(self):
        return self.check_cron is not None

    def set_config(self, params):
        self.config = params
        self.storage.set('priority_connection', 'config', self.config)
        self.storage.save()

    def get_config(self):
        return self.config

    def generate_name(self):
        login = u''
        for x in xrange(8):
            if x % 2:
                login += random.choice(u'aeiou')
            else:
                login += random.choice(u'bcdfghjklmnprstv')

        fakes = self.storage.get('priority_connection', 'fakes')
        while ('%s@%s' % (login, self.config['domain'])) in fakes.iterkeys():
            login += '_'
        return login

    def generate_password(self):
        return '%08x' % random.randint(1, int('ffffffff', 16))

    def check_godchilds(self):
        with self.browser:
            try:
                my_id = self.browser.get_my_id()
                nb_godchilds = self.browser.nb_godchilds()
            except AdopteWait:
                nb_godchilds = 0
            except BrowserUnavailable:
                # We'll check later
                return

        missing_godchilds = int(self.config['minimal']) - nb_godchilds

        self.logger.info('Missing godchilds: %s' % missing_godchilds)

        if missing_godchilds <= 0:
            return

        for i in xrange(missing_godchilds):
            registered = False
            while not registered:
                name = self.generate_name()
                password = self.generate_password()

                browser = AuMBrowser('%s@%s' % (name, self.config['domain']), proxy=self.browser.proxy)
                try:
                    browser.register(password=   password,
                                     sex=        1,  # slut
                                     birthday_d= random.randint(1, 28),
                                     birthday_m= random.randint(1, 12),
                                     birthday_y= random.randint(1975, 1990),
                                     zipcode=    75001,
                                     country=    'fr',
                                     godfather=  my_id)
                except AccountRegisterError as e:
                    self.logger.warning('Unable to register account: %s' % e)
                except CaptchaError:
                    self.logger.warning('Unable to solve captcha... Retrying')
                else:
                    registered = True

                    # set nickname
                    browser.set_nickname(name.strip('_').capitalize())
                    # rate my own profile with good score
                    for i in xrange(4):
                        browser.rate(my_id, i, 5.0)

                    # save fake in storage
                    fake = {'username': browser.username,
                            'password': password}
                    self.storage.set('priority_connection', 'fakes', name, fake)
                    self.storage.save()
                    self.logger.info('Fake account "%s" created (godfather=%s)' % (name, my_id))

    def activity_fakes(self):
        try:
            fakes = self.storage.get('priority_connection', 'fakes', default={})
            if len(fakes) == 0:
                return
            while True:
                name = random.choice(fakes.keys())
                fake = fakes[name]
                try:
                    browser = AuMBrowser(fake['username'], fake['password'], proxy=self.browser.proxy)
                except (AdopteBanned,BrowserIncorrectPassword) as e:
                    self.logger.warning('Fake %s can\'t login: %s' % (name, e))
                    continue

                profiles = browser.search_profiles(country="fr",
                                                   dist='10',
                                                   save=True)

                if not profiles:
                    continue

                id = profiles.pop()
                profile = browser.get_profile(id)
                # bad rate
                for i in xrange(4):
                    browser.rate(profile.get_id(), i, 0.6)
                # deblock
                browser.deblock(profile.get_id())
                return
        except BrowserUnavailable:
            # don't care
            pass
