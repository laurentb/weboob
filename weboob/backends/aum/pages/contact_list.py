# -*- coding: utf-8 -*-

"""
Copyright(C) 2008  Romain Bignon

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

import re

from weboob.backends.aum.pages.base import PageBase

class ContactItem:
    u"""
    <tr bgcolor="#ff7ccb" height=1><td colspan=10></td></tr>
    <tr style="background:#ffd5ee" height=74 onmouseover="this.style.background='#f3d5e7'" onmouseout="this.style.background='#ffd5ee'">
        <td class=a onclick="window.location='/thread.php?id=110921'" width=4></td>
        <td class=a onclick="window.location='/rencontres-femmes/france/ile-de-france/Hen/110921'" width=70 align=left>
            <table><tr valign="bottom"><td style="background:url(http://p1.adopteunmec.com/1/2/9/0/1/thumb0_7.jpg);width:66px;height:66px" align="right">&nbsp;</td></tr></table>
        </td>
        <td class=a onclick="window.location='/thread.php?id=110921'" width=150 align=left><big><b>Hen</b></big><br>
        19ans, Montreuil</td>
        <td class=a onclick="window.location='/thread.php?id=110921'" width=320 align=left><b>Comme ça, on est deux.</b><br>
        il y a 1 heure</td>
        <td class=a onclick="window.location='/thread.php?id=110921'" width=100 align=right>nouveau&nbsp;<img src="http://img.adopteunmec.com/img/ico_mail0.gif" />&nbsp;&nbsp;&nbsp;
        </td>
        <td class=a onclick="window.location='/thread.php?id=110921'" width=30 align=left></td>
        <td width=20 align=right><input id='fcc_suppr_545615' name='suppr[]' type='hidden' /><img id='cc_suppr_545615' src='http://img.adopteunmec.com/img/i/check0.png' onclick='customCheckClick(this)'   align="absmiddle"/>&nbsp;</td>
        <script>supprs[supprs.length] = 'cc_suppr_545615';</script>

        </td>
        <td width=7></td>
        </tr>
    """

    fields = ['thread_link', 'photo', 'useless3', 'name', 'resume', 'status', 'useless', 'remove', 'useless2']

    def __init__(self, tr):
        self.tr = tr

    def __get_element(self, id):

        return self.tr.getElementsByTagName('td')[self.fields.index(id)]

    def get_name(self):
        tag = self.__get_element('name')
        node = tag.getElementsByTagName('b')[0].firstChild
        if node:
            name = node.data
        else:
            # it is possible if the user has left site and hasn't any nickname
            name = ''

        return name

    def get_status(self):

        tag = self.__get_element('status')

        return tag.firstChild.data

    def is_new(self):
        return self.get_status() == u'nouveau'

    def is_answered(self):
        return self.get_status() == u'répondu'

    def get_resume(self):
        tag = self.__get_element('resume')

        return tag.getElementsByTagName('b')[0].firstChild.data.split('\n')[0]

    def get_id(self):
        tag = self.__get_element('thread_link')

        text = tag.getAttribute('onclick')

        regexp = re.compile("window.location='/thread.php\?id=(.*)'")
        m = regexp.match(text)

        if m:
            return int(m.group(1))

        return 0


class ContactListPage(PageBase):
    def on_loaded(self):
        self.items = []

        tags = self.document.getElementsByTagName('form')[0].childNodes[3].childNodes[1].childNodes

        for tag in tags:
            if not hasattr(tag, 'tagName') or tag.tagName != u'tr':
                continue

            if tag.hasAttribute('bgcolor'):
                continue

            self.items += [ContactItem(tag)]

    def get_contact_list(self):
        return self.items
