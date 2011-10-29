# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon, Pierre Mazière
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

import base64
from datetime import date
from weboob.capabilities.bank import Operation
from weboob.capabilities.bank import Account
from weboob.tools.browser import BasePage, BrowserUnavailable
from weboob.tools.virtkeyboard import VirtKeyboard, VirtKeyboardError
from logging import error

class LoginPage(BasePage):
    def myXOR(self,value,seed):
        s=''
        for i in xrange(len(value)):
            s+=chr(seed^ord(value[i]))
        return s

    def login(self, agency, login, passwd):
        symbols={'0':'9da2724133f2221482013151735f033c',
                 '1':'873ab0087447610841ae1332221be37b',
                 '2':'93ce6c330393ff5980949d7b6c800f77',
                 '3':'b2d70c69693784e1bf1f0973d81223c0',
                 '4':'498c8f5d885611938f94f1c746c32978',
                 '5':'359bcd60a9b8565917a7bf34522052c3',
                 '6':'aba912172f21f78cd6da437cfc4cdbd0',
                 '7':'f710190d6b947869879ec02d8e851dfa',
                 '8':'b42cc25e1539a15f767aa7a641f3bfec',
                 '9':'cc60e5894a9d8e12ee0c2c104c1d5490'
                }

        map=self.document.find("//map[@id='claviermap']")

        coords={}
        for area in map.getiterator("area"):
            code=area.attrib.get("onclick")[-5:-3]
            area_coords=[]
            for coord in area.attrib.get("coords").split(','):
                area_coords.append(int(coord))
            coords[code]=tuple(area_coords)
        try:
            vk=VirtKeyboard(self.browser.openurl("/UWBI/UWBIAccueil?DEST=GENERATION_CLAVIER"),
                            coords,(255,255,255,255))
        except VirtKeyboardError,err:
            error("Error: %s"%err)
            return False

        for s in symbols.keys():
            try:
                value=vk.get_symbol_code(symbols[s])
            except VirtKeyboardError:
                if self.browser.responses_dirname is None:
                    self.browser.responses_dirname = \
                            tempfile.mkdtemp(prefix='weboob_session_')
                vk.generate_MD5(self.browser.responses_dirname)
                error("Error: Symbol '%s' not found; all symbol hashes are available in %s" \
                      % (s,self.browser.responses_dirname))
                return False

        password=''
        for c in passwd:
            password+=vk.get_symbol_code(symbols[c])
        seed=-1
        str="var aleatoire = "
        for script in self.document.findall("/head/script"):
            if(script.text is None or len(script.text)==0):
                continue
            offset=script.text.find(str)
            if offset!=-1:
                seed=int(script.text[offset+len(str):offset+len(str)+1])
                break
        if seed==-1:
            error("Variable 'aleatoire' not found")
            return False

        self.browser.select_form(nr=0)
        self.browser.form.set_all_readonly(False)
        self.browser['agenceId'] = base64.b64encode(self.myXOR(agency,seed))
        self.browser['compteId'] = base64.b64encode(self.myXOR(login,seed))
        self.browser['postClavier'] = base64.b64encode(self.myXOR(password,seed))
        try:
            self.browser.submit()
        except BrowserUnavailable:
            # Login is not valid
            return False
        return True

class LoginResultPage(BasePage):
    def is_error(self):
        for text in self.document.find('body').itertext():
            text=text.strip()
            # Login seems valid, but password does not
            needle='Les données saisies sont incorrectes'
            if text.startswith(needle.decode('utf-8')):
                return True

        return False

class FramePage(BasePage):
    pass


class AccountsPage(BasePage):
    def get_list(self):
        l = []
        for div in self.document.getiterator('div'):
            if div.attrib.get('class')=="unCompte-CA" or\
            div.attrib.get('class')=="unCompte-CC" or\
            div.attrib.get('class')=="unCompte-CD" or\
            div.attrib.get('class')=="unCompte-CE":
                #CA=> ? maybe Assurance-vie
                #CC=> Compte Courant
                #CD=> Compte Dépôt
                #CE=> Compte d'Epargne
                account = Account()
                account.type=div.attrib.get('class')[-2:]
                account.id = div.attrib.get('id').replace('-','')
                for td in div.getiterator('td'):
                    if td.find("div") is not None and td.find("div").attrib.get('class') == 'libelleCompte':
                        account.label = td.find("div").text
                    elif td.find('a') is not None and td.find('a').attrib.get('class') is None:
                        balance = td.find('a').text.replace(u"\u00A0",'').replace('.','').replace('+','').replace(',','.')
                        account.balance = float(balance)
                        account.link_id = td.find('a').attrib.get('href')

                l.append(account)

        return l

class AccountHistoryPage(BasePage):
    def get_specific_operations(self,tableHeaderPrefixes,debitColumns,creditColumns):
        operations = []
        for td in self.document.iter('td'):
            text=td.findtext("b")
            if text is None:
                continue
            for i in range(len(tableHeaderPrefixes)):
                if text.startswith(tableHeaderPrefixes[i].decode('utf-8')):
                    tbody=td.getparent().getparent()
                    for tr in tbody.iter('tr'):
                        tr_class=tr.attrib.get('class')
                        if tr_class == 'tbl1' or tr_class=='tbl2':
                            tds=tr.findall('td')
                            d=date(*reversed([int(x) for x in tds[0].text.split('/')]))
                            label=u''+tds[1].find('a').text.strip()
                            if tds[debitColumns[i]].text.strip() != u"":
                                amount = - float(tds[debitColumns[i]].text.strip().replace('.','').replace(',','.').replace(u"\u00A0",'').replace(' ',''))
                            else:
                                amount= float(tds[creditColumns[i]].text.strip().replace('.','').replace(',','.').replace(u"\u00A0",'').replace(' ',''))
                            operation=Operation(len(operations))
                            operation.date=d
                            operation.label=label
                            operation.amount=amount
                            operations.append(operation)
        return operations

    def get_operations(self,account):
        if account.type=="CA":
            return [] # Not supported: page example required
        elif account.type=="CC":
            return self.get_specific_operations(['Opérations effectuées'],[3],[4])
        elif account.type=="CD":
            return self.get_specific_operations(['Solde au'],[2],[3])
        elif account.type=="CE":
            return self.get_specific_operations(['Solde au'],[2],[3])


