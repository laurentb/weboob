# -*- coding: utf-8 -*-

# Copyright(C) 2016      James GALT
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import re
from datetime import datetime

from weboob.browser.elements import ItemElement, method, DictElement
from weboob.browser.filters.standard import (
    CleanDecimal, Date, Field, CleanText,
    Env, Eval, Map, Regexp, Title,
)
from weboob.browser.filters.html import Attr
from weboob.browser.filters.json import Dict
from weboob.browser.pages import LoggedPage, JsonPage, HTMLPage
from weboob.capabilities.bank import Account, Investment, Transaction
from weboob.capabilities.base import NotAvailable
from weboob.exceptions import NoAccountsException
from weboob.tools.capabilities.bank.investments import IsinCode, IsinType


class LoginPage(JsonPage):
    def get_token(self):
        return Dict('token')(self.doc)


ACCOUNT_TYPES = {
    'PEE': Account.TYPE_PEE,
    'PEG': Account.TYPE_PEE,
    'PEI': Account.TYPE_PEE,
    'PERCO': Account.TYPE_PERCO,
    'PERCOI': Account.TYPE_PERCO,
    'RSP': Account.TYPE_RSP,
    'ART 83': Account.TYPE_ARTICLE_83,
}

class AccountsPage(LoggedPage, JsonPage):
    def get_company_name(self):
        json_list = Dict('listPositionsSalarieFondsDto')(self.doc)
        if json_list:
            return json_list[0].get('nomEntreprise', NotAvailable)
        return NotAvailable

    @method
    class iter_accounts(DictElement):
        def parse(self, el):
            if not el.get('count', 42):
                raise NoAccountsException()

        item_xpath = "listPositionsSalarieFondsDto/*/positionsSalarieDispositifDto"

        class item(ItemElement):
            klass = Account

            obj_id = CleanText(Dict('codeDispositif'))
            obj_balance = CleanDecimal(Dict('mtBrut'))

            def obj_number(self):
                # just the id is a kind of company id so it can be unique on a backend but not unique on multiple backends
                return '%s_%s' % (Field('id')(self), self.page.browser.username)

            obj_currency = 'EUR'
            obj_type = Map(Dict('typeDispositif'), ACCOUNT_TYPES, Account.TYPE_LIFE_INSURANCE)

            def obj_label(self):
                try:
                    return Dict('libelleDispositif')(self).encode('iso-8859-2').decode('utf8')
                except UnicodeError:
                    try:
                        return Dict('libelleDispositif')(self).encode('latin1').decode('utf8')
                    except UnicodeError:
                        return Dict('libelleDispositif')(self)

    @method
    class iter_investments(DictElement):
        def find_elements(self):
            for psds in Dict('listPositionsSalarieFondsDto')(self):
                for psd in psds.get('positionsSalarieDispositifDto'):
                    if psd.get('codeDispositif') == Env('account_id')(self):
                        return psd.get('positionsSalarieFondsDto')
            return {}

        class item(ItemElement):
            klass = Investment

            def condition(self):
                # Some additional invests are present in the JSON but are not
                # displayed on the website, besides they have no valuation,
                # so we check the 'valuation' key before parsing them
                return Dict('mtBrut', default=None)(self)

            obj_label = Dict('libelleFonds')
            obj_unitvalue = Dict('vl') & CleanDecimal
            obj_quantity = Dict('nbParts') & CleanDecimal
            obj_valuation = Dict('mtBrut') & CleanDecimal
            obj_vdate = Date(Dict('dtVl'))
            obj__details_url = Dict('urlFicheFonds', default=None)
            obj_code = IsinCode(Dict('codeIsin', default=NotAvailable), default=NotAvailable)
            obj_code_type = IsinType(Dict('codeIsin', default=NotAvailable))

            def obj_srri(self):
                srri = Dict('SRRI')(self)
                # The website displays '0 - Non disponible' when not available
                if srri.startswith('0'):
                    return NotAvailable
                return int(srri)

            def obj_performance_history(self):
                # The Amundi JSON only contains 1 year and 5 years performances.
                # It seems that when a value is unavailable, they display '0.0' instead...
                perfs = {}
                if Dict('performanceUnAn', default=None)(self) not in (0.0, None):
                    perfs[1] = Eval(lambda x: x / 100, CleanDecimal(Dict('performanceUnAn')))(self)
                if Dict('performanceCinqAns', default=None)(self) not in (0.0, None):
                    perfs[5] = Eval(lambda x: x / 100, CleanDecimal(Dict('performanceCinqAns')))(self)
                return perfs


