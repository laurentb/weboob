# -*- coding: utf-8 -*-

# Copyright(C) 2009-2014  Romain Bignon, Florent Fourcot
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

from weboob.capabilities.bank import Recipient, AccountNotFound, Transfer
from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, CleanDecimal, Format
from weboob.browser.filters.html import Attr
from .login import INGVirtKeyboard


class TransferPage(LoggedPage, HTMLPage):

    @method
    class get_recipients(ListElement):
        class ExternalRecipients(ListElement):
            item_xpath = '//select[@id="transfer_form:externalAccounts"]/option'

            class item(ItemElement):
                klass = Recipient
                condition = lambda self: Attr('.', 'value')(self.el) != "na"

                obj_id = Attr('.', 'value')
                obj_label = CleanText('.')
                obj__type = 'ext'

        class InternalRecipients(ListElement):
            item_xpath = '//table[@id="transfer_form:receiptAccount"]/tbody/tr'

            class item(ItemElement):
                klass = Recipient

                obj_id = Attr('td[1]/input', 'value')
                obj_label = Format(u"%s %s %s", CleanText('td[1]/label'),
                                   CleanText('td[2]/label'), CleanText('td[3]/label'))
                obj__type = "int"

    def ischecked(self, _id):
        # remove prefix (CC-, LA-, ...)
        if "-" in _id:
            _id = _id.split('-')[1]
        try:
            option = self.doc.xpath('//input[@value="%s"]' % _id)[0]
        except:
            raise AccountNotFound()
        return option.attrib.get("checked") == "checked"

    def transfer(self, recipient, amount, reason):
        form = self.get_form(name="transfer_form")
        form.pop('transfer_form:_link_hidden_')
        form.pop('transfer_form:j_idcl')
        form['AJAXREQUEST'] = "_viewRoot"
        form['AJAX:EVENTS_COUNT'] = "1"
        form['transfer_form:transferMotive'] = reason
        form["transfer_form:valide"] = "transfer_form:valide"
        form["transfer_form:validateDoTransfer"] = "needed"
        form["transfer_form:transferAmount"] = str(amount)
        if recipient._type == "int":
            form['transfer_recipient_radio'] = recipient.id
        else:
            form['transfer_form:externalAccounts'] = recipient.id
        form.submit()

    def buildonclick(self, recipient, account):
        javax = self.doc.xpath('//input[@id="javax.faces.ViewState"]')[0].attrib['value']
        if recipient._type == "ext":
            select = self.doc.xpath('//select[@id="transfer_form:externalAccounts"]')[0]
            onclick = select.attrib['onchange']
            params = onclick.split(',')[3].split('{')[1]
            idparam = params.split("'")[1]
            param = params.split("'")[3]
            request = {"AJAXREQUEST": "transfer_form:transfer_radios_form",
                       "transfer_form:generalMessages": "",
                       "transfer_issuer_radio": account.id[3:],
                       "transfer_form:externalAccounts": recipient.id,
                       "transfer_date": "0",
                       "transfer_form:transferAmount": "",
                       "transfer_form:transferMotive": "",
                       "transfer_form:validateDoTransfer": "needed",
                       "transfer_form": "transfer_form",
                       "autoScrol": "",
                       "javax.faces.ViewState": javax,
                       idparam: param}
            return request
        elif recipient._type == "int":
            for input in self.doc.xpath('//input[@value=%s]' % recipient.id):
                if input.attrib['name'] == "transfer_recipient_radio":
                    onclick = input.attrib['onclick']
                    break
            # Get something like transfer_form:issueAccount:0:click
            params = onclick.split(',')[3].split('{')[1]
            idparam = params.split("'")[1]
            param = params.split("'")[3]
            request = {"AJAXREQUEST": "transfer_form:transfer_radios_form",
                       'transfer_issuer_radio': account.id[3:],
                       "transfer_recipient_radio": recipient.id,
                       "transfer_form:externalAccounts": "na",
                       "transfer_date": 0,
                       "transfer_form:transferAmount": "",
                       "transfer_form:transferMotive": "",
                       "transfer_form:validateDoTransfer": "needed",
                       "transfer_form": "transfer_form",
                       "autoScroll": "",
                       "javax.faces.ViewState": javax,
                       idparam: param}
            return request


class TransferConfirmPage(LoggedPage, HTMLPage):
    def confirm(self, password):
        vk = INGVirtKeyboard(self)

        form = self.get_form(xpath='//div[@id="transfer_panel"]//form')
        for elem in form:
            if "_link_hidden_" in elem or "j_idcl" in elem:
                form.pop(elem)

        form['AJAXREQUEST'] = '_viewRoot'
        form['%s:mrgtransfer' % form.name] = '%s:mrgtransfer' % form.name
        form['%s:mrltransfer' % form.name] = vk.get_coordinates(password)
        form.submit()

    @method
    class recap(ListElement):
        item_xpath = '//div[@class="encadre transfert-validation"]'

        class item(ItemElement):
            klass = Transfer

            obj_amount = CleanDecimal('.//label[@id="confirmtransferAmount"]', replace_dots=True)
            obj_origin = CleanText('.//span[@id="confirmfromAccount"]')
            obj_recipient = CleanText('.//span[@id="confirmtoAccount"]')
            obj_reason = CleanText('.//span[@id="confirmtransferMotive"]')
