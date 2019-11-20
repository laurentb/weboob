# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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

import requests
from io import BytesIO
from decimal import Decimal
from lxml import objectify

from weboob.browser.pages import HTMLPage, XMLPage, RawPage, LoggedPage, pagination, FormNotFound, PartialHTMLPage, JsonPage
from weboob.browser.elements import ItemElement, TableElement, SkipItem, method
from weboob.browser.filters.standard import CleanText, Date, Regexp, Eval, CleanDecimal, Env, Field, MapIn, Upper
from weboob.browser.filters.html import Attr, TableCell
from weboob.browser.filters.json import Dict
from weboob.browser.exceptions import HTTPNotFound
from weboob.capabilities.bank import Account, Investment, Pocket, Transaction
from weboob.capabilities.base import NotAvailable, empty
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard
from weboob.exceptions import BrowserUnavailable, ActionNeeded, BrowserQuestion, BrowserIncorrectPassword
from weboob.tools.value import Value
from weboob.tools.compat import urljoin
from weboob.tools.capabilities.bank.investments import is_isin_valid


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


def percent_to_ratio(value):
    if empty(value):
        return NotAvailable
    return value / 100


class ErrorPage(HTMLPage):
    def on_load(self):
        raise BrowserUnavailable()


class S2eVirtKeyboard(MappedVirtKeyboard):
    symbols = {'0':('8adee734aaefb163fb008d26bb9b3a42', '922d79345bf824b1186d0aa523b37a7c'),
               '1':('b815d6ce999910d48619b5912b81ddf1', '4730473dcd86f205dff51c59c97cf8c0'),
               '2':('54255a70694787a4e1bd7dd473b50228', '2d8b1ab0b5ce0b88abbc0170d2e85b7e'),
               '3':('ba06373d2bfba937d00bf52a31d475eb', '08e7e7ab7b330f3cfcb819b95eba64c6'),
               '4':('3fa795ac70247922048c514115487b10', 'ffb3d035a3a335cfe32c59d8ee1302ad'),
               '5':('788963d15fa05832ee7640f7c2a21bc3', 'c4b12545020cf87223901b6b35b9a9e2'),
               '6':('c8bf62dfaed9feeb86934d8617182503', '473357666949855a0794f68f3fc40127'),
               '7':('f7543fdda3039bdd383531954dd4fc46', '5f3a71bd2f696b8dc835dfeb7f32f92a'),
               '8':('5c4210e2d8e39f7667d7a9e5534b18b7', 'b9a1a73430f724541108ed5dd862431b'),
               '9':('94520ac801883fbfb700f43cd4172d41', '12c18ca3d4350acd077f557ac74161e5'),
              }

    color = (0, 0, 0)

    def __init__(self, page, vkid):
        img = page.doc.find('//img[@id="clavier_virtuel"]')
        res = page.browser.open("/portal/rest/clavier_virtuel/%s" % vkid)
        MappedVirtKeyboard.__init__(self, BytesIO(res.content), page.doc, img, self.color, convert='RGB')
        self.check_symbols(self.symbols, None)

    def get_symbol_code(self, md5sum):
        code = MappedVirtKeyboard.get_symbol_code(self, md5sum)
        m = re.search('(\d+)', code)
        if m:
            return m.group(1)

    def get_string_code(self, string):
        return ''.join([self.get_symbol_code(self.symbols[c]) for c in string])


class BrowserIncorrectAuthenticationCode(BrowserIncorrectPassword):
    pass


class LoginErrorPage(PartialHTMLPage):
    pass


