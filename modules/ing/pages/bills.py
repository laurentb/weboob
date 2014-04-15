# -*- coding: utf-8 -*-

# Copyright(C) 2009-2014  Florent Fourcot
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

from weboob.capabilities.bill import Bill, Subscription
from weboob.tools.browser2 import HTMLPage, LoggedPage
from weboob.tools.browser2.filters import Filter, Attr, CleanText, Format, Field, Env
from weboob.tools.browser2.page import ListElement, ItemElement, method, pagination


__all__ = ['BillsPage']


class FormId(Filter):
    def filter(self, txt):
        formid = txt.split("parameters")[1]
        formid = formid.split("'")[2]
        return formid


class BillsPage(LoggedPage, HTMLPage):
    @method
    class iter_account(ListElement):
        item_xpath = '//ul[@class="unstyled striped"]/li'

        class item(ItemElement):
            klass = Subscription

            obj__javax = Attr("//form[@id='accountsel_form']/input[@name='javax.faces.ViewState']", 'value')
            obj_id = Attr('input', "value")
            obj_label = CleanText('label')
            obj__formid = FormId(Attr('input', 'onclick'))

    def postpredown(self, _id):
        _id = _id.split("'")[5]
        form = self.get_form(name="statements_form")
        form['AJAXREQUEST'] = 'statements_form:stat_region'
        form[_id] = _id
        form.submit()

    @pagination
    @method
    class iter_bills(ListElement):
        item_xpath = '//ul[@id="statements_form:statementsel"]/li'

        def next_page(self):
            lis = self.page.doc.xpath('//form[@name="years_form"]//li')
            selected = False
            ref = None
            for li in lis:
                if "rich-list-item selected" in li.attrib['class']:
                    selected = True
                else:
                    if selected:
                        ref = li.find('a').attrib['id']
                        break
            if ref is None:
                return
            form = self.page.get_form(name="years_form")
            form.pop('years_form:j_idcl')
            form.pop('years_form:_link_hidden_')
            form['AJAXREQUEST'] = "years_form:year_region"
            form[ref] = ref
            return form.request

        class item(ItemElement):
            klass = Bill

            condition = lambda self: not (u"tous les relev" in CleanText('a[1]')(self.el))

            obj_label = CleanText('a[1]', replace=[(' ', '-')])
            obj_id = Format(u"%s-%s", Env('subid'), Field('label'))
            obj_format = u"pdf"
            obj__url = Attr('a[2]', 'href')
            obj__localid = Attr('a[2]', 'onmouseover')