class AccountHistoryPage(LoggedPage, JsonPage):
    def belongs(self, instructions, account):
        for ins in instructions:
            if 'nomDispositif' in ins and 'codeDispositif' in ins and '%s%s' % (
                ins['nomDispositif'], ins['codeDispositif']) == '%s%s' % (account.label, account.id):
                return True
        return False

    def get_amount(self, instructions, account):
        amount = 0

        for ins in instructions:
            if ('nomDispositif' in ins and 'montantNet' in ins and 'codeDispositif' in ins
                and '%s%s' % (ins['nomDispositif'], ins['codeDispositif'])
                    == '%s%s' % (account.label, account.id)):
                if ins['type'] == 'RACH_TIT':
                    amount -= ins['montantNet']
                else:
                    amount += ins['montantNet']

        return CleanDecimal().filter(amount)

    def iter_history(self, account):
        for hist in self.doc['operationsIndividuelles']:
            if len(hist['instructions']) > 0:
                if self.belongs(hist['instructions'], account):
                    tr = Transaction()
                    tr.amount = self.get_amount(hist['instructions'], account)
                    tr.rdate = datetime.strptime(hist['dateComptabilisation'].split('T')[0], '%Y-%m-%d')
                    tr.date = tr.rdate
                    tr.label = hist.get('libelleOperation') or hist['libelleCommunication']
                    tr.type = Transaction.TYPE_UNKNOWN
                    yield tr


class AmundiInvestmentsPage(LoggedPage, HTMLPage):
    def get_asset_category(self):
        # Descriptions are like 'Fonds d'Investissement - (ISIN: FR001018 - Action'
        # Fetch the last words of the description (e.g. 'Action' or 'Diversifié')
        return Regexp(
            CleanText('//div[@class="amundi-fund-legend"]//strong'),
            r' ([^-]+)$',
            default=NotAvailable
        )(self.doc)


class EEInvestmentPage(LoggedPage, HTMLPage):
    def get_recommended_period(self):
        return Title(CleanText('//label[contains(text(), "Durée minimum de placement")]/following-sibling::span', default=NotAvailable))(self.doc)

    def get_details_url(self):
        return Attr('//a[contains(text(), "Caractéristiques")]', 'data-href', default=None)(self.doc)

    def get_performance_url(self):
        return Attr('//a[contains(text(), "Performances")]', 'data-href', default=None)(self.doc)


class EEInvestmentPerformancePage(LoggedPage, HTMLPage):
    def get_performance_history(self):
        perfs = {}
        if CleanDecimal.French('//tr[td[text()="Fonds"]]//td[position()=last()-2]', default=None)(self.doc):
            perfs[1] = Eval(lambda x: x / 100, CleanDecimal.French('//tr[td[text()="Fonds"]]//td[position()=last()-2]'))(self.doc)
        if CleanDecimal.French('//tr[td[text()="Fonds"]]//td[position()=last()-1]', default=None)(self.doc):
            perfs[3] = Eval(lambda x: x / 100, CleanDecimal.French('//tr[td[text()="Fonds"]]//td[position()=last()-1]'))(self.doc)
        if CleanDecimal.French('//tr[td[text()="Fonds"]]//td[position()=last()]', default=None)(self.doc):
            perfs[5] = Eval(lambda x: x / 100, CleanDecimal.French('//tr[td[text()="Fonds"]]//td[position()=last()]'))(self.doc)
        return perfs


class EEInvestmentDetailPage(LoggedPage, HTMLPage):
    def get_asset_category(self):
        return CleanText('//label[contains(text(), "Classe d\'actifs")]/following-sibling::span', default=NotAvailable)(self.doc)


class EEProductInvestmentPage(LoggedPage, HTMLPage):
    @method
    class fill_investment(ItemElement):
        obj_asset_category = CleanText('//span[contains(text(), "Classe")]/following-sibling::span[@class="valeur"][1]')
        obj_recommended_period = CleanText('//span[contains(text(), "Durée minimum")]/following-sibling::span[@class="valeur"][1]')


