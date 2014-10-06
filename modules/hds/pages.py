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

from weboob.deprecated.browser import Page


class ValidationPage(Page):
    pass


class HomePage(Page):
    pass


class Author(object):
    (UNKNOWN,
     MALE,
     FEMALE,
     TRANSEXUAL) = xrange(4)

    def __init__(self, name):
        self.name = name
        self.sex = self.UNKNOWN
        self.email = None
        self.description = None


class Story(object):
    def __init__(self, id):
        self.id = id
        self.title = u''
        self.date = None
        self.category = None
        self.author = None
        self.body = None


class HistoryPage(Page):
    def get_numerous(self):
        td = self.parser.select(self.document.getroot(), 'td.t0', 1)
        n = td.xpath('//u/strong|//u/b')[0].text
        return int(n)

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
                story.author = Author(link.text.strip())
                if not link.tail:
                    self.logger.warning('There is probably a mistake in the name of %s, skipping...' % story.author.name)
                    story = None
                    continue
                date_text = link.tail.strip().split('\n')[-1].strip()
                m = re.match('.*, le (\d+)-(\d+)-(\d+)', date_text)
                if not m:
                    self.logger.warning('Unable to parse datetime "%s"' % date_text)
                    story = None
                    continue
                story.date = datetime.date(int(m.group(3)),
                                           int(m.group(2)),
                                           int(m.group(1)))
                yield story
                story = None


class StoryPage(Page):
    def get_story(self):
        p_tags = self.document.getroot().xpath('//body/p')
        if len(p_tags) > 0 and p_tags[0].text.strip() == \
                u"Le r\xe9cit que vous demandez n'est pas accessible actuellement.":
            return None

        story = Story((self.group_dict['id']))
        story.body = u''
        meta = self.parser.select(self.document.getroot(), 'td.t0', 1)
        story.author = Author(meta.xpath('./a[@class="t3"]')[0].text.strip())
        gender = meta.xpath('./a[@class="t0"]')[0].text
        if 'homme' in gender:
            story.author.sex = story.author.MALE
        elif 'femme' in gender:
            story.author.sex = story.author.FEMALE
        else:
            story.author.sex = story.author.TRANSEXUAL
        email_tag = meta.xpath('./span[@class="police1"]')[0]
        story.author.email = email_tag.text.strip()
        for img in email_tag.findall('img'):
            if img.attrib['src'].endswith('meyle1.gif'):
                story.author.email += '@'
            elif img.attrib['src'].endswith('meyle1pouan.gif'):
                story.author.email += '.'
            else:
                self.logger.warning('Unable to know what image is %s' % img.attrib['src'])
            story.author.email += img.tail.strip()

        title_tag = self.parser.select(self.document.getroot(), 'h1', 1)
        story.title = title_tag.text.strip() if title_tag.text else u''

        span = self.parser.select(self.document.getroot(), 'span.t4', 1)
        date_text = span.text.strip().split('\n')[-1].strip()
        m = re.match('(\d+)-(\d+)-(\d+)', date_text)
        if m:
            story.date = datetime.date(int(m.group(3)),
                                       int(m.group(2)),
                                       int(m.group(1)))
        else:
            self.logger.warning('Unable to parse datetime "%s"' % date_text)

        story.category = span.find('br').tail.split(':')[1].strip()

        div = self.parser.select(self.document.getroot(), 'div[align=justify]', 1)
        for para in div.findall('br'):
            if para.text is not None:
                story.body += para.text.strip()
            story.body += '\n'
            if para.tail is not None:
                story.body += para.tail.strip()
        story.body = story.body.replace(u'\x92', "'").strip()
        return story


class AuthorPage(Page):
    def get_author(self):
        p_tags = self.document.getroot().xpath('//body/div/font/b')
        if len(p_tags) > 0 and p_tags[0].text.strip() == \
                u"La fiche de l'auteur n'est plus accessible.":
            return None

        meta = self.parser.select(self.document.getroot(), 'td.t0', 1)
        author_name = meta.xpath('./span[@class="t3"]')[0].text
        if author_name is None:
            author_name = self.group_dict['name']
        author = Author(author_name.strip())
        gender = meta.xpath('./a[@class="t0"]')[0].text
        if not gender:
            author.sex = author.UNKNOWN
        elif 'homme' in gender:
            author.sex = author.MALE
        elif 'femme' in gender:
            author.sex = author.FEMALE
        else:
            author.sex = author.TRANSEXUAL

        author.description = u''
        for para in meta.getchildren():
            if para.tag not in ('b', 'br'):
                continue
            if para.text is not None:
                author.description += '\n\n%s' % para.text.strip()
            if para.tail is not None:
                author.description += '\n%s' % para.tail.strip()
        author.description = author.description.replace(u'\x92', "'").strip()

        if author.description.startswith(u'0 récit '):
            self.logger.warning('This author does not have published any story.')
        return author
