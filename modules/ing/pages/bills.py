# -*- coding: utf-8 -*-

# Copyright(C) 2009-2012  Romain Bignon, Florent Fourcot
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

from weboob.tools.mech import ClientForm
from weboob.capabilities.bill import Bill, Subscription
from weboob.tools.browser import BasePage


__all__ = ['BillsPage']


class BillsPage(BasePage):
    def on_loaded(self):
        pass

    def iter_account(self):
        ul = self.document.xpath('//ul[@class="unstyled striped"]')
        javax = self.document.xpath("//form[@id='accountsel_form']/input[@name='javax.faces.ViewState']")
        javax = javax[0].attrib['value']
        #subscriber = unicode(self.document.find('//h5').text)
        for li in ul[0].xpath('li'):
            inputs = li.xpath('input')[0]
            label = li.xpath('label')[0]
            label = unicode(label.text)
            formid = inputs.attrib['onclick']
            formid = formid.split("parameters")[1]
            formid = formid.split("'")[2]
            id = inputs.attrib['value']
            subscription = Subscription(id)
            subscription.label = label
            subscription._formid = formid
            subscription._javax = javax
            yield subscription

    def postpredown(self, id):
        self.browser.select_form("statements_form")
        self.browser.set_all_readonly(False)
        self.browser.controls.append(ClientForm.TextControl('text', 'AJAXREQUEST', {'value': 'statements_form:stat_region'}))
        self.browser.controls.append(ClientForm.TextControl('text', id, {'value': id}))
        self.browser.submit(nologin=True)

    def islast(self):
        return True

    def next_page(self):
        pass

    def iter_bills(self, subscriptionid):
        ul = self.document.xpath('//ul[@id="statements_form:statementsel"]')
        lis = ul[0].xpath('li')
        lis.pop(0)  # Select alls
        for li in lis:
            acheck = li.xpath('a')[0]
            adirect = li.xpath('a')[1]
            label = unicode(acheck.text_content())
            id = subscriptionid + '-' + label.replace(' ', '-')
            bill = Bill()
            bill.id = id
            bill.label = label
            bill.format = u"pdf"
            onmouse = adirect.attrib['onmouseover']
            bill._localid = onmouse.split("'")[5]
            bill._url = adirect.attrib['href']
            yield bill
