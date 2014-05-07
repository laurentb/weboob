# -*- coding: utf-8 -*-

# Copyright(C) 2012 Roger Philibert
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

import urllib

from weboob.tools.browser import BaseBrowser, BasePage
from weboob.tools.ordereddict import OrderedDict

from .pages import LoginPage, ThreadPage, MessagesPage, PostMessagePage, ProfilePage, PhotosPage, VisitsPage

__all__ = ['OkCBrowser']


class OkCException(Exception):
    pass


class OkCBrowser(BaseBrowser):
    DOMAIN = 'm.okcupid.com'
    PROTOCOL = 'https'
    ENCODING = 'UTF-8'
    PAGES = OrderedDict((
            ('https://%s/login.*' % DOMAIN, LoginPage),
            ('http://%s/home' % DOMAIN, BasePage),
            ('http://%s/messages' % DOMAIN, ThreadPage),
            ('http://%s/messages\?compose=1' % DOMAIN, PostMessagePage),
            ('http://%s/messages\?.*' % DOMAIN, MessagesPage),
            ('http://%s/profile/.*/photos' % DOMAIN, PhotosPage),
            ('http://%s/profile/[^/]*' % DOMAIN, ProfilePage),
            ('http://%s/visitors' % DOMAIN, VisitsPage)
    ))

    logged_in = False

    def home(self):
        self.location(self.absurl('/home'))

    def login(self):
        self.location(self.absurl('/login'), no_login=True)
        self.page.login(self.username, self.password)
        self.logged_in = True

    def is_logged(self):
        return self.logged_in

    def check_login(func):
        def inner(self, *args, **kwargs):
            if not self.logged_in:
                self.login()
            return func(self, *args, **kwargs)
        return inner

    def get_consts(self):
        return { 'conts' : 'blah' }
    #    if self.consts is not None:
    #        return self.consts

    #    self.consts = []
    #    for i in xrange(2):
    #        r = self.api_request('me', 'all_values', data={'sex': i})
    #        self.consts.append(r['result']['values'])

    #    return self.consts

    #@check_login
    #def score(self):
    #    #r = self.api_request('member', 'view', data={'id': self.my_id})
    #    return int(r['result']['member']['popu']['popu'])

    def get_my_name(self):
        return self.username

    #@check_login
    #def nb_new_mails(self):
    #    r = self.api_request('me', '[default]')
    #    return r['result']['news']['newMails']

    #@check_login
    #def nb_new_baskets(self):
    #    r = self.api_request('me', '[default]')
    #    return r['result']['news']['newBaskets']

    #@check_login
    #def nb_new_visites(self):
    #    r = self.api_request('me', '[default]')
    #    return r['result']['news']['newVisits']

    #@check_login
    #def nb_available_charms(self):
    #    r = self.login()
    #    return r['result']['flashs']

    #@check_login
    #def nb_godchilds(self):
    #    r = self.api_request('member', 'view', data={'id': self.my_id})
    #    return int(r['result']['member']['popu']['invits'])

    #@check_login
    #def get_baskets(self):
    #    r = self.api_request('me', 'basket')
    #    return r['result']['basket']

    #@check_login
    #def get_flashs(self):
    #    r = self.api_request('me', 'flashs')
    #    return r['result']['all']

    @check_login
    def get_visits(self):
       self.location('http://m.okcupid.com/visitors')
       return self.page.get_visits()

    @check_login
    def get_threads_list(self, count=30):
        self.location('http://m.okcupid.com/messages')
        return self.page.get_threads()

    @check_login
    def get_thread_mails(self, id, count=30):
        id = int(id)
        self.location(self.absurl('/messages?readmsg=true&threadid=%i&folder=1' % id))

        # Find the peer username
        mails = self.page.get_thread_mails(count)
        for mail in mails['messages']:
            if mail['id_from'] != self.get_my_name():
                mails['member']['pseudo'] = mail['id_from']
                break
        return mails

    @check_login
    def post_mail(self, id, content):
        self.location(self.absurl('/messages?compose=1'))
        self.page.post_mail(id, content)

    @check_login
    def post_reply(self, thread_id, content):
        self.location(self.absurl('/messages?readmsg=true&threadid=%s&folder=1' % thread_id))
        username, key = self.page.get_post_params()
        data = urllib.urlencode({
            'ajax' : 1,
            'sendmsg' : 1,
            'r1' : username,
            'subject' : '',
            'body' : content,
            'threadid' : thread_id,
            'authcode' : key,
            'reply' : 1,
            })
        self.addheaders = [('Referer', self.page.url), ('Content-Type', 'application/x-www-form-urlencoded')]
        self.open('http://m.okcupid.com/mailbox', data=data)

    #@check_login
    #@url2id
    #def delete_thread(self, id):
    #    r = self.api_request('message', 'delete', data={'id_user': id})
    #    self.logger.debug('Thread deleted: %r' % r)

    #@check_login
    #@url2id
    #def send_charm(self, id):
    #    try:
    #        self.api_request('member', 'addBasket', data={'id': id})
    #    except AuMException:
    #        return False
    #    else:
    #        return True

    #def search_profiles(self, **kwargs):
    #    if self.search_query is None:
    #        r = self.api_request('searchs', '[default]')
    #        self.search_query = r['result']['search']['query']

    #    params = {}
    #    for key, value in json.loads(self.search_query).iteritems():
    #        if isinstance(value, dict):
    #            for k, v in value.iteritems():
    #                params['%s%s' % (key, k.capitalize())] = v
    #        else:
    #            params[key] = value or ''
    #    r = self.api_request('searchs', 'advanced', '30,0', params)
    #    ids = [s['id'] for s in r['result']['search']]
    #    return set(ids)

    @check_login
    def get_profile(self, id):
        self.location(self.absurl('/profile/%s' % id))
        profile = self.page.get_profile()
        return profile

    @check_login
    def get_photos(self, id):
        self.location(self.absurl('/profile/%s/photos' % id))
        return self.page.get_photos()

    #def _get_chat_infos(self):
    #    try:
    #        data = json.load(self.openurl('http://www.adopteunmec.com/1.1_cht_get.php?anticache=%f' % random.random()))
    #    except ValueError:
    #        raise BrowserUnavailable()

    #    if data['error']:
    #        raise ChatException(u'Error while getting chat infos. json:\n%s' % data)
    #    return data

    #def iter_contacts(self):
    #    def iter_dedupe(contacts):
    #        yielded_ids = set()
    #        for contact in contacts:
    #            if contact['id'] not in yielded_ids:
    #                yield contact
    #            yielded_ids.add(contact['id'])

    #    data = self._get_chat_infos()
    #    return iter_dedupe(data['contacts'])

    #def iter_chat_messages(self, _id=None):
    #    data = self._get_chat_infos()
    #    if data['messages'] is not None:
    #        for message in data['messages']:
    #            yield ChatMessage(id_from=message['id_from'], id_to=message['id_to'], message=message['message'], date=message['date'])

    #def send_chat_message(self, _id, message):
    #    url = 'http://www.adopteunmec.com/1.1_cht_send.php?anticache=%f' % random.random()
    #    data = dict(id=_id, message=message)
    #    headers = {
    #            'Content-type': 'application/x-www-form-urlencoded',
    #            'Accept': 'text/plain',
    #            'Referer': 'http://www.adopteunmec.com/chat.php',
    #            'Origin': 'http://www.adopteunmec.com',
    #            }
    #    request = self.request_class(url, urllib.urlencode(data), headers)
    #    response = self.openurl(request).read()
    #    try:
    #        datetime.datetime.strptime(response,  '%Y-%m-%d %H:%M:%S')
    #        return True
    #    except ValueError:
    #        return False
