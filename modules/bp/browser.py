# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Nicolas Duhamel
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


from datetime import datetime, timedelta

from weboob.browser import LoginBrowser, URL, need_login
from weboob.browser.browsers import StatesMixin
from weboob.exceptions import BrowserIncorrectPassword, BrowserBanned, NoAccountsException, BrowserUnavailable
from weboob.tools.compat import urlsplit, parse_qsl

from .pages import (
    LoginPage, Initident, CheckPassword, repositionnerCheminCourant, BadLoginPage, AccountDesactivate,
    AccountList, AccountHistory, CardsList, UnavailablePage, AccountRIB, Advisor,
    TransferChooseAccounts, CompleteTransfer, TransferConfirm, TransferSummary, CreateRecipient, ValidateRecipient,
    ValidateCountry, ConfirmPage, RcptSummary
)
from .pages.accounthistory import LifeInsuranceInvest, LifeInsuranceHistory, LifeInsuranceHistoryInv, RetirementHistory, SavingAccountSummary
from .pages.accountlist import MarketLoginPage, UselessPage
from .pages.pro import RedirectPage, ProAccountsList, ProAccountHistory, DownloadRib, RibPage
from .pages.mandate import MandateAccountsList, PreMandate, PreMandateBis, MandateLife, MandateMarket
from .linebourse_browser import LinebourseBrowser

from weboob.capabilities.bank import TransferError, Account, Recipient, AddRecipientStep
from weboob.tools.value import Value


__all__ = ['BPBrowser', 'BProBrowser']


