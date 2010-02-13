# -*- coding: utf-8 -*-

"""
Copyright(C) 2008-2010  Romain Bignon

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
from logging import error, warning
from weboob.tools.browser import BasePage

class PageBase(BasePage):
    def openContactListPage(self):
        self.browser.follow_link(url_regex=r"/mails.php$")

    def openThreadPage(self, id):
        self.browser.location('/thread.php?id=%d' % int(id))

    def score(self):
        """
            <table width="220">
            <tr>
            <td align=left class=header>popularité</td>
            <td align=right class=header><big style="color:#ff0198;" id=popScore>7.230</big> pts</td>
            </tr>
            </table>
        """

        l = self.document.getElementsByTagName('table')
        for tag in l:
            if tag.getAttribute('width') == '220':
                # <table><tbody(implicit)><td>
                child = tag.childNodes[1].childNodes[0].childNodes[3]
                return child.childNodes[0].childNodes[0].data

        error("Error: I can't find the score :(")
        return '0'

    def __get_indicator(self, elementName):
        """ <span id=mailsCounter><blink>1</blink></span> """

        l = self.document.getElementsByTagName('span')
        for tag in l:
            if tag.getAttribute('id') == elementName:
                child = tag.childNodes[0]

                if not hasattr(child, 'data'):
                    if child.tagName != u'blink':
                        warning("Warning: %s counter isn't a blink and hasn't data" % elementName)
                    child = child.childNodes[0]
                if not hasattr(child, 'data'):
                    break

                return int(child.data)

        error("Error: I can't find the %s counter :(" % elementName)
        return 0

    MYNAME_REGEXP = re.compile("Bonjour (.*)")
    def getMyName(self):
        """ <span class=header2>Bonjour Romain</span> """

        tags = self.document.getElementsByTagName('span')
        for tag in tags:
            if hasattr(tag.firstChild, 'data'):
                m = self.MYNAME_REGEXP.match(tag.firstChild.data)
                if m:
                    return m.group(1)

        warning('Warning: Unable to fetch name')
        return '?'

    def nbNewMails(self):

        return self.__get_indicator(u'mailsCounter')

    def nbNewBaskets(self):

        return self.__get_indicator(u'flashsCounter')

    def nbNewVisites(self):

        return self.__get_indicator(u'visitesCounter')
