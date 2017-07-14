# -*- coding: utf-8 -*-

# Copyright(C) 2013      Laurent Bachelier
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

from logging import error
import re
from io import BytesIO

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, CleanDecimal, Date, Env
from weboob.browser.filters.html import Attr
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.capabilities.profile import Profile, Person
from weboob.exceptions import ActionNeeded
from weboob.tools.json import json

from weboob.capabilities.base import NotAvailable

from ..captcha import Captcha, TileError


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(r'^CARTE \w+ RETRAIT DAB.* (?P<dd>\d{2})/(?P<mm>\d{2})( (?P<HH>\d+)H(?P<MM>\d+))? (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^CARTE \w+ (?P<dd>\d{2})/(?P<mm>\d{2})( A (?P<HH>\d+)H(?P<MM>\d+))? RETRAIT DAB (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^CARTE \w+ REMBT (?P<dd>\d{2})/(?P<mm>\d{2})( A (?P<HH>\d+)H(?P<MM>\d+))? (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_PAYBACK),
                (re.compile(r'^DEBIT MENSUEL CARTE.*'),
                                                            FrenchTransaction.TYPE_CARD_SUMMARY),
                (re.compile(r'^(?P<category>CARTE) \w+ (?P<dd>\d{2})/(?P<mm>\d{2}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile(r'^(?P<dd>\d{2})(?P<mm>\d{2})/(?P<text>.*?)/?(-[\d,]+)?$'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile(r'^REMISE CB /(?P<dd>\d{2})/(?P<mm>\d{2}) (?P<text>.*?)/?(-[\d,]+)?$'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile(r'^(?P<category>(COTISATION|PRELEVEMENT|TELEREGLEMENT|TIP|PRLV)) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile(r'^(\d+ )?VIR (PERM )?POUR: (.*?) (REF: \d+ )?MOTIF: (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile(r'^(?P<category>VIR(EMEN)?T? \w+) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile(r'^(CHEQUE) (?P<text>.*)'),     FrenchTransaction.TYPE_CHECK),
                (re.compile(r'^(FRAIS) (?P<text>.*)'),      FrenchTransaction.TYPE_BANK),
                (re.compile(r'^(?P<category>ECHEANCEPRET)(?P<text>.*)'),
                                                            FrenchTransaction.TYPE_LOAN_PAYMENT),
                (re.compile(r'^(?P<category>REMISE CHEQUES)(?P<text>.*)'),
                                                            FrenchTransaction.TYPE_DEPOSIT),
                (re.compile(r'^CARTE RETRAIT (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
               ]
    _coming = False


class SGPEPage(HTMLPage):
    def get_error(self):
        err = self.doc.getroot().cssselect('div.ngo_mire_reco_message') \
            or self.doc.getroot().cssselect('#nge_zone_centre .nge_cadre_message_utilisateur') \
            or self.doc.xpath(u'//div[contains(text(), "Echec de connexion à l\'espace Entreprises")]') \
            or self.doc.xpath(u'//div[contains(@class, "waitAuthJetonMsg")]')
        if err:
            return err[0].text.strip()


class ChangePassPage(SGPEPage):
    def on_load(self):
        message = (CleanText('//div[@class="ngo_gao_message_intro"]')(self.doc)
                or CleanText('//div[@class="ngo_gao_intro"]')(self.doc)
                or u'Informations manquantes sur le site Société Générale')
        raise ActionNeeded(message)


class LoginPage(SGPEPage):
    def login(self, login, password):
        infos_data = self.browser.open('/sec/vk/gen_crypto?estSession=0').text
        infos_data = re.match('^_vkCallback\((.*)\);$', infos_data).group(1)
        infos = json.loads(infos_data.replace("'", '"'))

        url = '/sec/vk/gen_ui?modeClavier=0&cryptogramme=' + infos["crypto"]
        img = Captcha(BytesIO(self.browser.open(url).content), infos)

        try:
            img.build_tiles()
        except TileError as err:
            error("Error: %s" % err)
            if err.tile:
                err.tile.display()

        form = self.get_form(name=self.browser.LOGIN_FORM)
        form['user_id'] = login
        form['codsec'] = img.get_codes(password[:6])
        form['cryptocvcs'] = infos['crypto']
        form['vk_op'] = 'auth'
        form.url = '/authent.html'
        try:
            form.pop('button')
        except KeyError:
            pass
        form.submit()


class CardsPage(LoggedPage, SGPEPage):
    def get_coming_list(self):
        coming_list = []
        for a in self.doc.xpath('//a[contains(@onclick, "changeCarte")]'):
            m = re.findall("'([^']+)'", Attr(a.xpath('.'), 'onclick')(self))
            params = {}
            params['carte'] = m[1]
            params['date'] = m[2]
            coming_list.append(params)
        return coming_list


class CardHistoryPage(LoggedPage, SGPEPage):
    @method
    class iter_transactions(ListElement):
        item_xpath = '//table[@id="tab-corps"]//tr'

        class item(ItemElement):
            klass = Transaction

            obj_rdate = Date(CleanText('./td[1]'), dayfirst=True)
            obj_date = Date(Env('date'), dayfirst=True, default=NotAvailable)
            obj_raw = Transaction.Raw(CleanText('./td[2]'))
            obj_type = Transaction.TYPE_DEFERRED_CARD
            obj__coming = True
            obj_nopurge = True

            def obj_amount(self):
                return CleanDecimal('./td[3]', replace_dots=True, default=NotAvailable)(self)  \
                    or CleanDecimal('./td[2]', replace_dots=True)(self)

            def condition(self):
                return CleanText('./td[2]')(self)

    def has_next(self):
        current = None
        total = None
        for script in self.doc.xpath('//script'):
            if script.text is None:
                continue

            m = re.search('var pageActive\s+= (\d+)', script.text)
            if m:
                current = int(m.group(1))
            m = re.search("var nombrePage\s+= (\d+)", script.text)
            if m:
                total = int(m.group(1))

        if all((current, total)) and current < total:
            return True

        return False


class ProfileProPage(LoggedPage, SGPEPage):
    @method
    class get_profile(ItemElement):
        klass = Profile

        obj_email = Attr('//input[contains(@name, "_email")]', 'value')

        def obj_name(self):
            civility = CleanText('//td[input[contains(@name, "civilite")][@checked]]/label', default=None)(self) or \
                       CleanText(u'//tr[td[contains(text(), "Civilité")]]/td[last()]')(self)
            firstname = Attr('//input[contains(@name, "_prenom")]', 'value', default=None)(self) or \
                        CleanText(u'//tr[td[contains(text(), "Prénom")]]/td[last()]')(self)
            lastname = Attr('//input[contains(@name, "_nom")]', 'value', default=None)(self) or \
                        CleanText(u'//tr[td[contains(text(), "Nom")]]/td[last()]')(self)
            return "%s %s %s" % (civility, firstname, lastname)


class ProfileEntPage(LoggedPage, SGPEPage):
    @method
    class get_profile(ItemElement):
        klass = Person

        obj_email = Attr('//input[@name="email"]', 'value')
        obj_phone = Attr('//input[@name="telephone"]', 'value')
        obj_job = CleanText('//select[@name="fonction"]/option[@selected]')
        obj_company_name = CleanText(u'//tr[th[contains(text(), "Raison sociale")]]/td')
        obj_company_siren = CleanText(u'//tr[th[contains(text(), "SIREN")]]/td')

        def obj_name(self):
            civility = Attr('//input[@name="civilite"][@checked]', 'value', default=None)(self) or \
                       CleanText(u'//tr[th[contains(text(), "Civilité")]]/td')(self)
            firstname = Attr('//input[@name="prenom"]', 'value', default=None)(self) or \
                        CleanText(u'//tr[th[contains(text(), "Prénom")]]/td')(self)
            lastname = Attr('//input[@name="nom"]', 'value', default=None)(self) or \
                       CleanText(u'//tr[th[contains(text(), "Nom")]]/td')(self)
            return "%s %s %s" % (civility, firstname, lastname)