class BPBrowser(LoginBrowser, StatesMixin):
    BASEURL = 'https://voscomptesenligne.labanquepostale.fr'

    STATE_DURATION = 5

    # FIXME beware that '.*' in start of URL() won't match all domains but only under BASEURL

    login_page = URL(r'.*wsost/OstBrokerWeb/loginform.*', LoginPage)
    repositionner_chemin_courant = URL(r'.*authentification/repositionnerCheminCourant-identif.ea', repositionnerCheminCourant)
    init_ident = URL(r'.*authentification/initialiser-identif.ea', Initident)
    check_password = URL(r'.*authentification/verifierMotDePasse-identif.ea',
                         r'/voscomptes/canalXHTML/securite/authentification/verifierPresenceCompteOK-identif.ea',
                         r'.*//voscomptes/identification/motdepasse.jsp',
                         CheckPassword)

    redirect_page = URL(r'.*voscomptes/identification/identification.ea.*',
                        r'.*voscomptes/synthese/3-synthese.ea',
                        RedirectPage)

    par_accounts_checking = URL('/voscomptes/canalXHTML/comptesCommun/synthese_ccp/afficheSyntheseCCP-synthese_ccp.ea', AccountList)
    par_accounts_savings_and_invests = URL('/voscomptes/canalXHTML/comptesCommun/synthese_ep/afficheSyntheseEP-synthese_ep.ea', AccountList)
    par_accounts_loan = URL('/voscomptes/canalXHTML/pret/encours/consulterPrets-encoursPrets.ea',
                            '/voscomptes/canalXHTML/pret/encours/detaillerPretPartenaireListe-encoursPrets.ea',
                            '/voscomptes/canalXHTML/pret/encours/detaillerOffrePretImmoListe-encoursPrets.ea',
                            '/voscomptes/canalXHTML/pret/encours/detaillerOffrePretConsoListe-encoursPrets.ea', AccountList)

    accounts_rib = URL(r'.*voscomptes/canalXHTML/comptesCommun/imprimerRIB/init-imprimer_rib.ea.*', AccountRIB)

    saving_summary = URL(r'/voscomptes/canalXHTML/assurance/vie/reafficher-assuranceVie.ea(\?numContrat=(?P<id>\w+))?',
                         r'/voscomptes/canalXHTML/assurance/retraiteUCEuro/afficher-assuranceRetraiteUCEuros.ea(\?numContrat=(?P<id>\w+))?',
                         r'/voscomptes/canalXHTML/assurance/retraitePoints/reafficher-assuranceRetraitePoints.ea(\?numContrat=(?P<id>\w+))?',
                         r'/voscomptes/canalXHTML/assurance/prevoyance/reafficher-assurancePrevoyance.ea(\?numContrat=(?P<id>\w+))?',
                         SavingAccountSummary)

    lifeinsurance_invest = URL(r'/voscomptes/canalXHTML/assurance/retraiteUCEuro/afficherSansDevis-assuranceRetraiteUCEuros.ea\?numContrat=(?P<id>\w+)',
                               r'https://www.labanquepostale.fr/particulier/bel_particuliers/assurance/accueil_cachemire.html', LifeInsuranceInvest)
    lifeinsurance_invest2 = URL(r'/voscomptes/canalXHTML/assurance/vie/valorisation-assuranceVie.ea\?numContrat=(?P<id>\w+)', LifeInsuranceInvest)
    lifeinsurance_history = URL(r'/voscomptes/canalXHTML/assurance/vie/historiqueVie-assuranceVie.ea\?numContrat=(?P<id>\w+)', LifeInsuranceHistory)
    lifeinsurance_hist_inv = URL(r'/voscomptes/canalXHTML/assurance/vie/detailMouvement-assuranceVie.ea\?idMouvement=(?P<id>\w+)',
                                 r'/voscomptes/canalXHTML/assurance/vie/detailMouvementHermesBompard-assuranceVie.ea\?idMouvement=(\w+)', LifeInsuranceHistoryInv)

    market_login = URL(r'/voscomptes/canalXHTML/bourse/aiguillage/oicFormAutoPost.jsp', MarketLoginPage)
    useless = URL(r'https://labanquepostale.offrebourse.com/ReroutageSJR', UselessPage)

    retirement_hist = URL(r'/voscomptes/canalXHTML/assurance/retraitePoints/historiqueRetraitePoint-assuranceRetraitePoints.ea(\?numContrat=(?P<id>\w+))?',
                          r'/voscomptes/canalXHTML/assurance/retraiteUCEuro/historiqueMouvements-assuranceRetraiteUCEuros.ea(\?numContrat=(?P<id>\w+))?',
                          r'/voscomptes/canalXHTML/assurance/prevoyance/consulterHistorique-assurancePrevoyance.ea(\?numContrat=(?P<id>\w+))?',
                          RetirementHistory)

    par_account_checking_history = URL('/voscomptes/canalXHTML/CCP/releves_ccp/init-releve_ccp.ea\?typeRecherche=10&compte.numero=(?P<accountId>.*)',
                                       '/voscomptes/canalXHTML/CCP/releves_ccp/afficher-releve_ccp.ea', AccountHistory)
    par_account_deferred_card_history = URL('/voscomptes/canalXHTML/CB/releveCB/preparerRecherche-mouvementsCarteDD.ea\?typeListe=(?P<type>.*)', AccountHistory)
    par_account_checking_coming = URL('/voscomptes/canalXHTML/CCP/releves_ccp_encours/preparerRecherche-releve_ccp_encours.ea\?compte.numero=(?P<accountId>.*)&typeRecherche=1',
                                      '/voscomptes/canalXHTML/CB/releveCB/init-mouvementsCarteDD.ea\?compte.numero=(?P<accountId>.*)&typeListe=1&typeRecherche=10', AccountHistory)
    par_account_savings_and_invests_history = URL('/voscomptes/canalXHTML/CNE/releveCNE/init-releve_cne.ea\?typeRecherche=10&compte.numero=(?P<accountId>.*)',
                                                  '/voscomptes/canalXHTML/CNE/releveCNE/releveCNE-releve_cne.ea', AccountHistory)

    cards_list = URL('/voscomptes/canalXHTML/CB/releveCB/init-mouvementsCarteDD.ea\?compte.numero=(?P<account_id>\w+)$',
                     r'.*CB/releveCB/init-mouvementsCarteDD.ea.*',
                     CardsList)

    transfer_choose = URL(r'/voscomptes/canalXHTML/virement/mpiaiguillage/init-saisieComptes.ea', TransferChooseAccounts)
    transfer_complete = URL(r'/voscomptes/canalXHTML/virement/mpiaiguillage/soumissionChoixComptes-saisieComptes.ea',
                            r'/voscomptes/canalXHTML/virement/virementSafran_national/init-creerVirementNational.ea', CompleteTransfer)
    transfer_confirm = URL(r'/voscomptes/canalXHTML/virement/virementSafran_pea/validerVirementPea-virementPea.ea',
                           r'/voscomptes/canalXHTML/virement/virementSafran_sepa/valider-virementSepa.ea',
                           r'/voscomptes/canalXHTML/virement/virementSafran_sepa/confirmerInformations-virementSepa.ea',
                           r'/voscomptes/canalXHTML/virement/virementSafran_national/valider-creerVirementNational.ea',
                           r'/voscomptes/canalXHTML/virement/virementSafran_national/validerVirementNational-virementNational.ea', TransferConfirm)
    transfer_summary = URL(r'/voscomptes/canalXHTML/virement/virementSafran_national/confirmerVirementNational-virementNational.ea',
                           r'/voscomptes/canalXHTML/virement/virementSafran_pea/confirmerInformations-virementPea.ea',
                           r'/voscomptes/canalXHTML/virement/virementSafran_national/confirmer-creerVirementNational.ea',
                           r'/voscomptes/canalXHTML/virement/virementSafran_sepa/confirmerInformations-virementSepa.ea', TransferSummary)

    create_recipient = URL(r'/voscomptes/canalXHTML/virement/mpiGestionBeneficiairesVirementsCreationBeneficiaire/init-creationBeneficiaire.ea', CreateRecipient)
    validate_country = URL(r'/voscomptes/canalXHTML/virement/mpiGestionBeneficiairesVirementsCreationBeneficiaire/validationSaisiePaysBeneficiaire-creationBeneficiaire.ea',
                             ValidateCountry)
    validate2_recipient = URL(r'/voscomptes/canalXHTML/virement/mpiGestionBeneficiairesVirementsCreationBeneficiaire/valider-creationBeneficiaire.ea', ValidateRecipient)
    rcpt_code = URL(r'/voscomptes/canalXHTML/virement/mpiGestionBeneficiairesVirementsCreationBeneficiaire/validerRecapBeneficiaire-creationBeneficiaire.ea', ConfirmPage)
    rcpt_summary = URL(r'/voscomptes/canalXHTML/virement/mpiGestionBeneficiairesVirementsCreationBeneficiaire/finalisation-creationBeneficiaire.ea', RcptSummary)

    badlogin = URL(r'https://transverse.labanquepostale.fr/.*ost/messages\.CVS\.html\?param=0x132120c8.*', # still valid?
                   r'https://transverse.labanquepostale.fr/xo_/messages/message.html\?param=0x132120c8.*',
                   BadLoginPage)
    disabled_account = URL(r'.*ost/messages\.CVS\.html\?param=0x132120cb.*',
                           r'.*/message\.html\?param=0x132120c.*',
                           r'https://transverse.labanquepostale.fr/xo_/messages/message.html\?param=0x132120cb.*',
                           AccountDesactivate)

    unavailable = URL(r'https?://.*.labanquepostale.fr/delestage.html',
                      r'https://transverse.labanquepostale.fr/xo_/messages/message.html\?param=delestage',
                      UnavailablePage)
    rib_dl = URL(r'.*/voscomptes/rib/init-rib.ea', DownloadRib)
    rib = URL(r'.*/voscomptes/rib/preparerRIB-rib.*', RibPage)
    advisor = URL(r'/ws_q45/Q45/canalXHTML/commun/authentification/init-identif.ea\?origin=particuliers&codeMedia=0004&entree=HubHome',
                  r'/ws_q45/Q45/canalXHTML/desktop/home/init-home.ea', Advisor)

    login_url = 'https://voscomptesenligne.labanquepostale.fr/wsost/OstBrokerWeb/loginform?TAM_OP=login&' \
            'ERROR_CODE=0x00000000&URL=%2Fvoscomptes%2FcanalXHTML%2Fidentif.ea%3Forigin%3Dparticuliers'

    pre_mandate = URL(r'/voscomptes/canalXHTML/sso/commun/init-integration.ea\?partenaire=procapital', PreMandate)
    pre_mandate_bis = URL(r'https://www.gestion-sous-mandat.labanquepostale-gestionprivee.fr/lbpgp/secure/main.html', PreMandateBis)
    mandate_accounts_list = URL(r'https://www.gestion-sous-mandat.labanquepostale-gestionprivee.fr/lbpgp/secure/accounts_list.html', MandateAccountsList)
    mandate_market = URL(r'https://www.gestion-sous-mandat.labanquepostale-gestionprivee.fr/lbpgp/secure_account/selectedAccountDetail.html', MandateMarket)
    mandate_life = URL(r'https://www.gestion-sous-mandat.labanquepostale-gestionprivee.fr/lbpgp/secure_main/asvContratClient.html',
                       r'https://www.gestion-sous-mandat.labanquepostale-gestionprivee.fr/lbpgp/secure_ajax/asvSupportsDetail.html', MandateLife)

    accounts = None

    def __init__(self, *args, **kwargs):
        self.weboob = kwargs.pop('weboob')
        super(BPBrowser, self).__init__(*args, **kwargs)
        dirname = self.responses_dirname
        if dirname:
            dirname += '/bourse'
        self.linebourse = LinebourseBrowser('https://labanquepostale.offrebourse.com/', logger=self.logger, responses_dirname=dirname, weboob=self.weboob)
        self.recipient_form = None

    def load_state(self, state):
        if 'recipient_form' in state and state['recipient_form'] is not None:
            super(BPBrowser, self).load_state(state)
            self.logged = True

    def deinit(self):
        super(BPBrowser, self).deinit()
        self.linebourse.deinit()

    def do_login(self):
        self.location(self.login_url)

        self.page.login(self.username, self.password)

        if self.redirect_page.is_here() and self.page.check_for_perso():
            raise BrowserIncorrectPassword(u"L'identifiant utilisé est celui d'un compte de Particuliers.")
        if self.badlogin.is_here():
            raise BrowserIncorrectPassword()
        if self.disabled_account.is_here():
            raise BrowserBanned()

    @need_login
    def get_accounts_list(self):
        if self.accounts is None:
            accounts = []

            self.par_accounts_checking.go()

            pages = [self.par_accounts_checking, self.par_accounts_savings_and_invests, self.par_accounts_loan]
            no_accounts = 0
            for page in pages:
                page.go()

                if self.page.no_accounts:
                    no_accounts += 1
                    continue

                for account in self.page.iter_accounts():
                    accounts.append(account)

                if self.page.has_mandate_management_space:
                    self.location(self.page.mandate_management_space_link())
                    for mandate_account in self.page.iter_accounts():
                        accounts.append(mandate_account)

            self.accounts = accounts

            # if we are sure there is no accounts on the all visited pages,
            # it is legit.
            if no_accounts == len(pages):
                raise NoAccountsException()

        return self.accounts

    @need_login
    def get_history(self, account):
        # TODO scrap pdf to get history of mandate accounts
        if 'gestion-sous-mandat' in account.url:
            return []

        if account.type in (account.TYPE_PEA, account.TYPE_MARKET):
            self.go_linebourse(account)

            return self.linebourse.iter_history(account.id)

        transactions = []

        if account.type is not Account.TYPE_LOAN:
            self.location(account.url)

            history = {Account.TYPE_CHECKING: self.par_account_checking_history,
                       Account.TYPE_SAVINGS: self.par_account_savings_and_invests_history,
                       Account.TYPE_MARKET: self.par_account_savings_and_invests_history
                      }.get(account.type)

            if history is not None:
                history.go(accountId=account.id)

            if hasattr(self.page, 'iter_transactions') and self.page.has_transactions():
                for tr in self.page.iter_transactions():
                    transactions.append(tr)

            for tr in self.iter_card_transactions(account):
                if not tr._coming:
                    transactions.append(tr)
        transactions.sort(key=lambda tr: tr.rdate, reverse=True)

        return transactions

    @need_login
    def go_linebourse(self, account):
        self.location(account.url)
        self.market_login.go()
        self.linebourse.session.cookies.update(self.session.cookies)
        self.par_accounts_checking.go()

    def _get_coming_transactions(self, account):
        if account.type == Account.TYPE_CHECKING:
            self.location(account.url)
            self.par_account_checking_coming.go(accountId=account.id)

            if self.par_account_checking_coming.is_here() and self.page.has_transactions():
                for tr in self.page.iter_transactions(coming=True):
                    yield tr

    @need_login
    def get_coming(self, account):
        if 'gestion-sous-mandat' in account.url:
            return []

        transactions = list(self._get_coming_transactions(account))

        for tr in self.iter_card_transactions(account):
            if tr._coming:
                transactions.append(tr)

        transactions.sort(key=lambda tr: tr.rdate, reverse=True)

        return transactions

    @need_login
    def iter_card_transactions(self, account):
        def iter_transactions(self, link):
            self.location(link)

            for t in range(6):
                try:
                    self.par_account_deferred_card_history.go(type=t)
                except BrowserUnavailable:
                    self.logger.debug("deferred card history stop at %s", t)
                    break

                if self.par_account_deferred_card_history.is_here():
                    for tr in self.page.get_history(deferred=True):
                        tr.type = tr.TYPE_CARD
                        yield tr

            assert t < 9, "verify if history goes back to 10 months"

        if not account._has_cards:
            return iter([])

        self.cards_list.go(account_id=account.id)
        if self.cards_list.is_here():
            for link in self.page.get_cards():
                return iter_transactions(self, link)
        else:
            return iter_transactions(self, account._has_cards)

    @need_login
    def iter_investment(self, account):
        if 'gestion-sous-mandat' in account.url:
            return self.location(account.url).page.iter_investments()

        if account.type in (account.TYPE_PEA, account.TYPE_MARKET):
            self.go_linebourse(account)
            return self.linebourse.iter_investment(account.id)

        if account.type != Account.TYPE_LIFE_INSURANCE:
            return iter([])

        self.lifeinsurance_invest.go(id=account.id)
        assert self.lifeinsurance_invest.is_here()
        if self.page.has_error():
            raise NotImplementedError()

        investments = list(self.page.iter_investments())

        if not investments:
            self.lifeinsurance_invest2.go(id=account.id)
            investments = list(self.page.iter_investments())

        # check if life insurance is a cachemire contract
        page = None
        if self.page.is_cachemire():
            # had to put full url to skip redirections.
            page = self.open('https://www.labanquepostale.fr/particulier/bel_particuliers/assurance/accueil_cachemire.html').page
            for inv in investments:
                setattr(inv, 'code', page.get_cachemire_code(inv.label))

        return investments

    @need_login
    def _iter_card_tr(self):
        """
        Iter all pages until there are no transactions.
        """
        ops = self.page.get_history(deferred=True)

        while True:
            for tr in ops:
                yield tr

            link = self.page.get_next_link()
            if link is None:
                return

            self.location(link)
            ops = self.page.get_history(deferred=True)

    @need_login
    def iter_recipients(self, account_id):
        return self.transfer_choose.stay_or_go().iter_recipients(account_id=account_id)

    @need_login
    def init_transfer(self, account, recipient, amount, transfer):
        self.transfer_choose.stay_or_go()
        self.page.init_transfer(account.id, recipient._value)
        self.page.complete_transfer(amount, transfer)
        return self.page.handle_response(account, recipient, amount, transfer.label)

    @need_login
    def execute_transfer(self, transfer, code=None):
        if not self.transfer_confirm.is_here():
            raise TransferError('Case not handled.')
        self.page.confirm()
        # Should only happen if double auth.
        if self.transfer_confirm.is_here():
            self.page.double_auth(transfer)
        return self.page.handle_response(transfer)

    def build_recipient(self, recipient):
        r = Recipient()
        r.iban = recipient.iban
        r.id = recipient.iban
        r.label = recipient.label
        r.category = recipient.category
        r.enabled_at = datetime.now().replace(microsecond=0) + timedelta(days=5)
        r.currency = u'EUR'
        r.bank_name = recipient.bank_name
        return r

    def post_code(self, code):
        data = {}
        for k, v in self.recipient_form.items():
            if k != 'url':
                data[k] = v
        data['codeOTPSaisi'] = code
        self.location(self.recipient_form['url'], data=data)

    @need_login
    def new_recipient(self, recipient, is_bp_account=False, **kwargs):
        if 'code' in kwargs:
            assert self.rcpt_code.is_here()

            self.post_code(kwargs['code'])
            self.recipient_form = None
            assert self.rcpt_summary.is_here()
            return self.build_recipient(recipient)

        self.create_recipient.go().choose_country(recipient, is_bp_account)
        self.page.populate(recipient)
        if self.page.is_bp_account():
            return self.new_recipient(recipient, is_bp_account=True, **kwargs)

        # send sms
        self.location(self.page.get_confirm_link())
        self.page.set_browser_form()
        raise AddRecipientStep(self.build_recipient(recipient), Value('code', label='Veuillez saisir votre code de validation'))

    @need_login
    def get_advisor(self):
        return iter([self.advisor.go().get_advisor()])


