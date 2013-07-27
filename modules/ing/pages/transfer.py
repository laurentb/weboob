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
from weboob.tools.browser import BasePage, BrokenPageError
from weboob.tools.mech import ClientForm
from .login import INGVirtKeyboard
from logging import error

__all__ = ['TransferPage']


class TransferPage(BasePage):
    def on_loaded(self):
        pass

    def get_recipients(self):
        # First, internals recipients
        table = self.document.xpath('//table[@id="transfer_form:receiptAccount"]')
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
        select = self.document.xpath('//select[@id="transfer_form:externalAccounts"]')
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
        option = self.document.xpath('//input[@value="%s"]' % id)
        if len(option) == 0:
            raise AccountNotFound()
        else:
            option = option[0]
        try:
            if option.attrib["checked"] == "checked":
                return True
            else:
                return False
        except:
            return False

    def transfer(self, recipient, amount, reason):
        self.browser.select_form("transfer_form")
        self.browser.set_all_readonly(False)
        for a in self.browser.controls[:]:
            #for label in a.get_labels():
            if "transfer_form:_link_hidden_" in str(a) or "transfer_form:j_idcl" in str(a):
                self.browser.controls.remove(a)
            if "transfer_form:valide" in str(a):
                self.browser.controls.remove(a)
        self.browser.controls.append(ClientForm.TextControl('text',
            'AJAXREQUEST', {'value': "_viewRoot"}))
        self.browser.controls.append(ClientForm.TextControl('text',
            'AJAX:EVENTS_COUNT', {'value': "1"}))
        self.browser['transfer_form:transferMotive'] = reason.encode('ISO-8859-1')
        self.browser.controls.append(ClientForm.TextControl('text', 'transfer_form:valide', {'value': "transfer_form:valide"}))
        self.browser['transfer_form:validateDoTransfer'] = "needed"
        self.browser['transfer_form:transferAmount'] = str(amount)
        if recipient._type == "int":
            self.browser['transfer_recipient_radio'] = [recipient.id]
        else:
            self.browser['transfer_form:externalAccounts'] = [recipient.id]
        self.browser.submit()

    def buildonclick(self, recipient, account):
        javax = self.document.xpath('//input[@id="javax.faces.ViewState"]')[0].attrib['value']
        if recipient._type == "ext":
            select = self.document.xpath('//select[@id="transfer_form:externalAccounts"]')[0]
            onclick = select.attrib['onchange']
            params = onclick.split(',')[3].split('{')[1]
            idparam = params.split("'")[1]
            param = params.split("'")[3]
            request = self.browser.buildurl('', ("AJAXREQUEST", "transfer_form:transfer_radios_form"),
                                            ("transfer_form:generalMessages", ""),
                                            ("transfer_issuer_radio", account.id[3:]),
                                            ("transfer_form:externalAccounts", recipient.id),
                                            ("transfer_date", 0),
                                            ("transfer_form:transferAmount", ""),
                                            ("transfer_form:transferMotive", ""),
                                            ("transfer_form:validateDoTransfer", "needed"),
                                            ("transfer_form", "transfer_form"),
                                            ("autoScrol", ""),
                                            ("javax.faces.ViewState", javax),
                                            (idparam, param))
            request = request[1:]  # remove the "?"
            return request
        elif recipient._type == "int":
            for input in self.document.xpath('//input[@value=%s]' % recipient.id):
                if input.attrib['name'] == "transfer_recipient_radio":
                    onclick = input.attrib['onclick']
                    break
            # Get something like transfer_form:issueAccount:0:click
            params = onclick.split(',')[3].split('{')[1]
            idparam = params.split("'")[1]
            param = params.split("'")[3]
            request = self.browser.buildurl('', ("AJAXREQUEST", "transfer_form:transfer_radios_form"),
                                      ('transfer_issuer_radio', account.id[3:]),
                                      ("transfer_recipient_radio", recipient.id),
                                      ("transfer_form:externalAccounts", "na"),
                                      ("transfer_date", 0),
                                      ("transfer_form:transferAmount", ""),
                                      ("transfer_form:transferMotive", ""),
                                      ("transfer_form:validateDoTransfer", "needed"),
                                      ("transfer_form", "transfer_form"),
                                      ("autoScroll", ""),
                                      ("javax.faces.ViewState", javax),
                                      (idparam, param))
            request = request[1:]
            return request


class TransferConfirmPage(BasePage):
    def on_loaded(self):
        pass

    def confirm(self, password):
        try:
            vk = INGVirtKeyboard(self)
        except VirtKeyboardError as err:
            error("Error: %s" % err)
            return
        realpasswd = ""
        span = self.document.find('//span[@id="digitpadtransfer"]')
        i = 0
        for font in span.getiterator('font'):
            if font.attrib.get('class') == "vide":
                realpasswd += password[i]
            i += 1
        confirmform = None
        for form in self.document.xpath('//form'):
            try:
                if form.attrib['name'][0:4] == "j_id" and 'enctype' not in form.attrib:
                    confirmform = form
                    break
            except:
                continue
        if confirmform is None:
            raise BrokenPageError('Unable to find confirm form')
        formname = confirmform.attrib['name']
        self.browser.logger.debug('We are looking for : ' + realpasswd)
        self.browser.select_form(formname)
        self.browser.set_all_readonly(False)
        for a in self.browser.controls[:]:
            if "_link_hidden_" in str(a) or "j_idcl" in str(a):
                self.browser.controls.remove(a)
        coordinates = vk.get_string_code(realpasswd)
        self.browser.logger.debug("Coordonates: " + coordinates)

        self.browser.controls.append(ClientForm.TextControl('text',
            'AJAXREQUEST', {'value': '_viewRoot'}))
        self.browser.controls.append(ClientForm.TextControl(
            'text', '%s:mrgtransfer' % formname,
            {'value': '%s:mrgtransfer' % formname}))
        self.browser['%s:mrltransfer' % formname] = coordinates
        self.browser.submit(nologin=True)

    def recap(self):
        if len(self.document.xpath('//p[@class="alert alert-success"]')) == 0:
            raise BrokenPageError('Unable to find confirmation')
        div = self.document.find(
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
