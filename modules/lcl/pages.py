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
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard, VirtKeyboardError
from logging import error
import tempfile
import math
import random

class LCLVirtKeyboard(MappedVirtKeyboard):
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

    url="/outil/UAUT/Clavier/creationClavier?random="

    color=(255,255,255,255)

    def __init__(self,basepage):
        img=basepage.document.find("//img[@id='idImageClavier']")
        random.seed()
        self.url+="%li"%math.floor(long(random.random()*1000000000000000000000))
        MappedVirtKeyboard.__init__(self,basepage.browser.openurl(self.url),
                                    basepage.document,img,self.color,"id")
        if basepage.browser.responses_dirname is None:
            basepage.browser.responses_dirname = \
                    tempfile.mkdtemp(prefix='weboob_session_')
        self.check_symbols(self.symbols,basepage.browser.responses_dirname)

    def get_symbol_code(self,md5sum):
        code=MappedVirtKeyboard.get_symbol_code(self,md5sum)
        return code[-2:]

    def get_string_code(self,string):
        code=''
        for c in string:
            code+=self.get_symbol_code(self.symbols[c])
        return code

class SkipPage(BasePage):
    pass

class LoginPage(BasePage):
    def myXOR(self,value,seed):
        s=''
        for i in xrange(len(value)):
            s+=chr(seed^ord(value[i]))
        return s

    def login(self, agency, login, passwd):
        try:
            vk=LCLVirtKeyboard(self)
        except VirtKeyboardError,err:
            error("Error: %s"%err)
            return False

        password=vk.get_string_code(passwd)

        seed=-1
        str="var aleatoire = "
        for script in self.document.findall("//script"):
            if(script.text is None or len(script.text)==0):
                continue
            offset=script.text.find(str)
            if offset!=-1:
                seed=int(script.text[offset+len(str)+1:offset+len(str)+2])
                break
        if seed==-1:
            error("Variable 'aleatoire' not found")
            return False

        self.browser.select_form(
            predicate=lambda x: x.attrs.get('id','')=='formAuthenticate')
        self.browser.form.set_all_readonly(False)
        self.browser['agenceId'] = agency
        self.browser['compteId'] = login
        self.browser['postClavierXor'] = base64.b64encode(self.myXOR(password,seed))
        try:
            self.browser.submit()
        except BrowserUnavailable:
            # Login is not valid
            return False
        return True

    def is_error(self):
        for text in self.document.find('body').itertext():
            text=text.strip()
            # Login seems valid, but password does not
            needle='Les données saisies sont incorrectes'
            if text.startswith(needle.decode('utf-8')):
                return True
        return False

class AccountsPage(BasePage):
    def get_list(self):
        l = []
        for a in self.document.getiterator('a'):
            link=a.attrib.get('href')
            if link is not None and link.startswith("/outil/UWLM/ListeMouvements"):
                account = Account()
                account.link_id=link
                parameters=link.split("?").pop().split("&")
                for parameter in parameters:
                    list=parameter.split("=")
                    value=list.pop()
                    name=list.pop()
                    if name=="agence":
                        account.id=value
                    elif name=="compte":
                        account.id+=value
                    elif name=="nature":
                        account.type=value
                account.label=a.getparent().getprevious().text.strip()
                balance=a.text.replace(u"\u00A0",'').replace(' ','').replace('.','').replace('+','').replace(',','.')
                account.balance=float(balance)
                l.append(account)
        return l

class AccountHistoryPage(BasePage):
    def get_operations(self,account):
        operations = []
        tables=self.document.findall("//table[@class='tagTab pyjama']")
        table=None
        for i in range(len(tables)):
            # Look for the relevant table in the Pro version
            header=tables[i].getprevious()
            while str(header.tag)=="<built-in function Comment>":
                header=header.getprevious()
            header=header.find("div")
            if header is not None:
                header=header.find("span")
            if header is not None and \
               header.text.strip().startswith("Opérations effectuées".decode('utf-8')):
                table=tables[i]
                break;
            # Look for the relevant table in the Particulier version
            header=tables[i].find("thead").find("tr").find("th[@class='titleTab titleTableft']")
            if header is not None and\
               header.text.strip().startswith("Solde au"):
                table=tables[i]
                break;

        for tr in table.iter('tr'):
            # skip headers and empty rows
            if len(tr.findall("th"))!=0 or\
               len(tr.findall("td"))==0:
                continue
            operation=Operation(len(operations))
            mntColumn=0
            for td in tr.iter('td'):
                value=td.attrib.get('id')
                if value is None:
                    value=td.attrib.get('class');
                if value.startswith("date"):
                    operation.date=date(*reversed([int(x) for x in td.text.split('/')]))
                elif value.startswith("lib") or value.startswith("opLib"):
                    # misclosed A tag requires to grab text from td
                    operation.label=u''.join([txt.strip() for txt in td.itertext()])
                elif value.startswith("solde") or value.startswith("mnt"):
                    mntColumn+=1
                    if td.text.strip() != "":
                        amount = float(td.text.strip().replace('.','').replace(',','.').replace(u"\u00A0",'').replace(' ',''))
                        if value.startswith("soldeDeb") or mntColumn==1:
                            amount=-amount
                        operation.amount=amount
            operations.append(operation)
        return operations


