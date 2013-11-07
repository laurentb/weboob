# -*- coding: utf-8 -*-

# Copyright(C) 2013      Vincent A
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


import datetime
import re
import urllib
from urlparse import urlsplit
from weboob.tools.browser import BasePage
from weboob.capabilities.messages import Message, Thread

import ovsparse

__all__ = ['PagePrivateThreadsList', 'PagePrivateThread', 'PageLogin', 'PageIndex', 'DummyPage', 'PagePostMessage', 'PageUserProfile', 'PageCityList']


class OvsPage(BasePage):
    def is_logged(self):
        return ovsparse.is_logged(self.document)

    def login(self, username, password):
        self.browser.select_form(name='connection')
        self.browser['Pseudo'] = username.encode(self.browser.ENCODING)
        self.browser['Password'] = password.encode(self.browser.ENCODING)
        self.browser['Retenir'] = ['ok']
        self.browser.submit(nologin=True)


class PagePrivateThreadsList(OvsPage):
    def iter_threads_list(self):
        # site is sorted from latest to oldest
        for message_a in reversed(self.document.findAll('a', href=re.compile(r'message_read.php\?'))):
            ovs_id = re.search(r'Id=(\d+)', message_a["href"]).group(1)
            id_ = ovs_id

            thread = Thread(id_)
            thread.title = ovsparse.all_text_recursive(message_a)
            thread.flags = Thread.IS_DISCUSSION

            #~ parent_tr = message_a.findParent('tr')
            #~ username = all_text_recursive(parent_tr.find('a', href=re.compile(r'profil_read.php\?.*')))
            #~ notread_self = (parent_tr.get('class') == 'newmails')
            #~ notread_other = (parent_tr.find('span', **{'class': 'new_sortiepartenaire'}) is not None)

            yield thread


class PagePrivateThread(OvsPage):
    def get_thread(self, _id):
        thread = Thread(_id)

        thread.title = self.document.find('div', 'PADtitreBlanc_txt').find('center').string
        thread.flags = Thread.IS_DISCUSSION
        root = True

        for message in self._get_messages(thread):
            if root:
                message.children = []
                thread.root = message
                thread.date = message.date
                message.title = thread.title
                root = False
            else:
                message.title = 'Re: %s' % thread.title
                message.children = []
                message.parent = thread.root
                thread.root.children.append(message)

        return thread

    def _get_messages(self, thread):
        thread_div = self.document.find(True, 'PADpost_txt')
        used_ids = set()

        rcpt = self.document.find('input', attrs={'type': 'hidden', 'name': 'Dest'})['value']
        sender_to_receiver = {rcpt: self.browser.username, self.browser.username: rcpt}
        # site is sorted from latest to oldest message
        for message_table in reversed(thread_div.findAll('table')):
            for td in message_table.findAll('td'):
                profile_a = td.find('a', href=re.compile(r'profil_read.php\?.*'))
                if not profile_a:
                    continue

                first_br = td.find('br')
                assert first_br.nextSibling.name == 'br'
                text_nodes = ovsparse.all_next_siblings(first_br.nextSibling.nextSibling) # TODO
                #~ print text_nodes

            # date will be used as id
            sitedate = profile_a.findParent('div').find(text=re.compile(',.*')).replace(', ', '')
            sysdate = ovsparse.parse_date_from_site(sitedate)
            compactdate = datetime.datetime.strftime(sysdate, '%Y%m%dT%H%M%S')

            # but make it unique
            msg_id = ovsparse.create_unique_id(compactdate, used_ids)
            used_ids.add(msg_id)

            message = Message(thread, msg_id)

            message.sender = re.search(r'\?(.+)', profile_a['href']).group(1)
            message.receivers = [sender_to_receiver[message.sender]]

            message.date = sysdate

            message.content = ovsparse.html_message_to_text(text_nodes)

            notread_self = bool(td.find('span', 'ColorSurligne'))
            notread_other = bool(td.find('span', 'new_sortiepartenaire'))
            if notread_other or notread_self:
                message.flags |= Message.IS_NOT_RECEIVED
            else:
                message.flags |= Message.IS_RECEIVED

            yield message

    def post_to_thread(self, thread_id, subject, body):
        form = ovsparse.private_message_form_fields(self.document)
        recode_dict(form, self.browser.ENCODING)
        form['Message'] = body.encode(self.browser.ENCODING)
        self.browser.location('/message_action_envoi.php', urllib.urlencode(form))

        # html code is so broken that mechanize won't parse the forms
        #~ self.browser.select_form('envoimail')
        #~ self.browser['Message'] = body.encode(self.browser.ENCODING)
        #~ self.browser['Pere'] = thread_id.encode(self.browser.ENCODING)
        #~ self.browser['Titre'] = subject.encode(self.browser.ENCODING)
        #~ self.browser.submit()


class PageLogin(BasePage):
    pass


class PageIndex(OvsPage):
    pass


class DummyPage(BasePage):
    pass


class PagePostMessage(OvsPage):
    pass


class PageUserProfile(OvsPage):
    def create_thread(self, recipient, subject, body):
        form = ovsparse.private_message_form_fields(self.document)
        recode_dict(form, self.browser.ENCODING)
        form['Message'] = body.encode(self.browser.ENCODING)
        form['Titre'] = subject.encode(self.browser.ENCODING)
        self.browser.location('/message_action_envoi.php', urllib.urlencode(form))

        #~ self.browser.select_form('envoimail')
        #~ self.browser['Titre'] = subject.encode(self.browser.ENCODING)
        #~ self.browser['Message'] = body.encode(self.browser.ENCODING)
        #~ self.browser.submit()


class PageCityList(DummyPage):
    def get_cities(self, master_domain='onvasortir.com'):
        cities = {}
        for home_a in self.document.findAll('a', href=re.compile(r'http://(.*)\.%s/?' % master_domain)):
            hostname = urlsplit(home_a['href']).hostname
            code = hostname.split('.')[0]
            if code == 'www':
                continue
            name = home_a.text
            cities[name] = {'code': code, 'hostname': hostname}
        return cities


def recode_dict(dict_, encoding):
    for k in dict_:
        dict_[k] = dict_[k].encode(encoding)
