# -*- coding: utf-8 -*-

# Copyright(C) 2008-2011  Romain Bignon, Christophe Benz
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


from base64 import b64encode
from hashlib import sha256
from datetime import datetime
import math
import re

from weboob.exceptions import BrowserIncorrectPassword, BrowserHTTPNotFound, BrowserUnavailable
from weboob.browser.exceptions import ClientError
from weboob.browser.browsers import LoginBrowser, DomainBrowser
from weboob.browser.pages import HTMLPage
from weboob.browser.filters.standard import CleanText
from weboob.tools.date import local2utc

from weboob.capabilities.messages import CantSendMessage


__all__ = ['AuMBrowser']


class WebsiteBrowser(LoginBrowser):
    BASEURL = 'https://www.adopteunmec.com'
    VERIFY = False
    TIMEOUT = 3.0

    def do_login(self):
        data = {'username': self.username,
                'password': self.password,
                'remember': 'on',
               }
        self.open('/auth/login', data=data)

    def get_profile(self, id):
        profile = {}
        if datetime.now().hour >= 18 or datetime.now().hour < 1:
            return profile

        r = None
        try:
            r = self.open('https://www.adopteunmec.com/profile/%s' % id)
        except BrowserUnavailable:
            pass

        if r is None or not re.match('https://www.adopteunmec.com/profile/\d+', r.url):
            self.do_login()
            try:
                r = self.open('https://www.adopteunmec.com/profile/%s' % id)
            except BrowserUnavailable:
                r = None

        if r is None:
            return {}

        page = HTMLPage(self, r)
        doc = page.doc
        profile['popu'] = {}
        for tr in doc.xpath('//div[@id="popularity"]//tr'):
            cols = tr.findall('td')
            if not cols[0].text:
                continue
            key = CleanText('./th')(tr).strip().lower()
            value = int(re.sub(u'[^0-9]+', u'', cols[0].text).strip())
            profile['popu'][key] = value

        for script in doc.xpath('//script'):
            text = script.text
            if text is None:
                continue
            m = re.search("'memberLat'\s*:\s*([\-\d\.]+),", text, re.IGNORECASE)
            if m:
                profile['lat'] = float(m.group(1))
            m = re.search("'memberLng'\s*:\s*([\-\d\.]+),", text, re.IGNORECASE)
            if m:
                profile['lng'] = float(m.group(1))

        return profile


def url2id(func):
    def inner(self, id, *args, **kwargs):
        m = re.match('^https?://.*adopteunmec.com.*/(\d+)$', str(id))
        if m:
            id = int(m.group(1))
        else:
            m = re.match('^https?://.*adopteunmec.com/(index.php/)?profile/(\d+).*', str(id))
            if m:
                id = int(m.group(2))
        return func(self, id, *args, **kwargs)
    return inner



