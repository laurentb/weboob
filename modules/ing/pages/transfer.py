# -*- coding: utf-8 -*-

# Copyright(C) 2009-2011  Romain Bignon, Florent Fourcot
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

from decimal import Decimal

from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.captcha.virtkeyboard import VirtKeyboardError
from weboob.capabilities.bank import Recipient, AccountNotFound, Transfer
from weboob.tools.browser2.page import HTMLPage, LoggedPage
from weboob.tools.browser import BrokenPageError
from .login import INGVirtKeyboard
from logging import error

__all__ = ['TransferPage']


class TransferPage(LoggedPage, HTMLPage):
    def get_recipients(self):
        # First, internals recipients
        table = self.doc.xpath('//table[@id="transfer_form:receiptAccount"]')
        for tr in table[0].xpath('tbody/tr'):
            tds = tr.xpath('td')
            id = tds[0].xpath('input')[0].attrib['value']
            name = tds[0].xpath('label')[0].text
            name += u" " + tds[1].xpath('label')[0].text.replace('\n', '')
            name += u" " + tds[2].xpath('label')[0].text.replace('\n', '')
            recipient = Recipient()
            recipient.id = id
            recipient.label = name
            recipient._type = "int"
            yield recipient

        # Second, externals recipients
        select = self.doc.xpath('//select[@id="transfer_form:externalAccounts"]')
        if len(select) > 0:
            recipients = select[0].xpath('option')
            recipients.pop(0)
            for option in recipients:
                recipient = Recipient()
                recipient.id = option.attrib['value']
                recipient.label = option.text
                recipient._type = "ext"
                yield recipient

    def ischecked(self, account):
        id = account.id
        # remove prefix (CC-, LA-, ...)
        if "-" in id:
            id = id.split('-')[1]
        option = self.doc.xpath('//input[@value="%s"]' % id)
        if len(option) == 0:
            raise AccountNotFound()
        else:
            option = option[0]
        try:
            return option.attrib["checked"] == "checked"
        except:
            return False

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


class TransferConfirmPage(HTMLPage):
    def on_loaded(self):
        pass

    def confirm(self, password):
        try:
            vk = INGVirtKeyboard(self)
        except VirtKeyboardError as err:
            error("Error: %s" % err)
            return
        realpasswd = ""
        span = self.doc.find('//span[@id="digitpadtransfer"]')
        i = 0
        for font in span.getiterator('font'):
            if font.attrib.get('class') == "vide":
                realpasswd += password[i]
            i += 1
        confirmform = None
        divform = self.doc.xpath('//div[@id="transfer_panel"]')[0]
        for form in divform.xpath('./form'):
            try:
                if form.attrib['name'][0:4] == "j_id":
                    confirmform = form
                    break
            except:
                continue
        if confirmform is None:
            raise BrokenPageError('Unable to find confirm form')
        formname = confirmform.attrib['name']
        self.browser.logger.debug('We are looking for : ' + realpasswd)

        form = self.get_form(name=formname)
        for elem in form:
            if "_link_hidden_" in elem or "j_idcl" in elem:
                form.pop(elem)

        coordinates = vk.get_string_code(realpasswd)
        self.browser.logger.debug("Coordonates: " + coordinates)

        form['AJAXREQUEST'] = '_viewRoot'
        form['%s:mrgtransfer' % formname] = '%s:mrgtransfer' % formname
        form['%s:mrltransfer' % formname] = coordinates
        form.submit()

    def recap(self):
        if len(self.doc.xpath('//p[@class="alert alert-success"]')) == 0:
            raise BrokenPageError('Unable to find confirmation')
        div = self.doc.find(
                '//div[@class="encadre transfert-validation"]')
        transfer = Transfer(0)
        transfer.amount = Decimal(FrenchTransaction.clean_amount(
            div.xpath('.//label[@id="confirmtransferAmount"]')[0].text))
        transfer.origin = div.xpath(
                './/span[@id="confirmfromAccount"]')[0].text
        transfer.recipient = div.xpath(
                './/span[@id="confirmtoAccount"]')[0].text
        transfer.reason = unicode(
                div.xpath('.//span[@id="confirmtransferMotive"]')[0].text)
        return transfer
