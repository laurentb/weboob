# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
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

import random

#from weboob.tools.browser import BrowserUnavailable
from weboob.capabilities.dating import Optimization
from weboob.capabilities.account import AccountRegisterError
from weboob.tools.log import getLogger
from weboob.tools.value import Value, ValuesDict, ValueInt

from weboob.backends.aum.captcha import CaptchaError
from weboob.backends.aum.exceptions import AdopteWait
from weboob.backends.aum.browser import AuMBrowser


__all__ = ['PriorityConnection']


class PriorityConnection(Optimization):
    CONFIG = ValuesDict(ValueInt('minimal', label='Minimal of godchilds', default=5),
                        Value('domain', label='Domain to use for fake accounts emails', default='aum.example.com'),
                        Value('interval', label='Interval of checks (seconds)', default=3600)
                       )

    def __init__(self, sched, storage, browser):
        self.sched = sched
        self.storage = storage
        self.browser = browser
        self.logger = getLogger('walker', browser.logger)

        self.config = storage.get('priority_connection', 'config', default=None)
        if self.config == {}:
            self.config = None

        self.cron = None

    def save(self):
        self.storage.set('profiles_walker', 'viewed', list(self.visited_profiles))
        self.storage.save()

    def start(self):
        if self.config is None:
            return False

        self.cron = self.sched.repeat(self.config['interval'], self.check_godchilds)
        return True

    def stop(self):
        self.sched.cancel(self.cron)
        self.cron = None
        return True

    def is_running(self):
        return self.cron is not None

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
            my_id = self.browser.get_my_id()
            try:
                nb_godchilds = self.browser.nb_godchilds()
            except AdopteWait:
                nb_godchilds = 0

        missing_godchilds = self.config['minimal'] - nb_godchilds
        if missing_godchilds <= 0:
            return

        self.logger.info('Missing godchilds: %s' % missing_godchilds)

        for i in xrange(missing_godchilds):
            registered = False
            while not registered:
                name = self.generate_name()
                password = self.generate_password()

                browser = AuMBrowser('%s@%s' % (name, self.config['domain']))
                try:
                    browser.register(password=   password,
                                     sex=        1, #slut
                                     birthday_d= random.randint(1,28),
                                     birthday_m= random.randint(1,12),
                                     birthday_y= random.randint(1970, 1990),
                                     zipcode=    75001,
                                     country=    'fr',
                                     godfather=  my_id)
                except AccountRegisterError, e:
                    self.logger.warning('Unable to register account: %s' % e)
                except CaptchaError:
                    self.logger.warning('Unable to solve captcha... Retrying')
                else:
                    registered = True
                    browser.set_nickname(name.strip('_').capitalize())
                    fake = {'username': browser.username,
                            'password': password}
                    self.storage.set('priority_connection', 'fakes', name, fake)
                    self.storage.save()
                    self.logger.info('Fake account "%s" created (godfather=%s)' % (name, my_id))