class AuMBrowser(DomainBrowser):
    BASEURL = 'https://www.adopteunmec.com/api/'
    APIKEY = 'fb0123456789abcd'
    APITOKEN = 'DCh7Se53v8ejS8466dQe63'
    APIVERSION = '2.2.5'
    GIRL_PROXY = None

    consts = None
    my_sex = 0
    my_id = 0
    my_name = u''
    my_coords = (0,0)

    def __init__(self, username, password, search_query, *args, **kwargs):
        self.username = username
        self.password = password
        self.search_query = search_query
        super(AuMBrowser, self).__init__(*args, **kwargs)

        self.login()

        self.website = WebsiteBrowser(self.username, self.password, *args, **kwargs)
        self.website.do_login()

        self.home()

    def id2url(self, id):
        return u'https://www.adopteunmec.com/profile/%s' % id

    def login(self):
        self.request('applications/android')

    def request(self, *args, **kwargs):
        try:
            return self.open(*args, **kwargs).json()
        except ClientError as e:
            if e.response.status_code == 401:
                raise BrowserIncorrectPassword()
            else:
                raise

    def build_request(self, url, *args, **kwargs):
        headers = kwargs.setdefault('headers', {})
        if 'applications' not in url:
            today = local2utc(datetime.now()).strftime('%Y-%m-%d')
            token = sha256(self.username + self.APITOKEN + today).hexdigest()

            headers['Authorization'] = 'Basic %s' % (b64encode('%s:%s' % (self.username, self.password)))
            headers['X-Platform'] = 'android'
            headers['X-Client-Version'] = self.APIVERSION
            headers['X-AUM-Token'] = token

        return super(AuMBrowser, self).build_request(url, *args, **kwargs)

    def home(self):
        r = self.request('home/')
        self.my_sex = r['user']['sex']
        self.my_id = int(r['user']['id'])
        self.my_name = r['user']['pseudo']

        if self.my_coords == (0,0):
            profile = self.get_full_profile(self.my_id)
            if 'lat' in profile and 'lng' in profile:
                self.my_coords = [profile['lat'], profile['lng']]

        return r

    def get_consts(self):
        if self.consts is not None:
            return self.consts

        self.consts = [{}, {}]
        for key, sexes in self.request('values').iteritems():
            for sex, values in sexes.iteritems():
                if sex in ('boy', 'both'):
                    self.consts[0][key] = values
                if sex in ('girl', 'both'):
                    self.consts[1][key] = values

        return self.consts

    def score(self):
        r = self.home()
        return int(r['user']['points'])

    def get_my_name(self):
        return self.my_name

    def get_my_id(self):
        return self.my_id

    def nb_new_mails(self):
        r = self.home()
        return r['counters']['new_mails']

    def nb_new_baskets(self):
        r = self.home()
        return r['counters']['new_baskets']

    def nb_new_visites(self):
        r = self.home()
        return r['counters']['new_visits']

    def nb_available_charms(self):
        r = self.home()
        return r['subscription']['flashes_stock']

    def get_baskets(self):
        r = self.request('basket', params={'count': 30, 'offset': 0})
        return r['results']

    def get_flashs(self):
        r = self.request('charms/', params={'count': 30, 'offset': 0})
        return r['results']

    def get_visits(self):
        r = self.request('visits', params={'count': 30, 'offset': 0})
        return r['results']

    def get_threads_list(self, count=30):
        r = self.request('threads', params={'count': count, 'offset': 0})
        return r['results']

    @url2id
    def get_thread_mails(self, id, count=30):
        r = self.request('threads/%s' % id, params={'count': count, 'offset': 0})
        return r

    @url2id
    def post_mail(self, id, content):
        content = content.replace('\n', '\r\n')

        try:
            self.request('threads/%s' % id, data=content)
        except BrowserHTTPNotFound:
            raise CantSendMessage('Unable to send message.')

    @url2id
    def delete_thread(self, id):
        r = self.request('message/delete', json={'id_user': id})
        self.logger.debug('Thread deleted: %r' % r)

    @url2id
    def send_charm(self, id):
        try:
            self.request('users/%s/charms' % id, data='')
        except BrowserHTTPNotFound:
            return False
        else:
            return True

    @url2id
    def add_basket(self, id):
        try:
            self.request('basket/%s' % id, data='')
        except BrowserHTTPNotFound:
            return False
        else:
            return True

    def search_profiles(self, **kwargs):
        if not self.search_query:
            # retrieve query
            self.login()

        r = self.request('users?count=100&offset=0&%s' % (self.search_query % {'lat': self.my_coords[0], 'lng': self.my_coords[1]}))
        ids = [s['id'] for s in r['results']]
        return set(ids)

    @url2id
    def get_full_profile(self, id):
        if self.GIRL_PROXY is not None:
            profile = self.open(self.GIRL_PROXY % id).json()
            if 'lat' in profile and 'lng' in profile:
                profile['dist'] = self.get_dist(profile['lat'], profile['lng'])
        else:
            profile = self.get_profile(id)

        return profile

    def get_dist(self, lat, lng):
        coords = (float(lat), float(lng))

        R = 6371
        lat1 = math.radians(self.my_coords[0])
        lat2 = math.radians(coords[0])
        lon1 = math.radians(self.my_coords[1])
        lon2 = math.radians(coords[1])
        dLat = lat2 - lat1
        dLong = lon2 - lon1
        a= pow(math.sin(dLat/2), 2) + math.cos(lat1) * math.cos(lat2) * pow(math.sin(dLong/2), 2)
        c= 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c

    @url2id
    def get_profile(self, id):
        profile = {}

        profile.update(self.request('users/%s' % id))
        profile.update(self.website.get_profile(id))

        # Calculate distance in km.
        profile['dist'] = 0.0
        if 'lat' in profile and 'lng' in profile:
            profile['dist'] = self.get_dist(profile['lat'], profile['lng'])

        return profile
