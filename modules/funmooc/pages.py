# -*- coding: utf-8 -*-

# Copyright(C) 2015      Vincent A
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


from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.elements import method, ListElement, ItemElement
from weboob.capabilities.collection import Collection

import re

class PageLogin(HTMLPage):
    def login(self, email, password, csrf):
        data = {'email': email, 'password': password, 'remember': 'true'}
        headers = {'X-CSRFToken': csrf}
        form = self.get_form(xpath='//form[contains(@class,"login-form")]')

        req = self.browser.build_request(form.url, data=data, headers=headers)
        self.browser.open(req)


class PageDashboard(HTMLPage, LoggedPage):
    def iter_courses(self):
        for c in self.doc.xpath('//article[@class="course"]'):
            title = c.xpath('.//h3[@class="course-title"]/a')[0].text.strip()
            link = c.xpath('.//a[contains(@class,"enter-course")]')[0]
            url = self.browser.absurl(link.get('href'))
            match = self.browser.course.match(url)
            courseid = match.group('course').replace('/', '-')
            yield Collection([courseid], title)


class PageChapter(LoggedPage, HTMLPage):
    @method
    class iter_chapters(ListElement):
        item_xpath = '//div[@class="chapter"]'

        class item(ItemElement):
            klass = Collection

            def obj_title(self):
                return self.xpath('.//a')[0].text.strip()

            def obj_split_path(self):
                # parse first section link
                url = self.xpath('.//li//a')[0].get('href')
                url = self.page.browser.absurl(url)
                match = self.page.browser.section.match(url)
                courseid = self.env['course'].replace('/', '-')
                chapter = match.group('chapter')
                return [courseid, chapter]

            def obj_id(self):
                return '-'.join(self.obj_split_path())

    @method
    class iter_sections(ListElement):
        item_xpath = '//div[@class="chapter"]//li'

        class item(ItemElement):
            klass = Collection

            def obj_title(self):
                return self.xpath('.//p')[0].text.strip()

            def obj_split_path(self):
                url = self.xpath('.//a')[0].get('href')
                url = self.page.browser.absurl(url)
                match = self.page.browser.section.match(url)
                courseid = self.env['course'].replace('/', '-')
                chapter = match.group('chapter')
                section = match.group('section')
                return [courseid, chapter, section]

            def obj_id(self):
                return '-'.join(self.obj_split_path())


class PageSection(LoggedPage, HTMLPage):
    def iter_videos(self):
        urls = re.findall(r'[^\s;]+fun-hd\.mp4', self.text)
        for n, url in enumerate(set(urls)):
            match = self.browser.file.match(url)
            _id = match.group('id')
            yield self.browser.get_video(_id)
