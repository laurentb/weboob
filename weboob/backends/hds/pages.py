# -*- coding: utf-8 -*-

# Copyright(C) 2011  Romain Bignon
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

from weboob.tools.browser import BasePage


__all__ = ['ValidationPage', 'HomePage', 'HistoryPage', 'StoryPage']


class ValidationPage(BasePage):
    pass

class HomePage(BasePage):
    pass

class Story(object):
    def __init__(self, id):
        self.id = id
        self.title = u''
        self.date = None
        self.author = None
        self.body = None

class HistoryPage(BasePage):
    def iter_stories(self):
        links = self.parser.select(self.document.getroot(), 'a.t11')
        story = None
        for link in links:
            if not story:
                m = re.match('.*histoire=(\d+)', link.attrib['href'])
                if not m:
                    self.logger.warning('Unable to parse ID "%s"' % link.attrib['href'])
                    continue
                story = Story(int(m.group(1)))
                story.title = link.text.strip()
            else:
                story.author = link.text.strip()
                date_text = link.tail.strip().split('\n')[-1].strip()
                m = re.match('(\d+)-(\d+)-(\d+)', date_text)
                if not m:
                    self.logger.warning('Unable to parse datetime "%s"' % date_text)
                    story = None
                    continue
                story.date = datetime.datetime(int(m.group(3)),
                                               int(m.group(2)),
                                               int(m.group(1)))
                yield story
                story = None

class StoryPage(BasePage):
    def get_story(self):
        story = Story((self.group_dict['id']))
        story.body = u''
        story.author = self.parser.select(self.document.getroot(), 'a.t3', 1).text.strip()
        story.title = self.parser.select(self.document.getroot(), 'h1', 1).text.strip()
        date_text = self.parser.select(self.document.getroot(), 'span.t4', 1).text.strip().split('\n')[-1].strip()
        m = re.match('(\d+)-(\d+)-(\d+)', date_text)
        if m:
            story.date = datetime.datetime(int(m.group(3)),
                                           int(m.group(2)),
                                           int(m.group(1)))
        else:
            self.logger.warning('Unable to parse datetime "%s"' % date_text)

        div = self.parser.select(self.document.getroot(), 'div[align=justify]', 1)
        for para in div.findall('br'):
            if para.text is not None:
                story.body += para.text.strip()
            story.body += '\n'
            if para.tail is not None:
                story.body += para.tail.strip()
        story.body = story.body.replace(u'\x92', "'").strip()
        return story