class AllianzInvestmentPage(LoggedPage, HTMLPage):
    def get_asset_category(self):
        # The format may be a very short description, or be
        # included between quotation marks within a paragraph
        asset_category = CleanText('//div[contains(@class, "fund-summary")]//h3/following-sibling::div', default=NotAvailable)(self.doc)
        m = re.search(r'« (.*) »', asset_category)
        if m:
            return m.group(1)
        return asset_category


class EresInvestmentPage(LoggedPage, HTMLPage):
    @method
    class fill_investment(ItemElement):
        obj_asset_category = CleanText('//li[span[contains(text(), "Classification")]]', children=False, default=NotAvailable)
        obj_recommended_period = CleanText('//li[span[contains(text(), "Durée")]]', children=False, default=NotAvailable)

        def obj_performance_history(self):
            perfs = {}
            if CleanDecimal.French('(//tr[th[text()="1 an"]]/td[1])[1]', default=None)(self):
                perfs[1] = Eval(lambda x: x / 100, CleanDecimal.French('(//tr[th[text()="1 an"]]/td[1])[1]'))(self)
            if CleanDecimal.French('(//tr[th[text()="3 ans"]]/td[1])[1]', default=None)(self):
                perfs[3] = Eval(lambda x: x / 100, CleanDecimal.French('(//tr[th[text()="3 ans"]]/td[1])[1]'))(self)
            if CleanDecimal.French('(//tr[th[text()="5 ans"]]/td[1])[1]', default=None)(self):
                perfs[5] = Eval(lambda x: x / 100, CleanDecimal.French('(//tr[th[text()="5 ans"]]/td[1])[1]'))(self)
            return perfs


class CprInvestmentPage(LoggedPage, HTMLPage):
    @method
    class fill_investment(ItemElement):
        obj_srri = CleanText('//span[@class="active"]', default=NotAvailable)
        obj_asset_category = CleanText('//div[contains(text(), "Classe d\'actifs")]//strong', default=NotAvailable)
        obj_recommended_period = CleanText('//div[contains(text(), "Durée recommandée")]//strong', default=NotAvailable)


class BNPInvestmentPage(LoggedPage, HTMLPage):
    def get_fund_id(self):
        return Regexp(
            CleanText('//script[contains(text(), "GLB_ProductId")]'),
            r'GLB_ProductId = "(\w+)',
            default=None
        )(self.doc)


class BNPInvestmentApiPage(LoggedPage, JsonPage):
    @method
    class fill_investment(ItemElement):
        obj_asset_category = Dict('Classification', default=NotAvailable)
        obj_recommended_period = Dict('DureePlacement', default=NotAvailable)


class AxaInvestmentPage(LoggedPage, HTMLPage):
    def get_asset_category(self):
        return Title(CleanText('//th[contains(text(), "Classe")]/following-sibling::td'))(self.doc)


class EpsensInvestmentPage(LoggedPage, HTMLPage):
    @method
    class fill_investment(ItemElement):
        obj_asset_category = CleanText('//div[div[span[contains(text(), "Classification")]]]/div[2]/span', default=NotAvailable)
        obj_recommended_period = CleanText('//div[div[span[contains(text(), "Durée de placement")]]]/div[2]/span', default=NotAvailable)


class EcofiInvestmentPage(LoggedPage, HTMLPage):
    @method
    class fill_investment(ItemElement):
        # Recommended period is actually an image so we extract the
        # information from its URL such as '/Horizon/Horizon_5_ans.png'
        obj_recommended_period = Regexp(
            CleanText(Attr('//img[contains(@src, "/Horizon/")]', 'src', default=NotAvailable), replace=[(u'_', ' ')]),
            r'\/Horizon (.*)\.png'
        )
        obj_asset_category = CleanText('//div[contains(text(), "Classification")]/following-sibling::div[1]', default=NotAvailable)


class SGGestionInvestmentPage(LoggedPage, HTMLPage):
    @method
    class fill_investment(ItemElement):
        obj_asset_category = CleanText('//label[contains(text(), "Classe d\'actifs")]/following-sibling::span', default=NotAvailable)
        obj_recommended_period = CleanText('//label[contains(text(), "Durée minimum")]/following-sibling::span', default=NotAvailable)

    def get_performance_url(self):
        return Attr('(//li[@role="presentation"])[1]//a', 'data-href', default=None)(self.doc)


class SGGestionPerformancePage(EEInvestmentPerformancePage):
    pass
