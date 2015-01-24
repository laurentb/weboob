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

import re
from datetime import datetime

from weboob.deprecated.browser import Page
from weboob.tools.ordereddict import OrderedDict
from weboob.capabilities.contact import ProfileNode
from weboob.tools.html import html2text
from weboob.tools.date import local2utc


class LoginPage(Page):
    def login(self, username, password):
        self.browser.select_form(name='loginf')
        self.browser['username'] = username.encode(self.browser.ENCODING)
        self.browser['password'] = password.encode(self.browser.ENCODING)
        self.browser.submit(id='login_btn', nologin=True)


class ThreadPage(Page):
    def get_threads(self):
        li_elems = self.parser.select(self.document.getroot(), "//div[@id='page_content']//li", method= 'xpath')

        threads = []
        for elem in li_elems:
            _class = elem.get('class', '')
            if 'clearfix' in _class.split():
                threads.append({
                        u'username' : unicode(elem.getchildren()[0].get('href').split('/')[-1].split('?')[0]),
                        u'id' : unicode(elem.get('id', '').split('_')[1]),
                        u'date' : unicode(elem.find('.//p[@class="date"]').text)
                })

        return threads


class MessagesPage(Page):
    def get_thread_mails(self):
        mails = {
            'member' : {},
            'messages' : [],
        }

        try:
            mails['member']['pseudo'] = self.parser.tocleanstring(self.document.getroot().cssselect('#message_heading div.username span.name')[0])
        except IndexError:
            mails['member']['pseudo'] = 'Unknown'

        for li in reversed(self.document.xpath('//ul[@id="thread"]//li[contains(@id, "message_")]')):
            try:
                txt = self.parser.tostring(li.xpath('.//div[@class="message_body"]')[0])
            except IndexError:
                continue # 'Match' message
            txt = html2text(txt).strip()

            m = re.search(r'(\d+), ', li.xpath('.//span[@class="timestamp"]//script')[0].text)
            assert m
            date = local2utc(datetime.fromtimestamp(int(m.group(1))))

            id_from = li.find('a').attrib['href'].split('/')[-1].split('?')[0]

            mails['messages'].append({
                'date' : date,
                'message' : unicode(txt),
                'id_from' : unicode(id_from),
            })

        return mails

    def get_post_params(self):
        # http://m.okcupid.com/mailbox
        # Paramètresapplication/x-www-form-urlencoded
        # ajax    1
        # authcode    1,0,1332766806,0x154df106d5af5993;51e1fa019f3423831e5b95c9c91346e5138f99cf
        # body    Ah bah ça y'est, ça marche ?!
        # r1  jeanneplop
        # reply   1
        # sendmsg 1
        # subject
        # threadid    154028265985080112
        # ajax=1&sendmsg=1&r1=jeanneplop&subject=&body=Ah%20bah%20%C3%A7a%20y'est%2C%20%C3%A7a%20marche%20%3F!&threadid=154028265985080112&authcode=1%2C0%2C1332766806%2C0x154df106d5af5993%3B51e1fa019f3423831e5b95c9c91346e5138f99cf&reply=1
        js = self.parser.select(self.document.getroot(), "//script", method='xpath')
        for script in js:
            script = script.text

            if script is None:
                continue
            for line in script.splitlines():
                match = re.match(".*Message\.initialize\([^,]*, '([^']*)', \"\", '([^']*)',.*", line)
                if match is not None:
                    return match.groups()
        raise Exception('Unexpected reply page')


