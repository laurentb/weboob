#!/usr/bin/env python

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


try:
    import BeautifulSoup
except ImportError:
    import bs4 as BeautifulSoup


def nearest_parent(node, expected):
    return node.findParent(expected)

    while node and node.name != expected:
        node = node.parent
    return node


def all_text_recursive(node):
    return ''.join(node.findAll(text=True))


def all_next_siblings(node):
    ret = []
    while node:
        ret.append(node)
        node = node.nextSibling
    return ret


def image_to_text(src):
    smileys = {'chat/e/grin.gif': ':D',
               'chat/e/unsure.gif': ':s',
               'chat/e/smile.gif': ':)',
               'chat/e/shocked.gif': ':|',
               'chat/e/sad.gif': ':(',
               'chat/e/huh.gif': ':h',
               'chat/e/suprised.gif': ':o',
               'chat/e/cool.gif': 'B)',
               'chat/e/redface.gif': ':red',
               'chat/e/confused.gif': ':=',
               'chat/e/razz.gif': ':p',
               'chat/e/wink.gif': ';)',
               'chat/e/mad.gif': ':x',
               'chat/e/rolleyes.gif': ':b',
               'chat/e/lol.gif': ':lol',
               'chat/e/wub.gif': ':$',
               'chat/e/bouche.gif': ':K',
               'chat/e/sick.gif': '+o('}

    return smileys.get(src)


def html_message_to_text(nodes):
    parts = []

    for node in nodes:
        if isinstance(node, BeautifulSoup.NavigableString):
            parts.append(unicode(node).replace('\r', ''))
        elif node.name == 'img':
            parts.append(image_to_text(node['src']))
        elif node.name == 'a':
            parts.append(node['href'])
        elif node.name == 'br':
            parts.append('\n')
        else:
            assert not ('%s not supported' % node.name)

    return ''.join(parts)


def create_unique_id(proposed_id, used_ids):
    if proposed_id not in used_ids:
        return proposed_id

    def make_id(base, index):
        return '%s-%s' % (base, index)

    index = 1
    while make_id(proposed_id, index) in used_ids:
        index += 1

    return make_id(proposed_id, index)


# public
def private_message_form_fields(document):
    ret = {}
    form = document.find('form', attrs={'name': 'envoimail'})

    def set_if_present(name):
        item = form.find('input', attrs={'name': name})
        if item:
            ret[name] = item['value']

    set_if_present('Pere')
    set_if_present('Sortie')
    set_if_present('Dest')
    set_if_present('Titre')
    return ret


def is_logged(document):
    return (not document.find('form', attrs={'name': 'connection'}))