class BProBrowser(BPBrowser):
    login_url = "https://banqueenligne.entreprises.labanquepostale.fr/wsost/OstBrokerWeb/loginform?TAM_OP=login&ERROR_CODE=0x00000000&URL=%2Fws_q47%2Fvoscomptes%2Fidentification%2Fidentification.ea%3Forigin%3Dprofessionnels"
    accounts_and_loans_url = None

    pro_accounts_list = URL(r'.*voscomptes/synthese/synthese.ea', ProAccountsList)

    pro_history = URL(r'.*voscomptes/historique(ccp|cne)/(\d+-)?historique(ccp|cne).*', ProAccountHistory)

    useless2 = URL(r'.*/voscomptes/bourseenligne/lancementBourseEnLigne-bourseenligne.ea\?numCompte=(?P<account>\d+)', UselessPage)
    market_login = URL(r'.*/voscomptes/bourseenligne/oicformautopost.jsp', MarketLoginPage)

    BASEURL = 'https://banqueenligne.entreprises.labanquepostale.fr'

    def set_variables(self):
        v = urlsplit(self.url)
        version = v.path.split('/')[1]

        self.base_url = 'https://banqueenligne.entreprises.labanquepostale.fr/%s' % version
        self.accounts_url = self.base_url + '/voscomptes/synthese/synthese.ea'

    def go_linebourse(self, account):
        self.location(account.url)
        self.location('../bourseenligne/oicformautopost.jsp')
        self.linebourse.session.cookies.update(self.session.cookies)
        self.location(self.accounts_url)

    @need_login
    def get_history(self, account):
        if account.type in (account.TYPE_PEA, account.TYPE_MARKET):
            self.go_linebourse(account)
            return self.linebourse.iter_history(account.id)

        transactions = []
        v = urlsplit(account.url)
        args = dict(parse_qsl(v.query))
        args['typeRecherche'] = 10

        self.location(v.path, params=args)

        for tr in self.page.iter_history():
            transactions.append(tr)
        transactions.sort(key=lambda tr: tr.rdate, reverse=True)

        return transactions

    def _get_coming_transactions(self, account):
        return []

    @need_login
    def get_accounts_list(self):
        if self.accounts is None:
            self.set_variables()

            accounts = []
            ids = set()

            self.location(self.accounts_url)
            assert self.pro_accounts_list.is_here()

            for account in self.page.get_accounts_list():
                ids.add(account.id)
                accounts.append(account)

            if self.accounts_and_loans_url:
                self.location(self.accounts_and_loans_url)
                assert self.pro_accounts_list.is_here()

            for account in self.page.get_accounts_list():
                if account.id not in ids:
                    ids.add(account.id)
                    accounts.append(account)

            for acc in accounts:
                self.location('%s/voscomptes/rib/init-rib.ea' % self.base_url)
                value = self.page.get_rib_value(acc.id)
                if value:
                    self.location('%s/voscomptes/rib/preparerRIB-rib.ea?%s' % (self.base_url, value))
                    if self.rib.is_here():
                        acc.iban = self.page.get_iban()

            self.accounts = accounts

        return self.accounts