class ProfilePage(Page):
    def get_visit_button_params(self):
        links = self.parser.select(self.document.getroot(), "//a", method='xpath')
        for a in links:
            # Premium users can browse anonymusly, need to click on a button to let the other person her profile was visited
            onclick = a.get("onclick")

            if onclick is None:
                continue
            for line in onclick.splitlines():
                match = re.match("^Profile\.action\({stalk:(\d*),u:'(\w*)',tuid:'(\d+)'}", line)
                if match is not None:
                    return match.groups()
        # Default case : no premium, profile already visited
        return None, None, None

    def get_profile(self):
        title = self.parser.select(self.document.getroot(), 'title', 1)
        if title.text == 'OkCupid: Account Not Found':
            return None

        profile = {}
        profile['id'] = unicode(title.text[len('OkCupid: '):])
        profile['data'] = OrderedDict()

        profile_p = self.parser.select(self.document.getroot(), "//div[@id='page_content']//div[contains(@class, 'basics')]//p", method='xpath')

        profile['data']['infos'] = ProfileNode('infos', u'Informations', OrderedDict(), flags=ProfileNode.SECTION)

        info = {
                        'age' : profile_p[1].text.split(u'•', 1)[0].strip(),
                        'location' : profile_p[1].text.split(u'•', 1)[1].strip(),
                        'sex' : profile_p[2].text.strip(),
            }

        for key, val in info.iteritems():
            profile['data']['infos'].value[key] = ProfileNode(key, key.capitalize(), val)

        div_essays = self.parser.select(self.document.getroot(), "//div[@class='essay']", method='xpath')
        h3_essays = self.parser.select(self.document.getroot(), "//div[@id='page_content']//h3", method='xpath')
        essays = OrderedDict(zip(h3_essays, div_essays))

        profile['data']['look_for'] = ProfileNode('look_for', u'Look for', OrderedDict(), flags=ProfileNode.SECTION)
        profile['data']['details'] = ProfileNode('details', u'Details', OrderedDict(), flags=ProfileNode.SECTION)
        profile['data']['essays'] = ProfileNode('essays', u'Essays', OrderedDict(), flags=ProfileNode.SECTION)

        for label, val in essays.iteritems():
            label = unicode(label.text).strip()
            txt = self.parser.tocleanstring(val)
            if 'looking for' in label:
                for i, li in enumerate(val.xpath('.//li')):
                    profile['data']['look_for'].value['look_for_%s' % i] = ProfileNode('look_for_%s' % i, '', li.text.strip())
            elif 'summary' in label and 'summary' not in profile:
                profile['summary'] = txt
            else:
                key = label.replace(' ', '_')
                profile['data']['essays'].value[key] = ProfileNode(key, label, txt)

        details_div = self.parser.select(self.document.getroot(), "//div[@id='details']//li", method='xpath')
        for elem in details_div:
            label = unicode(elem.getchildren()[0].text.strip())
            val = unicode(elem.getchildren()[1].text.strip())
            key = label.lower().replace(' ', '_')
            profile['data']['details'].value[key] = ProfileNode(key, label, val)

        return profile


class PhotosPage(Page):
    def get_photos(self):
        imgs = self.parser.select(self.document.getroot(), "//div[@class='pic clearfix']//img", method='xpath')
        return [unicode(img.get('src')) for img in imgs]


class PostMessagePage(Page):
    def post_mail(self, id, content):
        self.browser.select_form(name='f2')
        self.browser['r1'] = id.encode('utf-8')
        self.browser['body'] = content.encode('utf-8')
        self.browser.submit()


class VisitsPage(Page):
    def get_visits(self):
        ul_item = self.parser.select(self.document.getroot(), '//*[@id="page_content"]/ul[3]', method='xpath')[0]
        visitors = []
        for li in ul_item:
            visitor_id = unicode(li.get('id')[4:])
            visitor_timestamp = unicode(self.parser.select(li, './/div/span', method='xpath')[0].text.strip())
            visitors.append({
                'who': {
                    'id': visitor_id
                },
                'date': visitor_timestamp
            })
        return visitors


class QuickMatchPage(Page):
    def get_id(self):
        element = self.parser.select(self.document.getroot(), '//*[@id="sn"]', method='xpath')[0]
        visitor_id = unicode(element.get('value'))
        return visitor_id

    def get_rating_params(self):
        # initialization
        userid = None
        tuid = None

        # looking for CURRENTUSERID
        js = self.parser.select(self.document.getroot(), "//script", method='xpath')
        for script in js:
            script = script.text
            if script is None:
                continue

            match = re.search('.*var\s*CURRENTUSERID\s*=\s*"(\d+)"', script, flags=re.MULTILINE)
            if match is not None:
                userid = match.group(1)

            match = re.search('"tuid"\s*:\s*"(\d+)"', script, flags=re.MULTILINE)
            if match is not None:
                tuid = match.group(1)

        # Building params hash
        if userid and tuid:
            params = {
                'voterid': userid,
                'target_userid': tuid,
                'target_objectid': 0,
                'type': 'vote',
                'vote_type': 'personality',
                'score': 5,
            }
            return '/vote_handler', 1,params
        else:
            raise Exception('Unexpected reply page')


        # VoteHandler.process('vote', 'personality', stars, tuid, pass.succeed, pass.failure);
        # var params = {voterid: CURRENTUSERID,target_userid: tuid,target_objectid: 0,type: vote_or_note,vote_type: vote_type,score: rating}


class SentPage(Page):
    pass
