# -*- coding: utf-8 -*-

# Copyright(C) 2012 Lucien Loiseau
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


from weboob.tools.browser import BasePage
import re


LAST_THING_IN_PARENTHESIS = re.compile("\([^)]\)$")


class TranslatePage(BasePage):
    def get_translation(self):
        trs = self.document.getroot().xpath("//table[@class='WRD']/tr[@class='even']")
        if trs and len(trs) > 0:
            # taking the first signification in the case several were found
            return self.parser.select(trs[0], "td[@class='ToWrd']", 1, method='xpath').text
        """
        # taking the first signification in the case several were found
        for tr in self.document.getiterator('tr'):
            prev_was_nums1 = False
            for td in tr.getiterator('td'):
                if prev_was_nums1:
                    result = u''+td.text_content().split(';')[0].strip()
                    result = LAST_THING_IN_PARENTHESIS.sub("",result)
                    return result
                if td.attrib.get('class','') == 'nums1':
                    prev_was_nums1 = True
        # if only one signification is found
        for div in self.document.getiterator('div'):
            if div.attrib.get('class','') == "trans clickable":
                if ']' in div.text_content():
                    tnames = div.text_content().split(']')[1].split()[1:]
                else:
                    tnames = div.text_content().split()[1:]
                names = u''+" ".join(tnames).split(';')[0]
                names = LAST_THING_IN_PARENTHESIS.sub("",names)
                return names.strip()
        # another numerotation possibility...
        for table in self.document.getiterator('table'):
            if table.attrib.get('class','') == "trans clickable":
                prev_was_roman1 = False
                for td in table.getiterator('td'):
                    if prev_was_roman1:
                        return u''+td.text_content().split(';')[0].strip()
                    if td.attrib.get('class','') == 'roman1':
                        prev_was_roman1 = True
        """
