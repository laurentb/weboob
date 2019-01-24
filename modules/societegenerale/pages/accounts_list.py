# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Jocelyn Jaubert
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

from __future__ import unicode_literals

import requests
import datetime
import re

from weboob.capabilities.base import NotAvailable
from weboob.capabilities.bank import Account, Investment, Loan
from weboob.capabilities.contact import Advisor
from weboob.capabilities.profile import Person, ProfileMissing
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.capabilities.bank.investments import is_isin_valid, create_french_liquidity
from weboob.browser.elements import DictElement, ItemElement, TableElement, method, ListElement
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import (
    CleanText, CleanDecimal, Regexp, Currency, Eval, Field, Format, Date, Env,
)
from weboob.browser.filters.html import Link, TableCell
from weboob.browser.pages import HTMLPage, XMLPage, JsonPage, LoggedPage, pagination
from weboob.exceptions import BrowserUnavailable, ActionNeeded


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


def eval_decimal_amount(value, decimal_position):
    return Eval(lambda x,y: x / 10**y,
                CleanDecimal(Dict(value)),
                CleanDecimal(Dict(decimal_position)))


class JsonBasePage(LoggedPage, JsonPage):
    def on_load(self):
        if Dict('commun/statut')(self.doc).upper() == 'NOK':
            reason = Dict('commun/raison')(self.doc)
            action = Dict('commun/action')(self.doc)

            if action and 'BLOCAGE' in action:
                raise ActionNeeded()

            if 'le service est momentanement indisponible' in reason:
                # TODO: iter account on old website
                # can't access new website
                raise BrowserUnavailable()

            assert 'pas encore géré' in reason, 'Error %s is not handled yet' % reason
            self.browser.logger.warning('This page is not handled yet by SG')


class AccountsMainPage(LoggedPage, HTMLPage):
    def is_old_website(self):
        return Link('//a[contains(text(), "Afficher la nouvelle consultation")]', default=None)(self.doc)


class AccountDetailsPage(LoggedPage, HTMLPage):
    pass


class AccountsPage(JsonBasePage):
    @method
    class iter_accounts(DictElement):
        item_xpath = 'donnees'

        class item(ItemElement):
            klass = Account

            # There are more account type to find
            TYPES = {
                'COMPTE_COURANT': Account.TYPE_CHECKING,
                'PEL': Account.TYPE_SAVINGS,
                'CEL': Account.TYPE_SAVINGS,
                'LDD': Account.TYPE_SAVINGS,
                'LIVRETA': Account.TYPE_SAVINGS,
                'LIVRET_JEUNE': Account.TYPE_SAVINGS,
                'LIVRET_EUROKID': Account.TYPE_SAVINGS,
                'COMPTE_SUR_LIVRET': Account.TYPE_SAVINGS,
                'LIVRET_EPARGNE_PLUS': Account.TYPE_SAVINGS,
                'PLAN_EPARGNE_BANCAIRE': Account.TYPE_SAVINGS,
                'LIVRET_EPARGNE_POPULAIRE': Account.TYPE_SAVINGS,
                'BANQUE_FRANCAISE_MUTUALISEE': Account.TYPE_SAVINGS,
                'PRET_GENERAL': Account.TYPE_LOAN,
                'PRET_PERSONNEL_MUTUALISE': Account.TYPE_LOAN,
                'COMPTE_TITRE_GENERAL': Account.TYPE_MARKET,
                'PEA_ESPECES': Account.TYPE_PEA,
                'PEA_PME_ESPECES': Account.TYPE_PEA,
                'COMPTE_TITRE_PEA': Account.TYPE_PEA,
                'COMPTE_TITRE_PEA_PME': Account.TYPE_PEA,
                'VIE_FEDER': Account.TYPE_LIFE_INSURANCE,
                'PALISSANDRE': Account.TYPE_LIFE_INSURANCE,
                'ASSURANCE_VIE_GENERALE': Account.TYPE_LIFE_INSURANCE,
                'RESERVEA': Account.TYPE_REVOLVING_CREDIT,
                'COMPTE_ALTERNA': Account.TYPE_REVOLVING_CREDIT,
                'AVANCE_PATRIMOINE': Account.TYPE_REVOLVING_CREDIT,
                'PRET_EXPRESSO': Account.TYPE_CONSUMER_CREDIT,
                'PRET_EVOLUTIF': Account.TYPE_CONSUMER_CREDIT,
                'PERP_EPICEA': Account.TYPE_PERP,
            }

            obj_id = obj_number = CleanText(Dict('numeroCompteFormate'), replace=[(' ', '')])
            obj_label = Dict('labelToDisplay')
            obj_balance = CleanDecimal(Dict('soldes/soldeTotal'))
            obj_coming = CleanDecimal(Dict('soldes/soldeEnCours'))
            obj_currency = Currency(Dict('soldes/devise'))
            obj__cards = Dict('cartes', default=[])

            def obj_type(self):
                return self.TYPES.get(Dict('produit')(self), Account.TYPE_UNKNOWN)

            # Useful for navigation
            obj__internal_id = Dict('idTechnique')
            obj__prestation_id = Dict('id')

            def obj__loan_type(self):
                if Field('type')(self) in (Account.TYPE_LOAN, Account.TYPE_CONSUMER_CREDIT,
                                           Account.TYPE_REVOLVING_CREDIT, ):
                    return Dict('codeFamille')(self)
                return None


