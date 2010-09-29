# -*- coding: utf-8 -*-
#
#    browser.py
#
#    Copyright 2010 nicolas <nicolas@NicolasDesktop>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#    MA 02110-1301, USA.

import mechanize
import hashlib
import re

from weboob.tools.parsers import get_parser
from weboob.capabilities.bank import Account
from weboob.capabilities.bank import Operation

def remove_html_tags(data):
    p = re.compile(r'<.*?>')
    return p.sub(' ', data)

def remove_extra_spaces(data):
    p = re.compile(r'\s+')
    return p.sub(' ', data)



LOCAL_HASH = ['a02574d7bf67677d2a86b7bfc5e864fe', 'eb85e1cc45dd6bdb3cab65c002d7ac8a', '596e6fbd54d5b111fe5df8a4948e80a4', '9cdc989a4310554e7f5484d0d27a86ce', '0183943de6c0e331f3b9fc49c704ac6d', '291b9987225193ab1347301b241e2187', '163279f1a46082408613d12394e4042a', 'b0a9c740c4cada01eb691b4acda4daea', '3c4307ee92a1f3b571a3c542eafcb330', 'dbccecfa2206bfdb4ca891476404cc68']

ENCODING = 'utf-8'

class BPbrowser(object):


    def __init__(self, login, pwd):

        self.is_logged = False

        self.login_id = login
        self.pwd = pwd

        self.parser = get_parser()()

        self.Browser = mechanize.Browser()
        self.Browser.set_handle_robots(False)

        self.Account_List = []




    def login(self):

        def md5(file):
            f = open(file,'rb')
            md5 = hashlib.md5()
            md5.update(f.read())
            return md5.hexdigest()

        self.Browser.open("https://voscomptesenligne.labanquepostale.fr/wsost/OstBrokerWeb/loginform?TAM_OP=login&ERROR_CODE=0x00000000&URL=%2Fvoscomptes%2FcanalXHTML%2Fidentif.ea%3Forigin%3Dparticuliers")

        process = lambda i: md5(
        
        self.Browser.retrieve(("https://voscomptesenligne.labanquepostale.fr/wsost/OstBrokerWeb/loginform?imgid=%d&0.25122230781963073" % i ))[0])
        Keypad = [ process(i) for i in range(10)]
      
        correspondance = [ Keypad.index(i) for i in LOCAL_HASH]
            

        Newpassword = "".join([str(correspondance[int(c)]) for c in self.pwd])


        self.Browser.select_form(name="formAccesCompte")
        self.Browser.find_control("password").readonly = False
        self.Browser["password"] = Newpassword
        self.Browser["username"] = self.login_id

        self.Browser.submit()
        self.is_logged = True

    def get_accounts_list(self):

        if self.Account_List:
            return self.Account_List



        if not self.is_logged:
            self.login()

        self.Browser.open("https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/authentification/liste_contrat_atos.ea")
        self.Browser.open("https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/releve/liste_comptes.jsp")

        document = self.parser.parse(self.Browser.response(), ENCODING)


        #Parse CCP
        compte_table = document.xpath("//table[@id='comptes']", smart_strings=False)[0]
        compte_ligne = compte_table.xpath("./tbody/tr")

        for compte in compte_ligne:
            account = Account()
            tp = compte.xpath("./td/a")[0]
            account.label = tp.text
            account.link_id = tp.get("href")
            account.id = compte.xpath("./td")[1].text
            account.balance = ''.join( compte.xpath("./td/span")[0].text.replace('.','').replace(',','.').split() )
            self.Account_List.append(account)

        #Parse epargne
        epargne_table = document.xpath("//table[@id='comptesEpargne']", smart_strings=False)[0]
        epargne_ligne = epargne_table.xpath("./tbody/tr")

        for epargne in epargne_ligne:
            account = Account()
            tp = epargne.xpath("./td/a")[0]
            account.label = tp.text
            account.link_id = tp.get("href")
            account.id = epargne.xpath("./td")[1].text
            account.balance = ''.join( epargne.xpath("./td/span")[0].text.replace('.','').replace(',','.').split() )
            self.Account_List.append(account)

        return self.Account_List


    def get_account(self, id):
        if self.Account_List:
            for account in self.Account_List:
                if account.id == id:
                    return account
            return None

        self.get_accounts_list()

        for account in self.Account_List:
                if account.id == id:
                    return account
        return None


    def get_history(self, account):

        self.Browser.open(account.link_id)
        rep = self.Browser.follow_link(url_regex="releve", tag="a")
        document = self.parser.parse(rep, ENCODING)

        mvt_table = document.xpath("//table[@id='mouvements']", smart_strings=False)[0]
        mvt_ligne = mvt_table.xpath("./tbody/tr")

        operations = []

        for mvt in mvt_ligne:
            operation = Operation(len(operations))
            operation.date = mvt.xpath("./td")[0].text
            tp = mvt.xpath("./td")[1]
            operation.label = remove_extra_spaces(remove_html_tags(self.parser.tostring(tp)))


            r = re.compile(r'\d+')
            tp = mvt.xpath("./td/span")
            amount = None
            for t in tp:
                if r.search(t.text):
                    amount = t.text
            amount =  ''.join( amount.replace('.', '').replace(',', '.').split() )
            if amount[0] == "-":
                operation.amount = -float(amount[1:])
            else:
                operation.amount = float(amount)

            operations.append(operation)
        return operations



    def make_transfer(self, from_account, to_account, amount):
        self.Browser.open("https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/f_virementSafran.jsp?n=11")
        self.Browser.open("https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/virementsafran/aiguillage/saisieComptes.ea")

        self.Browser.select_form(name="AiguillageForm")
        self.Browser["idxCompteEmetteur"] = [from_account.id]
        self.Browser["idxCompteReceveur"] = [to_account.id]
        self.Browser.submit()

        self.Browser.select_form(name="VirementNationalForm")
        self.Browser["montant"] = str(amount)
        self.Browser.submit()

        #Confirmation
        # TODO: verifier que tout c'est bien passe
        rep = self.Browser.open("https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/virementsafran/virementnational/4-virementNational.ea")
        html = rep.get_data()
        
        pattern = "Votre virement N.+ ([0-9]+) "
        
        regex = re.compile(pattern)
        match = regex.search(html)
        id_transfer = match.groups()[0]
        return id_transfer