class LoginPage(HTMLPage):
    def get_password(self, password, secret):
        vkid = Attr('//input[@id="identifiantClavierVirtuel"]', 'value')(self.doc)
        code = S2eVirtKeyboard(self, vkid).get_string_code(password)
        tcc = Attr('//input[@id="codeTCC"]', 'value')(self.doc)
        password = "%s|%s|#%s#" % (code, vkid, tcc)
        if secret:
            password = "%s%s" % (password, secret)
        return password

    def login(self, login, password, secret):
        form = self.get_form(id="formulaireEnvoi")
        device_print = '''{"screen":{"screenWidth":500,"screenHeight":500,"screenColourDepth":24},"timezone":{"timezone":-60},"plugins":{"installedPlugins":""},"fonts":{"installedFonts":"cursive;monospace;serif;sans-serif;fantasy;default;Arial;Courier;Courier New;Gentium;Times;Times New Roman;"},"userAgent":"Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Mobile Safari/537.36","appName":"Netscape","appCodeName":"Mozilla","appVersion":"5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Mobile Safari/537.36","platform":"Linux x86_64","product":"Gecko","productSub":"20030107","vendor":"Google Inc.","language":"en-US"}'''
        form['password'] = self.get_password(password, secret) + device_print
        form['username'] = login
        form['devicePrint'] = device_print
        form.submit()

    def get_error(self):
        cgu = CleanText('//h1[contains(text(), "Conditions")]', default=None)(self.doc)
        if cgu:
            cgu = "Veuillez accepter les conditions générales d'utilisation." if self.browser.LANG == "fr" \
               else "Please accept the general conditions of use." if self.browser.LANG == 'en' \
               else cgu
        return cgu or CleanText('//div[contains(text(), "Erreur")]', default='')(self.doc)

    def send_otp(self, otp):
        try:
            form = self.get_form(xpath='//form[.//div[has-class("authentification-bloc-content-btn-bloc")]]',
                                submit='//div[has-class("authentification-bloc-content-btn-bloc")]//input[@type="submit"]')
        except FormNotFound:
            form = self.get_form(xpath='//form[.//div[contains(@class, "otp")]]')
            input_validate = (Attr('//a[.//span[contains(text(), "VALIDATE")]]', 'onclick', default=None)(self.doc) or
                              Attr('//a[.//span[contains(text(), "VALIDER")]]', 'onclick', default=None)(self.doc) or
                              Attr('//a[.//span[contains(text(), "Confirm")]]', 'onclick')(self.doc))
            m = re.search(r"{\\'([^\\]+)\\':\\'([^\\]+)\\'}", input_validate)
            form[m.group(1)] = m.group(2)
            form.pop('pb12876:j_idt3:j_idt158:j_idt159:j_idt244:j_idt273', None)

        for k in form:
            if 'need help' in form[k].lower():
                del form[k]
                break

        input_otp = Attr('//input[contains(@id, "otp")]', 'id')(self.doc)
        input_id = Attr('//input[@type="checkbox"]', 'id')(self.doc)
        form[input_otp] = otp
        form[input_id] = 'on'
        form.submit()

    def check_error(self):
        if bool(self.doc.xpath('//span[@class="operation-bloc-content-message-erreur-text"][contains(text(), "est incorrect")]')) or \
           bool(self.doc.xpath('//span[@class="operation-bloc-content-message-erreur-text"][contains(text(), "is incorrect")]')):
            raise BrowserIncorrectAuthenticationCode('Invalid OTP')
        elif bool(self.doc.xpath('//span[@class="operation-bloc-content-message-erreur-text"][contains(text(), "Technical error")]')):
            raise BrowserUnavailable()

    def on_load(self):
        receive_code_btn = bool(self.doc.xpath('//div[has-class("authentification-bloc-content-btn-bloc")][count(input)=1]'))
        submit_input = self.doc.xpath('//input[@type="submit"]')
        if receive_code_btn and len(submit_input) == 1:
            form = self.get_form(xpath='//form[.//div[has-class("authentification-bloc-content-btn-bloc")][count(input)=1]]',
                                 submit='//div[has-class("authentification-bloc-content-btn-bloc")]//input[@type="submit"]')

            # sending mail with code
            form.submit()
            raise BrowserQuestion(Value('otp', label=u'Veuillez saisir votre code de sécurité (reçu par mail ou par sms)'))

        send_code_form = bool(self.doc.xpath('//form[.//div[has-class("authentification-bloc-content-btn-bloc")]]'))
        # TODO move this code in browser
        otp = self.browser.config['otp'].get() if 'otp' in self.browser.config else None
        if send_code_form and otp:
            self.check_error()
            self.send_otp(otp)


class LandingPage(LoggedPage, HTMLPage):
    pass


class CodePage(object):
    '''
    This class is used as a parent class to include
    all classes that contain a get_code() method.
    '''
    pass


