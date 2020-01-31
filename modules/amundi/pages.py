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
    Env, Eval, Map, Regexp, Title, Format,
)
from weboob.browser.filters.html import Attr
from weboob.browser.filters.json import Dict
from weboob.browser.pages import LoggedPage, JsonPage, HTMLPage
from weboob.capabilities.bank import Account, Investment, Transaction, Pocket
from weboob.capabilities.base import NotAvailable, empty
from weboob.exceptions import NoAccountsException
from weboob.tools.capabilities.bank.investments import IsinCode, IsinType


def percent_to_ratio(value):
    if empty(value):
        return NotAvailable
    return value / 100


class LoginPage(JsonPage):
    def get_token(self):
        return Dict('token')(self.doc)


ACCOUNT_TYPES = {
    'PEE': Account.TYPE_PEE,
    'PEG': Account.TYPE_PEE,
    'PEI': Account.TYPE_PEE,
    'PERCO': Account.TYPE_PER,
    'PERCOI': Account.TYPE_PER,
    'PER': Account.TYPE_PER,
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
            obj_currency = 'EUR'
            obj_type = Map(Dict('typeDispositif'), ACCOUNT_TYPES, Account.TYPE_LIFE_INSURANCE)

            def obj_number(self):
                # just the id is a kind of company id so it can be unique on a backend but not unique on multiple backends
                return '%s_%s' % (Field('id')(self), self.page.browser.username)

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

            def obj_diff(self):
                diff = CleanDecimal.SI(Dict('mtPMV', default=None), default=NotAvailable)(self)
                # Some invests have no diff value but the website fills the json field with the valuation.
                if diff == Field('valuation')(self):
                    return NotAvailable
                return diff

            def obj_portfolio_share(self):
                portfolio_share_percent = CleanDecimal.SI(Dict('pourcentageSupport', default=None), default=None)(self)
                if portfolio_share_percent is None:
                    return NotAvailable
                return portfolio_share_percent / 100

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

            # Fetch pockets for each investment:
            class obj__pockets(DictElement):
                item_xpath = 'positionSalarieFondsEchDto'

                class item(ItemElement):
                    klass = Pocket

                    obj_condition = Env('condition')
                    obj_availability_date = Env('availability_date')
                    obj_amount = CleanDecimal.SI(Dict('mtBrut'))
                    obj_quantity = CleanDecimal.SI(Dict('nbParts'))

                    def parse(self, obj):
                        availability_date = datetime.strptime(obj['dtEcheance'].split('T')[0], '%Y-%m-%d')
                        if availability_date <= datetime.today():
                            # In the past, already available
                            self.env['availability_date'] = availability_date
                            self.env['condition'] = Pocket.CONDITION_AVAILABLE
                        else:
                            # In the future, but we have no information on condition
                            self.env['availability_date'] = availability_date
                            self.env['condition'] = Pocket.CONDITION_UNKNOWN


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
    def get_tab_url(self, tab_id):
        return Format(
            '%s%d',
            Regexp(CleanText('//script[contains(text(), "Product.init")]'), r'init\(.*?,"(.*?tab_)\d"', default=None),
            tab_id
        )(self.doc)

    def get_details_url(self):
        return self.get_tab_url(5)

    def get_performance_url(self):
        return self.get_tab_url(2)


class EEInvestmentPage(LoggedPage, HTMLPage):
    def get_recommended_period(self):
        return Title(CleanText('//label[contains(text(), "Durée minimum de placement")]/following-sibling::span', default=NotAvailable))(self.doc)

    def get_details_url(self):
        return Attr('//a[contains(text(), "Caractéristiques")]', 'data-href', default=None)(self.doc)

    def get_performance_url(self):
        return Attr('//a[contains(text(), "Performances")]', 'data-href', default=None)(self.doc)


class InvestmentPerformancePage(LoggedPage, HTMLPage):
    def get_performance_history(self):
        # The positions of the columns depend on the age of the investment fund.
        # For example, if the fund is younger than 5 years, there will be not '5 ans' column.
        durations = [CleanText('.')(el) for el in self.doc.xpath('//div[h2[contains(text(), "Performances glissantes")]]//th')]
        values = [CleanText('.')(el) for el in self.doc.xpath('//div[h2[contains(text(), "Performances glissantes")]]//tr[td[text()="Fonds"]]//td')]
        matches = dict(zip(durations, values))
        # We do not fill the performance dictionary if no performance is available,
        # otherwise it will overwrite the data obtained from the JSON with empty values.
        perfs = {}
        if matches.get('1 an'):
            perfs[1] = percent_to_ratio(CleanDecimal.French(default=NotAvailable).filter(matches['1 an']))
        if matches.get('3 ans'):
            perfs[3] = percent_to_ratio(CleanDecimal.French(default=NotAvailable).filter(matches['3 ans']))
        if matches.get('5 ans'):
            perfs[5] = percent_to_ratio(CleanDecimal.French(default=NotAvailable).filter(matches['5 ans']))
        return perfs


class InvestmentDetailPage(LoggedPage, HTMLPage):
    def get_recommended_period(self):
        return Title(CleanText('//label[contains(text(), "Durée minimum de placement")]/following-sibling::span', default=NotAvailable))(self.doc)

    def get_asset_category(self):
        return CleanText('(//label[contains(text(), "Classe d\'actifs")])[1]/following-sibling::span', default=NotAvailable)(self.doc)


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
        # Text headers can be in French or in English
        obj_asset_category = Title('//div[contains(text(), "Classe d\'actifs") or contains(text(), "Asset class")]//strong', default=NotAvailable)
        obj_recommended_period = Title('//div[contains(text(), "Durée recommandée") or contains(text(), "Recommended duration")]//strong', default=NotAvailable)


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


class SGGestionPerformancePage(InvestmentPerformancePage):
    pass
