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

from weboob.capabilities.bill import DocumentTypes, Bill, Subscription
from weboob.browser.pages import HTMLPage, LoggedPage, pagination
from weboob.browser.filters.standard import Filter, CleanText, Format, Field, Env, Date
from weboob.browser.filters.html import Attr
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.tools.date import parse_french_date


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
        _id = _id.split("'")[3]
        form = self.get_form(name="downpdf_form")
        form['statements_form'] = 'statements_form'
        form['statements_form:j_idcl'] = _id
        form.submit()

    @pagination
    @method
    class iter_documents(ListElement):
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

            condition = lambda self: not (u"tous les relev" in CleanText('a[1]')(self.el)) and not (u'annuel' in CleanText('a[1]')(self.el))

            obj_label = CleanText('a[1]', replace=[(' ', '-')])
            obj_id = Format(u"%s-%s", Env('subid'), Field('label'))
            # Force first day of month as label is in form "janvier 2016"
            obj_date = Format("1 %s", Field('label')) & Date(parse_func=parse_french_date)
            obj_format = u"pdf"
            obj_type = DocumentTypes.BILL
            obj__localid = Attr('a[2]', 'onclick')