# AMF codes
class AMFHSBCPage(XMLPage, CodePage):
    ENCODING = "UTF-8"
    CODE_TYPE = Investment.CODE_TYPE_AMF

    def build_doc(self, content):
        doc = super(AMFHSBCPage, self).build_doc(content).getroot()
        # Remove namespaces
        for el in doc.getiterator():
            if not hasattr(el.tag, 'find'):
                continue
            i = el.tag.find('}')
            if i >= 0:
                el.tag = el.tag[i+1:]
        objectify.deannotate(doc, cleanup_namespaces=True)
        return doc

    def get_code(self):
        return CleanText('//AMF_Code', default=NotAvailable)(self.doc)


class AMFAmundiPage(HTMLPage, CodePage):
    CODE_TYPE = Investment.CODE_TYPE_AMF

    def get_code(self):
        return Regexp(CleanText('//td[@class="bannerColumn"]//li[contains(., "(C)")]', default=NotAvailable),
               r'(\d+)', default=NotAvailable)(self.doc)


class AMFSGPage(LoggedPage, HTMLPage, CodePage):
    CODE_TYPE = Investment.CODE_TYPE_AMF

    def build_doc(self, data):
        if not data.strip():
            # sometimes the page is totally blank... prevent an XMLSyntaxError
            data = b'<html></html>'
        return super(AMFSGPage, self).build_doc(data)

    def get_code(self):
        return Regexp(CleanText('//div[@id="header_code"]'), r'(\d+)', default=NotAvailable)(self.doc)

    def get_investment_performances(self):
        # Fetching the performance history (1 year, 3 years & 5 years)
        perfs = {}
        if not self.doc.xpath('//table[tr[th[contains(text(), "Performances glissantes")]]]'):
            return
        # Available performance durations are: 1 week, 1 month, 1 year, 3 years & 5 years.
        # We need to match the durations with their respective values.
        durations = [CleanText('.')(el) for el in self.doc.xpath('//table[tr[th[contains(text(), "Performances glissantes")]]]//tr[2]//th')]
        values = [CleanText('.')(el) for el in self.doc.xpath('//table[tr[th[contains(text(), "Performances glissantes")]]]//td')]
        matches = dict(zip(durations, values))
        perfs[1] = percent_to_ratio(CleanDecimal.French(default=NotAvailable).filter(matches['1 an *']))
        perfs[3] = percent_to_ratio(CleanDecimal.French(default=NotAvailable).filter(matches['3 ans *']))
        perfs[5] = percent_to_ratio(CleanDecimal.French(default=NotAvailable).filter(matches['5 ans *']))
        return perfs


class LyxorfcpePage(LoggedPage, HTMLPage, CodePage):
    CODE_TYPE = Investment.CODE_TYPE_ISIN

    def get_code(self):
        return Regexp(CleanText('//span[@class="isin"]'), 'Code ISIN : (.*)')(self.doc)


class LyxorFundsPage(LoggedPage, HTMLPage):
    def get_investment_performances(self):
        # Fetching the performance history (1 year, 3 years & 5 years)
        perfs = {}
        if not self.doc.xpath('//table[tr[td[text()="Performance"]]]'):
            return
        # Available performance history: 1 month, 3 months, 6 months, 1 year, 2 years, 3 years, 4years & 5 years.
        # We need to match the durations with their respective values.
        durations = [CleanText('.')(el) for el in self.doc.xpath('//table[tr[td[text()="Performance"]]]//tr//th')]
        values = [CleanText('.')(el) for el in self.doc.xpath('//table[tr[td[text()="Performance"]]]//tr//td')]
        matches = dict(zip(durations, values))
        perfs[1] = percent_to_ratio(CleanDecimal.French(default=NotAvailable).filter(matches['1A']))
        perfs[3] = percent_to_ratio(CleanDecimal.French(default=NotAvailable).filter(matches['3A']))
        perfs[5] = percent_to_ratio(CleanDecimal.French(default=NotAvailable).filter(matches['5A']))
        return perfs


class EcofiPage(LoggedPage, HTMLPage, CodePage):
    CODE_TYPE = Investment.CODE_TYPE_ISIN

    def get_code(self):
        return CleanText('//div[has-class("field-name-CodeISIN")]/div[@class="field-items"]')(self.doc)


class EcofiDummyPage(LoggedPage, RawPage):
    pass


