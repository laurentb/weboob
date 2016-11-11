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
from weboob.browser.filters.standard import CleanText

import re

class PageLogin(HTMLPage):
    def login(self, email, password, csrf):
        data = {'email': email, 'password': password, 'remember': 'true'}
        headers = {'X-CSRFToken': csrf}
        form = self.get_form(xpath='//form[contains(@class,"login-form")]')

        req = self.browser.build_request(form.url, data=data, headers=headers)
        self.browser.open(req)


class PageDashboard(LoggedPage, HTMLPage):
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
        item_xpath = '//a[has-class("button-chapter")]'

        class item(ItemElement):
            klass = Collection

            obj_title = CleanText('.')

            def obj_split_path(self):
                # parse first section link
                url = self.xpath('./following-sibling::div[has-class("chapter-content-container")]//a')[0].get('href')
                url = self.page.browser.absurl(url)
                match = self.page.browser.section.match(url)
                courseid = self.env['course'].replace('/', '-')
                chapter = match.group('chapter')
                return [courseid, chapter]

            def obj_id(self):
                return '-'.join(self.obj_split_path())

    @method
    class iter_sections(ListElement):
        item_xpath = '//div[has-class("chapter-content-container")]//div[has-class("menu-item")]//a'

        class item(ItemElement):
            klass = Collection

            obj_title = CleanText('.')

            def obj_split_path(self):
                url = self.xpath('.')[0].get('href')
                url = self.page.browser.absurl(url)
                match = self.page.browser.section.match(url)
                courseid = self.env['course'].replace('/', '-')
                chapter = match.group('chapter')
                section = match.group('section')
                return [courseid, chapter, section]

            def obj_id(self):
                return '-'.join(self.obj_split_path())


class PageSection(LoggedPage, HTMLPage):
    video_url = re.compile(r'[^\s;]+/HD\.mp4', re.I)
    video_thumb = re.compile(r'reposter=&#34;(.*?)&#34;')
    video_title = re.compile(r'&lt;h2&gt;(.*?)&lt;/h2&gt;')

    def iter_videos(self):
        urls = set()

        # this part of the site contains escaped HTML...
        for n, page_match in enumerate(self.video_url.finditer(self.text)):
            url = page_match.group(0)
            match = self.browser.file.match(url)
            _id = match.group('id')

            if _id in urls:
                # prevent duplicate urls
                continue
            urls.add(_id)

            beforetext = self.text[:page_match.end(0)]
            try:
                thumb = list(self.video_thumb.finditer(beforetext))[-1].group(1)
            except IndexError:
                thumb = None
            try:
                title = list(self.video_title.finditer(beforetext))[-1].group(1)
            except IndexError:
                title = u'%s - %s' % (_id, n)

            yield {
                'id': _id,
                'title': title,
                'thumbnail': thumb,
            }