class AccountsSynthesesPage(JsonBasePage):
    def get_account_comings(self):
        account_comings = {}

        for product in Dict('donnees/syntheseParGroupeProduit')(self.doc):
            for prestation in Dict('prestations')(product):
                account_comings[Dict('id')(prestation)] = CleanDecimal(Dict('soldes/soldeEnCours'))(prestation)
        return account_comings


class LoansPage(JsonBasePage):
    def get_loan_account(self, account):
        assert account._prestation_id in Dict('donnees/tabIdAllPrestations')(self.doc), \
            'Loan with prestation id %s should be on this page ...' % account._prestation_id

        for acc in Dict('donnees/tabPrestations')(self.doc):
            if CleanText(Dict('idPrestation'))(acc) == account._prestation_id:
                loan = Loan()
                loan.id = loan.number = account.id
                loan.label = account.label
                loan.type = account.type

                loan.currency = Currency(Dict('capitalRestantDu/devise'))(acc)
                loan.balance = Eval(lambda x: x / 100, CleanDecimal(Dict('capitalRestantDu/valeur')))(acc)
                loan.coming = account.coming

                loan.total_amount = Eval(lambda x: x / 100, CleanDecimal(Dict('montantPret/valeur')))(acc)
                loan.next_payment_amount = Eval(lambda x: x / 100, CleanDecimal(Dict('montantEcheance/valeur')))(acc)

                loan.duration = Dict('dureeNbMois')(acc)
                loan.maturity_date = datetime.datetime.strptime(Dict('dateFin')(acc), '%Y%m%d')

                loan._internal_id = account._internal_id
                loan._prestation_id = account._prestation_id
                loan._loan_type = account._loan_type
                return loan

    def get_revolving_account(self, account):
        loan = Loan()
        loan.id = loan.number = account.id
        loan.label = account.label
        loan.type = account.type

        loan.currency = account.currency
        loan.balance = account.balance
        loan.coming = account.coming

        loan._internal_id = account._internal_id
        loan._prestation_id = account._prestation_id
        loan._loan_type = account._loan_type

        if Dict('donnees/tabIdAllPrestations')(self.doc):
            for acc in Dict('donnees/tabPrestations')(self.doc):
                if CleanText(Dict('idPrestation'))(acc) == account._prestation_id:

                    if Dict('encoursFinMois', default=NotAvailable)(acc):
                        loan.coming = eval_decimal_amount('encoursFinMois/valeur', 'encoursFinMois/posDecimale')(acc)

                    if Dict('reserveAutorisee', default=NotAvailable)(acc):
                        loan.total_amount = eval_decimal_amount('reserveAutorisee/valeur', 'reserveAutorisee/posDecimale')(acc)
                    else:
                        loan.total_amount = eval_decimal_amount('reserveMaximum/valeur', 'reserveMaximum/posDecimale')(acc)

                    loan.available_amount = eval_decimal_amount('reserveDispo/valeur', 'reserveDispo/posDecimale')(acc)

                    if Dict('reserveUtilisee', default=NotAvailable)(acc):
                        loan.used_amount = eval_decimal_amount('reserveUtilisee/valeur', 'reserveUtilisee/posDecimale')(acc)

                    if Dict('prochaineEcheance', default=NotAvailable)(acc):
                        loan.next_payment_amount = eval_decimal_amount('prochaineEcheance/valeur', 'prochaineEcheance/posDecimale')(acc)
                    else:
                        loan.next_payment_amount = eval_decimal_amount('montantMensualite/valeur', 'montantMensualite/posDecimale')(acc)
                        loan.last_payment_amount = loan.next_payment_amount

                    loan.duration = Dict('dureeNbMois')(acc)
                    return loan
        return loan


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(r'^CARTE \w+ RETRAIT DAB.*? (?P<dd>\d{2})\/(?P<mm>\d{2})( (?P<HH>\d+)H(?P<MM>\d+))? (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^CARTE \w+ (?P<dd>\d{2})\/(?P<mm>\d{2})( A (?P<HH>\d+)H(?P<MM>\d+))? RETRAIT DAB (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^CARTE \w+ REMBT (?P<dd>\d{2})\/(?P<mm>\d{2})( A (?P<HH>\d+)H(?P<MM>\d+))? (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_PAYBACK),
                (re.compile(r'^(?P<category>CARTE) \w+ (?P<dd>\d{2})\/(?P<mm>\d{2}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile(r'^(?P<dd>\d{2})(?P<mm>\d{2})\/(?P<text>.*?)\/?(-[\d,]+)?$'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile(r'^(?P<category>(COTISATION|PRELEVEMENT|TELEREGLEMENT|TIP)) (?P<text>.*)'),
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
                (re.compile(r'^TOTAL DES FACTURES (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CARD_SUMMARY),
                (re.compile(r'^DEBIT MENSUEL CARTE (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CARD_SUMMARY),
                (re.compile(r'^CREDIT MENSUEL CARTE (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CARD_SUMMARY),
                (re.compile(r'^CARTE \w+ (?P<dd>\d{2})\/(?P<mm>\d{2}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CARD),
               ]


class TransactionItemElement(ItemElement):
    klass = Transaction

    def obj_id(self):
        if not Dict('idOpe')(self):
            return
        id_op = Regexp(CleanText(Dict('idOpe')), r'(\d+)/')(self)
        if id_op != '0':
            # card summary has id '0'
            return id_op

    def obj_vdate(self):
        if Dict('dateChargement')(self):
            return Eval(lambda t: datetime.date.fromtimestamp(int(t)/1000),Dict('dateChargement'))(self)

    obj_date = Eval(lambda t: datetime.date.fromtimestamp(int(t)/1000), Dict('dateOpe'))
    obj_amount = CleanDecimal(Dict('mnt'))
    obj_raw = Transaction.Raw(Dict('libOpe'))


class HistoryPage(JsonBasePage):
    def hist_pagination(self, condition):
        all_conditions = {
            'history': (
                not Dict('donnees/listeOperations')(self.doc),
                not Dict('donnees/recapitulatifCompte/chargerPlusOperations')(self.doc)
            ),
            'future': (
                not Dict('donnees/listeOperationsFutures')(self.doc),
                not Dict('donnees/recapitulatifCompte/chargerPlusOperations')(self.doc)
            ),
            'intraday': (
                not Dict('donnees/listeOperations')(self.doc),
                Dict('donnees/listeOperations')(self.doc) and \
                    not Dict('donnees/listeOperations/0/statutOperation')(self.doc) == 'INTRADAY',
                not Dict('donnees/recapitulatifCompte/chargerPlusOperations')(self.doc),
                not Dict('donnees/recapitulatifCompte/encours')(self.doc),
            ),
        }

        if any(all_conditions[condition]):
            return

        if '&an200_operationsSupplementaires=true' in self.browser.url:
            return self.browser.url
        return self.browser.url + '&an200_operationsSupplementaires=true'

    @pagination
    @method
    class iter_history(DictElement):
        def next_page(self):
            return self.page.hist_pagination('history')

        item_xpath = 'donnees/listeOperations'

        class item(TransactionItemElement):
            def condition(self):
                return Dict('statutOperation')(self) == 'COMPTABILISE'

    @pagination
    @method
    class iter_card_transactions(DictElement):
        def next_page(self):
            return self.page.hist_pagination('history')

        item_xpath = 'donnees/listeOperations'

        class item(TransactionItemElement):
            def condition(self):
                conditions = (
                    Dict('idOpe')(self) and Regexp(CleanText(Dict('idOpe')), r'(\d+)/')(self) == '0',
                    Env('card_number')(self) in Dict('libOpe')(self),
                    Dict('statutOperation')(self) == 'COMPTABILISE',
                )
                return all(conditions)

            obj_type = Transaction.TYPE_CARD_SUMMARY

            def obj_amount(self):
                return abs(CleanDecimal(Dict('mnt'))(self))

            class obj__card_transactions(DictElement):
                item_xpath = 'listeOpeFilles'

                class tr_item(TransactionItemElement):
                    def condition(self):
                        return Dict('statutOperation')(self) == 'COMPTABILISE'

    @pagination
    @method
    class iter_intraday_comings(DictElement):
        def next_page(self):
            return self.page.hist_pagination('intraday')

        item_xpath = 'donnees/listeOperations'

        class item(TransactionItemElement):
            def condition(self):
                return Dict('statutOperation')(self) == 'INTRADAY'

    @pagination
    @method
    class iter_future_transactions(DictElement):
        def next_page(self):
            return self.page.hist_pagination('future')

        item_xpath = 'donnees/listeOperationsFutures'

        class item(ItemElement):
            def condition(self):
                conditions = (
                    Dict('operationCategorisable')(self) in ('FUTURE', 'OPERATION_MERE'),
                    Dict('prestationIdAssocie')(self) == Env('acc_prestation_id')(self)
                )
                return all(conditions)

            klass = Transaction

            obj_date = Date(Dict('dateEcheance'))
            obj_amount = CleanDecimal(Dict('montant/value'))
            obj_raw = obj_label = Dict('libelleAAfficher')

            class obj__card_coming(DictElement):
                item_xpath = 'operationsFilles'

                class tr_item(ItemElement):
                    klass = Transaction

                    obj_amount = CleanDecimal(Dict('montant/value'))
                    obj_date = obj_vdate = Date(Dict('dateEcheance'))
                    obj_raw = Transaction.Raw(Dict('libelleOrigine'))


class CardHistoryPage(LoggedPage, HTMLPage):
    @method
    class iter_card_history(ListElement):
        item_xpath = '//tr'

        class item(ItemElement):
            klass = Transaction

            obj_label = CleanText('.//td[@headers="Libelle"]/span')

            def obj_date(self):
                if not 'TOTAL DES FACTURES' in Field('label')(self):
                    return Date(Regexp(CleanText('.//td[@headers="Date"]'), r'\d{2}\/\d{2}\/\d{4}'))(self)
                else:
                    return NotAvailable

            def obj_amount(self):
                if not 'TOTAL DES FACTURES' in Field('label')(self):
                    return MyDecimal(CleanText('.//td[contains(@headers, "Debit")]'))(self)
                else:
                    return abs(MyDecimal(CleanText('.//td[contains(@headers, "Debit")]'))(self))

            def obj_raw(self):
                if not 'TOTAL DES FACTURES' in Field('label')(self):
                    return Transaction.Raw(CleanText('.//td[@headers="Libelle"]/span'))(self)
                return NotAvailable


class CreditPage(LoggedPage, HTMLPage):
    def go_history_page(self):
        redirection_script = CleanText('//script[contains(text(), "setPrestationURL")]')(self.doc)
        history_link = re.search(r'setPrestationURL\("(.*)"\)', redirection_script)
        if history_link:
            self.browser.location(self.browser.absurl(history_link.group(1)))


class CreditHistoryPage(LoggedPage, HTMLPage):
    def build_doc(self, content):
        # for some reason, lxml discards the first tag inside the CDATA
        # (of course, there shouldn't be XML inside the CDATA in the first place)
        content = content.replace(b'<![CDATA[', b'<![CDATA[<bullshit/>')
        return super(CreditHistoryPage, self).build_doc(content)

    @method
    class iter_credit_history(ListElement):
        item_xpath = '//tr'

        class item(ItemElement):
            klass = Transaction

            obj_label = CleanText('./@title')
            obj_date = Date(CleanText('./td[@headers="Date"]'), dayfirst=True)

            def obj_amount(self):
                credit = MyDecimal(CleanText('./td[contains(@headers, "Credit")]', replace=[('&nbsp;', '')]))(self)
                if credit:
                    return credit
                return MyDecimal(CleanText('./td[contains(@headers, "Debit")]', replace=[('&nbsp;', '')]))(self)


class LifeInsurance(LoggedPage, HTMLPage):
    def on_load(self):
        errors_msg = (
            CleanText('//span[@class="error_msg"]')(self.doc),
            CleanText("//div[@class='net2g_asv_error_full_page']")(self.doc)
        )
        for error_msg in errors_msg:
            if error_msg and 'Le service est momentanément indisponible' in error_msg:
                raise BrowserUnavailable(error_msg)
            if error_msg and 'Aucune opération' in error_msg:
                break
        else:
            assert not any(errors_msg), 'Some errors are not handle yet'

    def has_link(self):
        return Link('//a[@href="asvcns20a.html"]', default=NotAvailable)(self.doc)

    def get_history_link(self):
        return Link('//a[img[@alt="Suivi des opérations"]]', default=NotAvailable)(self.doc)

    def get_pages(self):
        pages = CleanText('//div[@class="net2g_asv_tableau_pager"]')(self.doc)
        if pages:
            # "pages" value is for example "1/5"
            return re.search(r'(\d)/(\d)', pages).group(1, 2)

    def li_pagination(self):
        pages = self.get_pages()
        if pages:
            current_page, total_pages = int(pages[0]), int(pages[1])
            if current_page < total_pages:
                data = {
                    'a100_asv_action': 'actionSuivPage',
                    'a100_asv_numPage': current_page,
                    'a100_asv_nbPages': total_pages,
                }
                return requests.Request('POST', self.browser.url, data=data)


class LifeInsuranceInvest(LifeInsurance):
    @pagination
    @method
    class iter_investment(TableElement):
        def next_page(self):
            return self.page.li_pagination()

        item_xpath = '//table/tbody/tr[starts-with(@class, "net2g_asv_tableau_ligne_")]'
        head_xpath = '//table/thead/tr/td'

        col_label = re.compile('Support')
        col_quantity = re.compile("Nombre")
        col_unitvalue = re.compile("Valeur")
        col_valuation = re.compile("Capital")

        class item(ItemElement):
            klass = Investment

            obj_code = Regexp(CleanText(TableCell('label')), r'Code ISIN : (\w+) ', default=NotAvailable)
            obj_quantity = MyDecimal(TableCell('quantity'), default=NotAvailable)
            obj_unitvalue = MyDecimal(TableCell('unitvalue'), default=NotAvailable)

            # Some PERP invests don't have valuation
            obj_valuation = MyDecimal(TableCell('valuation', default=NotAvailable), default=NotAvailable)

            def obj_label(self):
                if 'FONDS EN EUROS' in CleanText(TableCell('label'))(self):
                    return 'FONDS EN EUROS'
                return Regexp(CleanText(TableCell('label')), r'Libellé support : (.*) Code ISIN')(self)

            def obj_code_type(self):
                if Field('label')(self) == 'FONDS EN EUROS':
                    return NotAvailable
                return Investment.CODE_TYPE_ISIN


class LifeInsuranceInvest2(LifeInsuranceInvest):
    @method
    class iter_investment(TableElement):
        item_xpath = '//table/tbody/tr[starts-with(@class, "net2g_asv_tableau_ligne_")]'
        head_xpath = '//table/thead/tr/td'

        col_label = u'Support'
        col_valuation = u'Montant'

        class item(ItemElement):
            klass = Investment
            obj_label = CleanText(TableCell('label'))
            obj_valuation = MyDecimal(TableCell('valuation'))


class LifeInsuranceHistory(LifeInsurance):
    @pagination
    @method
    class iter_li_history(TableElement):
        def next_page(self):
            return self.page.li_pagination()

        item_xpath = '//table/tbody/tr[starts-with(@class, "net2g_asv_tableau_ligne_")]'
        head_xpath = '//table/thead/tr/td'

        col_label = 'Opération'
        col_date = 'Date'
        col_amount = 'Montant'
        col__status = 'Statut'

        class item(ItemElement):
            def condition(self):
                return (CleanText(TableCell('_status'))(self) == 'Réalisé' and
                        MyDecimal(TableCell('amount'), default=NotAvailable)(self))

            klass = Transaction

            obj_label = CleanText(TableCell('label'))
            obj_amount = MyDecimal(TableCell('amount'))

            def obj_date(self):
                tr_date = CleanText(TableCell('date'))(self)
                if len(tr_date) == 4:
                    # date of transaction with label 'Intérêts crédités au cours de l'année'
                    # is only year valuation
                    # set transaction date to the last day year
                    return datetime.date(int(tr_date), 12, 31)
                return Date(dayfirst=True).filter(tr_date)


class MarketPage(LoggedPage, HTMLPage):
    @method
    class iter_investments(TableElement):
        table_xpath = '//tr[td[contains(@class,"TabTit1l")]]/following-sibling::tr//table'
        head_xpath = table_xpath + '//tr[1]/td'
        item_xpath = table_xpath + '//tr[position()>1]'

        col_quantity = 'Quantité'
        col_valuation = 'Evaluation'
        col_vdate = 'Date'
        col_unitvalue = 'Cours'

        def condition(self):
            return not 'PAS DE VALEURS DETENUES ACTUELLEMENT SUR CE COMPTE' in \
                CleanText('//td[@class="MessErreur"]')(self.el)

        class item(ItemElement):
            klass = Investment

            obj_code = Regexp(CleanText('./td[1]//@title'), '- (\w+) -')
            obj_label = CleanText('./td[1]//text()')
            obj_quantity = MyDecimal(TableCell('quantity'))
            obj_valuation = MyDecimal(TableCell('valuation'))
            obj_vdate = Date(Regexp(CleanText(TableCell('vdate')), r'(\d{2}/\d{2}/\d{4})'))
            obj_unitvalue = MyDecimal(TableCell('unitvalue'))

            def obj_code_type(self):
                if is_isin_valid(Field('code')(self)):
                    return Investment.CODE_TYPE_ISIN
                return NotAvailable


class PeaLiquidityPage(LoggedPage, HTMLPage):
    def iter_investments(self, account):
        yield (create_french_liquidity(account.balance))


class AdvisorPage(LoggedPage, XMLPage):
    ENCODING = 'ISO-8859-15'

    def get_advisor(self):
        advisor = Advisor()
        advisor.name = Format('%s %s', CleanText('//NomConseiller'), CleanText('//PrenomConseiller'))(self.doc)
        advisor.phone = CleanText('//NumeroTelephone')(self.doc)
        advisor.agency = CleanText('//liloes')(self.doc)
        advisor.address = Format('%s %s %s',
                                 CleanText('//ruadre'),
                                 CleanText('//cdpost'),
                                 CleanText('//loadre')
                                 )(self.doc)
        advisor.email = CleanText('//Email')(self.doc)
        advisor.role = "wealth" if "patrimoine" in CleanText('//LibelleNatureConseiller')(self.doc).lower() else "bank"
        yield advisor


class HTMLProfilePage(LoggedPage, HTMLPage):
    def on_load(self):
        msg = CleanText('//div[@id="connecteur_partenaire"]', default='')(self.doc)
        service_unavailable_msg = CleanText('//div[@class="message-error" and contains(text(), "indisponible")]')(self.doc)

        if 'Erreur' in msg:
            raise BrowserUnavailable(msg)
        if service_unavailable_msg:
            raise ProfileMissing(service_unavailable_msg)

    def get_profile(self):
        profile = Person()
        profile.name = Regexp(CleanText('//div[@id="dcr-conteneur"]//div[contains(text(), "PROFIL DE")]'), r'PROFIL DE (.*)')(self.doc)
        profile.address = CleanText('//div[@id="dcr-conteneur"]//div[contains(text(), "ADRESSE")]/following::table//tr[3]/td[2]')(self.doc)
        profile.address += ' ' + CleanText('//div[@id="dcr-conteneur"]//div[contains(text(), "ADRESSE")]/following::table//tr[5]/td[2]')(self.doc)
        profile.address += ' ' + CleanText('//div[@id="dcr-conteneur"]//div[contains(text(), "ADRESSE")]/following::table//tr[6]/td[2]')(self.doc)
        profile.country = CleanText('//div[@id="dcr-conteneur"]//div[contains(text(), "ADRESSE")]/following::table//tr[7]/td[2]')(self.doc)

        return profile


class XMLProfilePage(LoggedPage, XMLPage):
    def get_email(self):
        return CleanText('//AdresseEmailExterne')(self.doc)


class UnavailableServicePage(LoggedPage, HTMLPage):
    def on_load(self):
        if self.doc.xpath('//div[contains(@class, "erreur_404_content")]'):
            raise BrowserUnavailable()