class ItemInvestment(ItemElement):
    klass = Investment

    obj_unitvalue = Env('unitvalue')
    obj_vdate = Env('vdate')
    obj_code = Env('code')
    obj_code_type = Env('code_type')
    obj__link = Env('_link')

    def obj_label(self):
        return CleanText(TableCell('label')(self)[0].xpath('.//div[contains(@style, \
            "text-align")][1]'))(self)

    def obj_valuation(self):
        return MyDecimal(TableCell('valuation')(self)[0].xpath('.//div[not(.//div)]'))(self)

    def parse(self, el):
        # Trying to find vdate and unitvalue
        unitvalue, vdate = None, None
        for span in TableCell('label')(self)[0].xpath('.//span'):
            if unitvalue is None:
                unitvalue = Regexp(CleanText('.'), '^([\d,]+)$', default=None)(span)
            if vdate is None:
                vdate = None if any(x in CleanText('./parent::div')(span) for x in ["échéance", "Maturity"]) else \
                        Regexp(CleanText('.'), '^([\d\/]+)$', default=None)(span)
        self.env['unitvalue'] = MyDecimal().filter(unitvalue) if unitvalue else NotAvailable
        self.env['vdate'] = Date(dayfirst=True).filter(vdate) if vdate else NotAvailable
        self.env['_link'] = None

        page = None
        link_id = Attr(u'.//a[contains(@title, "détail du fonds")]', 'id', default=None)(self)
        inv_id = Attr('.//a[contains(@id, "linkpdf")]', 'id', default=None)(self)

        if link_id and inv_id:
            form = self.page.get_form('//div[@id="operation"]//form')
            form['idFonds'] = inv_id.split('-', 1)[-1]
            form['org.richfaces.ajax.component'] = form[link_id] = link_id
            page = self.page.browser.open(form['javax.faces.encodedURL'], data=dict(form)).page

            if 'hsbc.fr' in self.page.browser.BASEURL:
                # Special space for HSBC, does not contain any information related to performances.
                m = re.search(r'fundid=(\w+).+SH=(\w+)', CleanText('//complete', default='')(page.doc))
                if m: # had to put full url to skip redirections.
                    page = page.browser.open('https://www.assetmanagement.hsbc.com/feedRequest?feed_data=gfcFundData&cod=FR&client=FCPE&fId=%s&SH=%s&lId=fr' % m.groups()).page

            elif not self.page.browser.history.is_here():
                url = page.get_invest_url()

                if empty(url):
                    self.env['code'] = NotAvailable
                    self.env['code_type'] = NotAvailable
                    return

                # URLs used in browser.py to access investments performance history:
                if url.startswith('https://optimisermon.epargne-retraite-entreprises'):
                    # This URL can be used to access the BNP Wealth API to fetch investment performance and ISIN code
                    self.env['_link'] = url
                    self.env['code'] = NotAvailable
                    self.env['code_type'] = NotAvailable
                    return
                elif url.startswith('http://sggestion-ede.com/product') or url.startswith('https://www.lyxorfunds.com/part'):
                    self.env['_link'] = url

                # Try to fetch ISIN code from URL with re.match
                match = re.match(r'http://www.cpr-am.fr/fr/fonds_detail.php\?isin=([A-Z0-9]+)', url)
                match = match or re.match(r'http://www.cpr-am.fr/particuliers/product/view/([A-Z0-9]+)', url)
                if match:
                    self.env['code'] = m.group(1)
                    if is_isin_valid(match.group(1)):
                        self.env['code_type'] = Investment.CODE_TYPE_ISIN
                    else:
                        self.env['code_type'] = Investment.CODE_TYPE_AMF
                    return

                # Try to fetch ISIN code from URL with re.search
                m = re.search(r'&ISIN=([^&]+)', url)
                m = m or re.search(r'&isin=([^&]+)', url)
                m = m or re.search(r'&codeIsin=([^&]+)', url)
                m = m or re.search(r'lyxorfunds\.com/part/([^/]+)', url)
                if m:
                    self.env['code'] = m.group(1)
                    if is_isin_valid(m.group(1)):
                        self.env['code_type'] = Investment.CODE_TYPE_ISIN
                    else:
                        self.env['code_type'] = Investment.CODE_TYPE_AMF
                    return

                useless_urls = (
                    # pdf... http://docfinder.is.bnpparibas-ip.com/api/files/040d05b3-1776-4991-aa49-f0cd8717dab8/1536
                    'http://docfinder.is.bnpparibas-ip.com/',
                    # The AXA website displays performance graphs but everything is calculated using JS scripts.
                    # There is an API but it only contains risk data and performances per year, not 1-3-5 years.
                    'https://epargne-salariale.axa-im.fr/fr/',
                    # Redirection to the Rothschild Gestion website, which doesn't exist anymore...
                    'https://www.rothschildgestion.com',
                    # URL to the Morningstar website does not contain any useful information
                    'http://doc.morningstar.com',
                )
                for useless_url in useless_urls:
                    if url.startswith(useless_url):
                        self.env['code'] = NotAvailable
                        self.env['code_type'] = NotAvailable
                        return

                if url.startswith('http://fr.swisslife-am.com/fr/'):
                    self.page.browser.session.cookies.set('location', 'fr')
                    self.page.browser.session.cookies.set('prof', 'undefined')
                try:
                    page = self.page.browser.open(url).page
                except HTTPNotFound:
                    # Some pages lead to a 404 so we must avoid unnecessary crash
                    self.logger.warning('URL %s was not found, investment details will be skipped.', url)

        if isinstance(page, CodePage):
            self.env['code'] = page.get_code()
            self.env['code_type'] = page.CODE_TYPE
        else:
            # The page is not handled and does not have a get_code method.
            self.env['code'] = NotAvailable
            self.env['code_type'] = NotAvailable


