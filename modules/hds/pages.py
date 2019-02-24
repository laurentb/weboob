# -*- coding: utf-8 -*-

# Copyright(C) 2014  Romain Bignon
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


from weboob.browser.pages import HTMLPage
from weboob.browser.elements import method, ListElement, ItemElement
from weboob.browser.filters.standard import CleanText, Regexp, Date, Env, Filter
from weboob.browser.filters.html import XPath, Link


class ValidationPage(HTMLPage):
    pass


class HomePage(HTMLPage):
    pass


class Author(object):
    (UNKNOWN,
     MALE,
     FEMALE,
     TRANSEXUAL) = xrange(4)

    def __init__(self, name=None):
        self.name = name
        self.sex = self.UNKNOWN
        self.description = None

    class Sex2Enum(Filter):
        def filter(self, text):
            if text == 'homme':
                return Author.MALE
            if text == 'femme':
                return Author.FEMALE
            return Author.TRANSEXUAL



class Story(object):
    def __init__(self, id=None):
        self.id = id
        self.title = u''
        self.date = None
        self.category = None
        self.author = None
        self.body = None


class HistoryPage(HTMLPage):
    ENCODING = 'iso-8859-1'

    def get_numerous(self):
        return int(CleanText('//div[@align="justify"]/table[1]//td[has-class("t0")]/font/u/strong[1]')(self.doc))

    @method
    class iter_stories(ListElement):
        item_xpath = '//div[@align="justify"]/span[has-class("t4")]'

        class item(ItemElement):
            klass = Story

            def parse(self, el):
                self.env['header'] = el.getprevious().xpath('.//span')[0]
                self.env['body'] = el.getnext().xpath('.//a')

            obj_id = XPath(Env('body')) & Link & Regexp(pattern=r'.*histoire=(\d+)')
            obj_title = CleanText('.')
            obj_date = XPath(Env('header')) & CleanText & Regexp(pattern=r'le (\d+)-(\d+)-(\d+)', template=r'\3-\2-\1') & Date
            obj_category = XPath(Env('header')) & CleanText & Regexp(pattern=u'Catégorie :\s*(.*)\s*Auteur')

            def obj_author(self):
                return Author(self.env['header'].xpath('.//a/text()')[0])

class StoryPage(HTMLPage):
    ENCODING = 'iso-8859-1'

    @method
    class get_story(ItemElement):
        klass = Story

        obj_id = Env('id')
        obj_title = CleanText('//h1')
        obj_date = CleanText('//span[has-class("t4")]') & Regexp(pattern=r'le (\d+)-(\d+)-(\d+)', template=r'\3-\2-\1') & Date
        obj_category = CleanText('//a[starts-with(@href, "histoires-cat")]')

        def obj_body(self):
            div = self.el.xpath('//div[@align="justify"]')[0]
            body = ''
            for para in div.findall('br'):
                if para.text is not None:
                    body += para.text.strip()
                body += '\n'
                if para.tail is not None:
                    body += para.tail.strip()
            return body.replace(u'\x92', "'").strip()


        class obj_author(ItemElement):
            klass = Author

            obj_name = CleanText('//a[starts-with(@href, "fiche.php")][2]')
            obj_sex = CleanText('//td[has-class("t0")]') & Regexp(pattern=r"Auteur (\w+)") & Author.Sex2Enum


class AuthorPage(HTMLPage):
    @method
    class get_author(ItemElement):
        klass = Author

        obj_name = CleanText('//span[has-class("t3")]')
        obj_sex = CleanText('//td[has-class("t0")]') & Regexp(pattern=r"Auteur (\w+)") & Author.Sex2Enum

        def obj_description(self):
            description = u''
            for para in self.el.xpath('//td[has-class("t0")]')[0].getchildren():
                if para.tag not in ('b', 'br'):
                    continue
                if para.text is not None:
                    description += '\n\n%s' % para.text.strip()
                if para.tail is not None:
                    description += '\n%s' % para.tail.strip()
            return description.replace(u'\x92', "'").strip()
