# -*- coding: utf-8 -*-

# Copyright(C) 2010  Nicolas Duhamel
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


import re

from weboob.capabilities.bank import Operation

from weboob.tools.browser import BasePage


__all__ = ['AccountHistory']


def remove_html_tags(data):
    p = re.compile(r'<.*?>')
    return p.sub(' ', data)


def remove_extra_spaces(data):
    p = re.compile(r'\s+')
    return p.sub(' ', data)


class AccountHistory(BasePage):
    def on_loaded(self):
        if self.document.docinfo.doctype == '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Frameset//EN" ' \
            '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd">':
            self.browser.follow_link(url_regex="releve", tag="a")

    def get_history(self):
        mvt_table = self.document.xpath("//table[@id='mouvements']", smart_strings=False)[0]
        mvt_ligne = mvt_table.xpath("./tbody/tr")

        operations = []

        for mvt in mvt_ligne:
            operation = Operation(len(operations))
            operation.date = mvt.xpath("./td")[0].text
            tp = mvt.xpath("./td")[1]
            operation.label = remove_extra_spaces(remove_html_tags(self.browser.parser.tostring(tp)))

            r = re.compile(r'\d+')
            tp = mvt.xpath("./td/span")
            amount = None
            for t in tp:
                if r.search(t.text):
                    amount = t.text
            amount =  ''.join( amount.replace('.', '').replace(',', '.').split() )
            if amount[0] == "-":
                operation.amount = -float(amount[1:])
            else:
                operation.amount = float(amount)

            operations.append(operation)
        return operations