class MultiPage(HTMLPage):
    def get_multi(self):
        return [Attr('.', 'value')(option) for option in \
            self.doc.xpath('//select[@class="ComboEntreprise"]/option')]

    def go_multi(self, id):
        if Attr('//select[@class="ComboEntreprise"]/option[@selected]', 'value')(self.doc) != id:
            form = self.get_form('//select[@class="ComboEntreprise"]/ancestor::form[1]')
            key = [k for k, v in dict(form).items() if "SelectItems" in k][0]
            form[key] = id
            form['javax.faces.source'] = key
            form.submit()


class AccountsPage(LoggedPage, MultiPage):
    def on_load(self):
        if CleanText('//a//span[contains(text(), "J\'ACCEPTE LES CONDITIONS GENERALES D\'UTILISATION") or'
                     '          contains(text(), "I ACCEPT THE GENERAL CONDITIONS OF USE")]')(self.doc):
            raise ActionNeeded("Veuillez valider les conditions générales d'utilisation")

    TYPES = {
        'PEE': Account.TYPE_PEE,
        'PEI': Account.TYPE_PEE,
        'PEEG': Account.TYPE_PEE,
        'PEG': Account.TYPE_PEE,
        'PLAN': Account.TYPE_PEE,
        'PAGA': Account.TYPE_PEE,
        'ABONDEMENT EXCEPTIONNEL': Account.TYPE_PEE,
        'PERCO': Account.TYPE_PERCO,
        'PERCOI': Account.TYPE_PERCO,
        'SWISS': Account.TYPE_MARKET,
        'RSP': Account.TYPE_RSP,
        'CCB': Account.TYPE_DEPOSIT,
        'PARTICIPATION': Account.TYPE_DEPOSIT,
        'PERF': Account.TYPE_PERP,
    }

    CONDITIONS = {
        u'disponible': Pocket.CONDITION_AVAILABLE,
        u'épargne': Pocket.CONDITION_AVAILABLE,
        u'available': Pocket.CONDITION_AVAILABLE,
        u'withdrawal': Pocket.CONDITION_RETIREMENT,
        u'retraite': Pocket.CONDITION_RETIREMENT,
    }

    def get_no_accounts_message(self):
        no_accounts_message = CleanText(
            '//span[contains(text(), "A ce jour, vous ne disposez plus d\'épargne salariale dans cette entreprise.")] | '
            '//span[contains(text(), "On this date, you still have no employee savings in this company.")] | '
            '//span[contains(text(), "On this date, you do not yet have any employee savings in this company.")] | '
            '//span[contains(text(), "On this date, you no longer have any employee savings in this company.")] | '
            '//p[contains(text(), "You no longer have any employee savings.")]'
        )(self.doc)
        return no_accounts_message

    @method
    class iter_accounts(TableElement):
        item_xpath = '//div[contains(@id, "Dispositif")]//table/tbody/tr'
        head_xpath = '//div[contains(@id, "Dispositif")]//table/thead/tr/th'

        col_label = [u'My schemes', u'Mes dispositifs']
        col_balance = [re.compile(u'Total'), re.compile(u'Montant')]

        class item(ItemElement):
            klass = Account

            # the account has to have a color correspondig to the graph
            # if not, it may be a duplicate
            def condition(self):
                return self.xpath('.//div[contains(@class, "mesavoirs-carre-couleur") and contains(@style, "background-color:#")]')

            obj_id = obj_number = Env('id')
            obj_label = Env('label')

            def obj_type(self):
                return MapIn(Upper(Field('label')), self.page.TYPES, Account.TYPE_UNKNOWN)(self)

            def obj_balance(self):
                return MyDecimal(TableCell('balance')(self)[0].xpath('.//div[has-class("nowrap")]'))(self)

            def obj_currency(self):
                return Account.get_currency(CleanText(TableCell('balance')(self)[0].xpath('.//div[has-class("nowrap")]'))(self))

            def parse(self, el):
                id, label = CleanText(TableCell('label'))(self).split(' ', 1)
                self.env['id'] = id
                self.env['label'] = label

    def get_investment_pages(self, accid, valuation=True, pocket=False):
        form = self.get_form('//div[@id="operation"]//form')
        div_xpath = '//div[contains(@id, "%s")]' % ("detailParSupportEtDate" if pocket else "ongletDetailParSupport")
        input_id = Attr('//input[contains(@id, "onglets")]', 'name')(self.doc)
        select_id = Attr('%s//select' % div_xpath, 'id')(self.doc)
        form[select_id] = Attr('//option[contains(text(), "%s")]' % accid, 'value')(self.doc)
        form[input_id] = "onglet4" if pocket else "onglet2"
        # Select display : amount or quantity
        if self.browser.LANG == "fr":
            radio_txt = "En montant" if valuation else ["Quantité", "En parts", "Nombre de parts"]
        else:
            radio_txt = "In amount" if valuation else ["Quantity", "In units", "Number of units"]
        if isinstance(radio_txt, list):
            radio_txt = '" or text()="'.join(radio_txt)
        input_id = Regexp(Attr('%s//span[text()="%s"]/preceding-sibling::a[1]' \
            % (div_xpath, radio_txt), 'onclick'), '"([^"]+)')(self.doc)
        form[input_id] = input_id
        form['javax.faces.source'] = input_id
        if pocket:
            form['visualisationMontant'] = "true" if valuation else "false"
        else:
            form['valorisationMontant'] = "true" if valuation else "false"
        data = {k: v for k, v in dict(form).items() if "blocages" not in v}
        self.browser.location(form.url, data=data)

    @method
    class iter_investment(TableElement):
        item_xpath = '//div[contains(@id, "ongletDetailParSupport")]//table/tbody/tr[td[4]]'
        head_xpath = '//div[contains(@id, "ongletDetailParSupport")]//table/thead/tr/th'

        col_label = [re.compile(u'My investment'), re.compile(u'Mes supports')]
        col_valuation = [re.compile(u'Gross amount'), re.compile(u'Montant brut')]
        col_portfolio_share = [u'Distribution', u'Répartition']
        col_diff = [u'+ or - potential value', u'+ ou - value potentielle']

        class item(ItemInvestment):
            def obj_diff(self):
                td = TableCell('diff', default=None)(self)
                return MyDecimal('.//div[not(.//div)]')(td[0]) if td else NotAvailable

            def obj_portfolio_share(self):
                return Eval(lambda x: x / 100, MyDecimal(TableCell('portfolio_share')(self)[0] \
                    .xpath('.//div[has-class("nowrap")]'))(self))(self)

    def update_invs_quantity(self, invs):
        for inv in invs:
            inv.quantity = MyDecimal().filter(CleanText('//div[contains(@id, "ongletDetailParSupport")] \
                       //tr[.//div[contains(replace(text(), "\xa0", " "), "%s")]]/td[last()]//div/text()' % inv.label)(self.doc))
        return invs

    def get_invest_url(self):
        return Regexp(CleanText('//complete'), r"openUrlFichesFonds\('([^']+)", default=NotAvailable)(self.doc)

    @method
    class iter_pocket(TableElement):
        item_xpath = '//div[contains(@id, "detailParSupportEtDate")]//table/tbody[@class="rf-cst"]/tr[td[4]]'
        head_xpath = '//div[contains(@id, "detailParSupportEtDate")]//table/thead/tr/th'

        col_amount = [re.compile(u'Gross amount'), re.compile(u'Montant brut')]
        col_availability = [u'Availability date', u'Date de disponibilité']

        class item(ItemElement):
            klass = Pocket

            obj_availability_date = Env('availability_date')
            obj_condition = Env('condition')
            obj__matching_txt = Env('matching_txt')

            def obj_amount(self):
                return MyDecimal(TableCell('amount')(self)[0].xpath('.//div[has-class("nowrap")]'))(self)

            def obj_investment(self):
                investment = None
                for inv in self.page.browser.cache['invs'][Env('accid')(self)]:
                    if inv.label in CleanText('./parent::tbody/preceding-sibling::tbody[1]')(self):
                        investment = inv
                assert investment is not None
                return investment

            def obj_label(self):
                return Field('investment')(self).label

            def parse(self, el):
                txt = CleanText(TableCell('availability')(self)[0].xpath('./span'))(self)
                self.env['availability_date'] = Date(dayfirst=True, default=NotAvailable).filter(txt)
                self.env['condition'] = Pocket.CONDITION_DATE if self.env['availability_date'] else \
                                        self.page.CONDITIONS.get(txt.lower().split()[0], Pocket.CONDITION_UNKNOWN)
                self.env['matching_txt'] = txt

    def update_pockets_quantity(self, pockets):
        for pocket in pockets:
            # not so pretty
            pocket.quantity = MyDecimal(CleanText('//div[contains(@id, "detailParSupportEtDate")] \
                //tbody[.//div[contains(replace(text(), "\xa0", " "), "%s")]]/following-sibling::tbody[1]//tr[.//span[contains(text(), \
                "%s")]]/td[last()]//div/text()' % (pocket.investment.label, pocket._matching_txt)))(self.doc)
        return pockets


