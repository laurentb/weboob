# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon
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

from datetime import datetime

import lxml.html

from weboob.tools.date import local2utc
from weboob.tools.compat import unicode

from ..tools import url2id
from .index import DLFPPage


class RSSComment(DLFPPage):
    def on_load(self):
        pass


class Content(object):
    TAGGABLE = False

    def __init__(self, browser):
        self.browser = browser
        self.url = u''
        self.id = u''
        self.title = u''
        self.author = u''
        self.username = u''
        self.body = u''
        self.date = None
        self.score = 0
        self.comments = []
        self.relevance_url = None
        self.relevance_token = None

    def is_taggable(self):
        return False


class Comment(Content):
    def __init__(self, article, div, reply_id):
        super(Comment, self).__init__(article.browser)
        self.reply_id = reply_id
        self.signature = u''
        self.preurl = article.url
        self.div = div
        self.id = div.attrib['id'].split('-')[1]
        subs = div.find('ul')
        if subs is not None:
            for sub in subs.findall('li'):
                comment = Comment(article, sub, self.id)
                self.comments.append(comment)

    def parse(self):
        self.url = '%s#%s' % (self.preurl, self.div.attrib['id'])
        self.title = unicode(self.div.find('h2').xpath('.//a[has-class("title")]')[0].text)
        try:
            a = self.div.find('p').xpath('.//a[@rel="author"]')[0]
        except IndexError:
            self.author = 'Anonyme'
            self.username = None
        else:
            self.author = unicode(a.text)
            self.username = unicode(a.attrib['href'].split('/')[2])
        self.date = datetime.strptime(self.div.find('p').xpath('.//time')[0].attrib['datetime'].split('+')[0],
                                      '%Y-%m-%dT%H:%M:%S')
        self.date = local2utc(self.date)

        content = self.div.find('div')
        try:
            signature = content.xpath('.//p[has-class("signature")]')[0]
        except IndexError:
            # No signature.
            pass
        else:
            content.remove(signature)
            self.signature = lxml.html.tostring(signature).decode('utf-8')
        self.body = lxml.html.tostring(content).decode('utf-8')

        self.score = int(self.div.find('p').xpath('.//span[has-class("score")]')[0].text)
        forms = self.div.find('footer').xpath('.//form[has-class("button_to")]')
        if len(forms) > 0:
            self.relevance_url = forms[0].attrib['action'].rstrip('for').rstrip('against')
            self.relevance_token = forms[0].xpath('.//input[@name="authenticity_token"]')[0].attrib['value']

    def iter_all_comments(self):
        for comment in self.comments:
            yield comment
            for c in comment.iter_all_comments():
                yield c

    def __repr__(self):
        return "<Comment id=%r author=%r title=%r>" % (self.id, self.author, self.title)


class Article(Content):
    TAGGABLE = True

    def __init__(self, browser, url, tree):
        super(Article, self).__init__(browser)
        self.url = url
        self.id = url2id(self.url)

        if tree is None:
            return

        header = tree.find('header')
        self.title = u' — '.join([a.text for a in header.find('h1').xpath('.//a')])
        try:
            a = header.xpath('.//a[@rel="author"]')[0]
        except IndexError:
            self.author = 'Anonyme'
            self.username = None
        else:
            self.author = unicode(a.text)
            self.username = unicode(a.attrib['href'].split('/')[2])
        self.body = lxml.html.tostring(tree.xpath('.//div[has-class("content")]')[0]).decode('utf-8')
        try:
            self.date = datetime.strptime(header.xpath('.//time')[0].attrib['datetime'].split('+')[0],
                                          '%Y-%m-%dT%H:%M:%S')
            self.date = local2utc(self.date)
        except IndexError:
            pass
        for form in tree.find('footer').xpath('//form[has-class("button_to")]'):
            if form.attrib['action'].endswith('/for'):
                self.relevance_url = form.attrib['action'].rstrip('for').rstrip('against')
                self.relevance_token = form.xpath('.//input[@name="authenticity_token"]')[0].attrib['value']

        self.score = int(tree.xpath('.//div[has-class("figures")]//figure[has-class("score")]')[0].text)

    def append_comment(self, comment):
        self.comments.append(comment)

    def iter_all_comments(self):
        for comment in self.comments:
            yield comment
            for c in comment.iter_all_comments():
                yield c


class CommentPage(DLFPPage):
    def get_comment(self):
        article = Article(self.browser, self.url, None)
        return Comment(article, self.doc.xpath('//li[has-class("comment")]')[0], 0)


class ContentPage(DLFPPage):
    article = None

    def is_taggable(self):
        return True

    def get_comment(self, id):
        article = Article(self.browser, self.url, None)
        try:
            li = self.doc.xpath('//li[has-class("comment-%s")]' % id)[0]
        except IndexError:
            return None
        else:
            return Comment(article, li, 0)

    def get_article(self):
        if not self.article:
            self.article = Article(self.browser,
                                   self.url,
                                   self.doc.xpath('//main[@id="contents"]//article')[0])

            try:
                threads = self.doc.xpath('//ul[has-class("threads")]')[0]
            except IndexError:
                pass # no comments
            else:
                for comment in threads.findall('li'):
                    self.article.append_comment(Comment(self.article, comment, 0))

        return self.article

    def get_post_comment_url(self):
        return self.doc.xpath('//p[@id="send-comment"]')[0].find('a').attrib['href']

    def get_tag_url(self):
        return self.doc.xpath('//div[has-class("tag_in_place")]')[0].find('a').attrib['href']


class NewCommentPage(DLFPPage):
    pass


class NewTagPage(DLFPPage):
    def tag(self, tag):
        form = self.get_form(xpath='//form[ends-with(@action,"/tags")]')
        form['tags'] = tag
        form.submit()


class NodePage(DLFPPage):
    def get_errors(self):
        try:
            div = self.doc.xpath('//div[has-class("errors")]')[0]
        except IndexError:
            return []

        l = []
        for li in div.find('ul').findall('li'):
            l.append(li.text)
        return l
