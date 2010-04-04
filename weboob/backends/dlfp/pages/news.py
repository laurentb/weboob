# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from .index import DLFPPage
from weboob.tools.parser import tostring
from datetime import datetime
from weboob.backends.dlfp.tools import url2id

class Comment(object):
    def __init__(self, div, reply_id):
        self.id = ''
        self.reply_id = reply_id
        self.title = u''
        self.author = u''
        self.date = u''
        self.body = u''
        self.score = 0
        self.comments = []

        for sub in div.getchildren():
            if sub.tag == 'a':
                self.id = sub.attrib['name']
            elif sub.tag == 'h1':
                self.title = sub.find('b').text
            elif sub.tag == 'div' and sub.attrib.get('class', '').startswith('comment'):
                self.author = sub.find('a').text
                self.date = self.parse_date(sub.find('i').tail)
                self.score = int(sub.findall('i')[1].find('span').text)
                self.body = tostring(sub.find('p'))
            elif sub.attrib.get('class', '') == 'commentsul':
                comment = Comment(sub.find('li'), self.id)
                self.comments.append(comment)

    def parse_date(self, date_s):
        return datetime.strptime(unicode(date_s.strip()), u'le %d/%m/%Y à %H:%M.')

    def iter_all_comments(self):
        for comment in self.comments:
            yield comment
            for c in comment.iter_all_comments():
                yield c

    def __repr__(self):
        return u"<Comment id='%s' author='%s' title='%s'>" % (self.id, self.author, self.title)

class Article(object):
    def __init__(self, _id, tree):
        self.id = _id
        self.title = u''
        self.author = u''
        self.body = u''
        self.part2 = u''
        self.date = u''
        self.comments = []

        for div in tree.findall('div'):
            if div.attrib.get('class', '').startswith('titlediv '):
                self.author = div.find('a').text
                for a in div.find('h1').getiterator('a'):
                    if a.text: self.title += a.text
                    if a.tail: self.title += a.tail
                date_s = unicode(div.findall('a')[1].text)
            if div.attrib.get('class', '').startswith('bodydiv '):
                self.body = tostring(div)

    def append_comment(self, comment):
        self.comments.append(comment)

    def iter_all_comments(self):
        for comment in self.comments:
            yield comment
            for c in comment.iter_all_comments():
                yield c

    def parse_part2(self, div):
        self.part2 = tostring(div)

class ContentPage(DLFPPage):
    def loaded(self):
        self.article = None
        for div in self.document.find('body').find('div').findall('div'):
            if div.attrib.get('class', '') == 'newsdiv':
                self.article = Article(url2id(self.url), div)
            if div.attrib.get('class', '') == 'articlediv':
                self.article.parse_part2(div)
            if div.attrib.get('class', '') == 'comments':
                comment = Comment(div, 0)
                self.article.append_comment(comment)

    def get_article(self):
        return self.article