class HistoryPage(LoggedPage, MultiPage):
    XPATH_FORM = '//div[@id="operation"]//form'

    def get_history_form(self, idt, args={}):
        form = self.get_form(self.XPATH_FORM)
        form[idt] = idt
        form['javax.faces.source'] = idt
        form.update(args)
        return form

    def show_more(self, nb):
        try:
            form = self.get_form(self.XPATH_FORM)
        except FormNotFound:
            return False
        for select in self.doc.xpath('//select'):
            if Attr('./option[@selected]', 'value')(select) == nb:
                return
            idt = Attr('.', 'id')(select)
            form[idt] = nb
            if 'javax.faces.source' not in form:
                form['javax.faces.source'] = idt
        form.submit()
        return True

    def go_start(self):
        idt = Attr('//a[@title="debut" or @title="precedent"]', 'id', default=None)(self.doc)
        if idt:
            form = self.get_history_form(idt)
            form.submit()

    @method
    class get_investments(TableElement):
        item_xpath = '//table//table/tbody/tr[td[4]]'
        head_xpath = '//table//table/thead/tr/th'

        col_scheme = ['Scheme', 'Dispositif']
        col_label = [re.compile('Investment'), re.compile('My investment'), 'fund', re.compile('Support')]
        col_quantity = [re.compile('Quantity'), re.compile('Quantité'), re.compile('En parts'), re.compile('Nombre de parts')]
        col_valuation = ['Gross amount', 'Net amount', re.compile('.*Montant brut'), re.compile('.*Montant [Nn]et')]

        class item(ItemInvestment):
            def obj_quantity(self):
                return MyDecimal(TableCell('quantity')(self)[0].xpath('./text()'))(self)

            def condition(self):
                return Env('accid')(self) in CleanText(TableCell('scheme'))(self)

    @pagination
    @method
    class iter_history(TableElement):
        item_xpath = '//table/tbody/tr[td[4]]'
        head_xpath = '//table/thead/tr/th'

        col_id = [re.compile(u'Ref'), re.compile(u'Réf')]
        col_date = [re.compile(u'Date'), re.compile('Creation date')]
        col_label = [re.compile('Transaction'), re.compile(u'Type')]

        def next_page(self):
            idt = Attr('//a[@title="suivant"]', 'id', default=None)(self.page.doc)
            if idt:
                form = self.page.get_history_form(idt)
                return requests.Request("POST", form.url, data=dict(form))

        class item(ItemElement):
            klass = Transaction

            obj_id = CleanText(TableCell('id'))
            obj_label = CleanText(TableCell('label'))
            obj_type = Transaction.TYPE_BANK
            obj_date = Date(CleanText(TableCell('date')), dayfirst=True)
            obj_amount = Env('amount')
            obj_investments = Env('investments')

            def parse(self, el):
                # We have only one history for all accounts...
                # And we know only on details page if it match current account.
                trid = CleanText(TableCell('id'))(self)
                if trid not in self.page.browser.cache['details']:
                    # Thanks to stateful website : first go on details page...
                    idt = Attr(TableCell('id')(self)[0].xpath('./a'), 'id', default=None)(self)
                    typeop = Regexp(Attr(TableCell('id')(self)[0].xpath('./a'), 'onclick'), 'Operation.+?([A-Z_]+)')(self)
                    form = self.page.get_history_form(idt, {'referenceOp': trid, 'typeOperation': typeop})
                    details_page = self.page.browser.open(form.url, data=dict(form)).page
                    self.page.browser.cache['details'][trid] = details_page
                    # ...then go back to history list.
                    idt = Attr('//input[@title="Retour"]', 'id', default=None)(details_page.doc)
                    form = self.page.get_history_form(idt)
                    self.page.browser.open(form.url, data=dict(form))
                else:
                    details_page = self.page.browser.cache['details'][trid]

                # Check if page is related to the account
                if not len(details_page.doc.xpath('//td[contains(text(), $id)]', id=Env('accid')(self))):
                    raise SkipItem()

                self.env['investments'] = list(details_page.get_investments(accid=Env('accid')(self)))
                self.env['amount'] = sum([i.valuation or Decimal('0') for i in self.env['investments']])


