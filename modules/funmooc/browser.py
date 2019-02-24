# -*- coding: utf-8 -*-

# Copyright(C) 2015      Vincent A
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from weboob.browser import LoginBrowser, URL, need_login
from weboob.browser.exceptions import HTTPNotFound
from weboob.exceptions import BrowserIncorrectPassword
from weboob.capabilities.image import Thumbnail

from .pages import PageLogin, PageDashboard, PageChapter, PageSection
from .video import MoocVideo

import re


class FunmoocBrowser(LoginBrowser):
    BASEURL = 'https://www.fun-mooc.fr'

    login = URL('/login', '/login_ajax', PageLogin)
    dashboard = URL('/dashboard', PageDashboard)
    course = URL('/courses/(?P<course>[^/]+/[^/]+/[^/]+)/courseware/?$',
                 '/courses/(?P<course>[^/]+/[^/]+/[^/]+)/info/?$',
                 PageChapter)
    chapter = URL('/courses/(?P<course>[^/]+/[^/]+/[^/]+)/courseware'
                  '/(?P<chapter>[0-9a-f]+)/$', PageChapter)
    section = URL('/courses/(?P<course>[^/]+/[^/]+/[^/]+)/courseware/'
                  '(?P<chapter>[0-9a-f]+)/(?P<section>[0-9a-f]+)/$', PageSection)

    file = URL(r'https://.*\.cloudfront\.net/videos/(?P<id>[^/]+)/'
               r'(?P<quality>\w+)\.mp4')

    def __init__(self, username, password, quality='hd', *args, **kwargs):
        super(FunmoocBrowser, self).__init__(username, password, *args, **kwargs)
        self.quality = quality

    def do_login(self):
        self.login.stay_or_go()
        csrf = self.session.cookies.get('csrftoken')
        self.page.login(self.username, self.password, csrf)
        self.dashboard.stay_or_go()
        if not self.page.logged:
            raise BrowserIncorrectPassword()

    def get_video(self, url):
        v = MoocVideo(url)
        v.url = url
        v.ext = 'mp4'
        v.title = re.sub(r'[:/"]', '-', url)
        return v

    @need_login
    def iter_videos(self, course, chapter, section):
        course = course.replace('-', '/')
        assert self.section.stay_or_go(course=course, chapter=chapter, section=section)

        for n, d in enumerate(self.page.iter_videos()):
            video = self.get_video(d['url'])
            if d.get('thumbnail'):
                video.thumbnail = Thumbnail(d['thumbnail'])
            if d.get('title'):
                video.title = d['title']
            yield video

    @need_login
    def iter_sections(self, courseid, chapter):
        course = courseid.replace('-', '/')
        assert self.chapter.stay_or_go(course=course, chapter=chapter)
        for coll in self.page.iter_sections():
            if coll.split_path[:2] == [courseid, chapter]:
                yield coll

    @need_login
    def iter_chapters(self, courseid):
        course = courseid.replace('-', '/')
        assert self.course.stay_or_go(course=course)
        return self.page.iter_chapters()

    @need_login
    def iter_courses(self):
        assert self.dashboard.stay_or_go()
        return self.page.iter_courses()

    @need_login
    def check_collection(self, path):
        if len(path) == 0:
            return True
        elif len(path) > 3:
            return False

        parts = list(zip(('course', 'chapter', 'section'), path))
        parts[0] = (parts[0][0], parts[0][1].replace('-', '/'))
        try:
            getattr(self, parts[-1][0]).open(**dict(parts))
        except HTTPNotFound:
            return False

        return True