class SwissLifePage(HTMLPage, CodePage):
    CODE_TYPE = Investment.CODE_TYPE_ISIN

    def get_code(self):
        code = CleanText('//span[contains(text(), "Code ISIN")]/following-sibling::span[@class="data"]', default=NotAvailable)(self.doc)
        if code == "n/a":
            return NotAvailable
        return code


class EtoileGestionPage(HTMLPage, CodePage):
    CODE_TYPE = NotAvailable

    def get_code(self):
        # Codes (AMF / ISIN) are available after a click on a tab
        characteristics_url = urljoin(self.url, Attr(u'//a[contains(text(), "Caractéristiques")]', 'data-href', default=None)(self.doc))
        if characteristics_url is not None:
            detail_page = self.browser.open(characteristics_url).page

            # We prefer to return an ISIN code by default
            code_isin = detail_page.get_code_isin()
            if code_isin is not None:
                self.CODE_TYPE = Investment.CODE_TYPE_ISIN
                return code_isin

            # But if it's unavailable we can fallback to an AMF code
            code_amf = detail_page.get_code_amf()
            if code_amf is not None:
                self.CODE_TYPE = Investment.CODE_TYPE_AMF
                return code_amf

        return NotAvailable


class EtoileGestionCharacteristicsPage(PartialHTMLPage):
    def get_code_isin(self):
        code = CleanText('//td[contains(text(), "Code Isin")]/following-sibling::td', default=None)(self.doc)
        return code

    def get_code_amf(self):
        code = CleanText('//td[contains(text(), "Code AMF")]/following-sibling::td', default=None)(self.doc)
        return code


class ProfilePage(LoggedPage, MultiPage):
    def get_company_name(self):
        return CleanText('//div[contains(@class, "operation-bloc")]//span[contains(text(), "Entreprise")]/following-sibling::span[1]')(self.doc)


class APIInvestmentDetailsPage(LoggedPage, JsonPage):
    def get_investment_performances(self):
        # Fetching the performance history (1 year, 3 years & 5 years)
        perfs = {}
        for item in Dict('sharePerf')(self.doc):
            if item['name'] in ('1Y', '3Y', '5Y'):
                duration = int(item['name'][0])
                value = item['value']
                perfs[duration] = Eval(lambda x: x / 100, CleanDecimal.US(value))(self.doc)
        return perfs
