# -*- coding: utf-8 -*-

# Copyright(C) 2015 Romain Bignon
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

import re
from io import BytesIO

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.exceptions import ParseError, ActionNeeded
from weboob.tools.captcha.virtkeyboard import GridVirtKeyboard
from weboob.browser.filters.standard import CleanText


class DelubacVirtKeyboard(GridVirtKeyboard):
    symbols = {'0': ('ad0ae6278e58bf2300cb7e0b87729e4d', '33e6fecddeb02ad3756570b541320914', '9f47d540a8bf89056106bc2c06fdea2e',
                     '176c63721c61da6cbae04ed95b36a343', '6af3ed27e718a93acc8923abebef4734', '0f8aa934a28d0a3dc989b3d6889d5964',
                     '1d21ebe7eb1d1ae32ec52ea4c30a38ca'),
               '1': ('ba6ca06344687bd2337e2bfb39e2378a', 'cef70da6fb76b8bb90c025d4e62db7f6'),
               '2': ('c442cd1cee0c95d8423665983e9e45b7', '38aac4c0dcc1c40bfa0173bb2fc959f6', '8be33fe7de693d8d1404c0b51ce6f893',
                     '85bf89cc03d7d772f7b0b4aa9a7897c6', '955423582ae4cde07b0831eee879c068', '19712acd76beedef3038b131ee9b5f19',
                     '34b0276d52b8bdc2e68c98f1bac8fecc'),
               '3': ('f5ebe3bdfc645210c38f1b89bde6b732', '0ff42e4481af10901213636a654d56ab', '3b6b94bc9748a881fd0692f5a8c4a791',
                     '38809719796e812285e8da365268336d', '31ee44b350e8a062fcde5c8c6e8e1dbf', '84012a1fe9c2809fb348d3dcd362d15a',
                     '4e076b4b60852f8e8fb40ac751a8c7a5', 'd9db707af417a8dc78d464b9baa90aae'),
               '4': ('6d194520cb4d7e5ba0c24fa6dad21285', '08e40532e7c4207239c543576a2fa7b1', '4f7267f5879ba5fdda61ff6ac7897d75',
                     '7a5d5abb743d13a036a7d8582576b284', '59767e1a982ee4212d795acf1f3bda3d', '9f796703a309453d5f4c0f3baddf2f0d',
                     '9d52b25d92866001c6035ea3abfc04ed', 'b6fe068a99e5b93af2348947ddeddf5c', '9a021f8eb7ab9091aeba512481de3301'),
               '5': ('b3d5990972b82abd9e8c049457794ab1', '4c761e7b65eed3baf899960e0ba0d131', '729a2baf278fe557ee54f532b8263a98',
                     '634e8b3ec904f219b858990a739b8283', '55138402b60e3d3027e1d26b078b73f9', '7a03617f129806672ae5c4b478535b29',
                     'c4bb4958271d61d098bd239e403e9ecc', '2860e8a046d22bcd14c26d78cae1d730', '84eb9c1747471c3fb29a68703f2da976'),
               '6': ('c69e8ad49ffa359ca7f77658c090e1dd', 'e0294f0af8037d544f5b4729931453f3', '359f46ac7dc0d8dee18831981c863a73',
                     '77d2f88d5f0f2fcc323bcdbd2b62cb29', '50e2c34749b3aa4010db73d108e241ae', '3fdc463cfea86a565151059d8d114123',
                     '9e321e0d31a1e54510b51ae5c2e91749', 'fab5e1970f78c521a94d8aa52a88075a', 'b620c174da8d74d04139b0d334d064b5',
                     'd83eff07ba513c875dc42ec87a441989', '67b214138a7efe3f600adaea1d1cffbc', '014dc575b0a980b0037cf1e8f5ed9987',
                     '0994aab1f56f9427d1f5dbba27eb3266', 'bda8a78783bddfbb8a3bc6b03ba1c449', '1ddb303b52769096582095e70ef481a4',
                     '344642e1a97750328f058e1dcb4cd6e9', '4250fbdcf8859e6b45fc065f1bbd3967'),
               '7': ('57b179554275be15562824284395c833', '687f5020c59bdde6edac72917cbbebc2', '6752eb433a0f72312f19b24f69ea6adb',
                     'ea6eec45008ddb61cd830bd690a3d55f'),
               '8': ('394752d62aea07c5c5f5650b3e404e88', 'dc72f59b61e18dd313e16d4ee0bb8207', '06297c98471f5a06a9c180dbb8b82305',
                     '8349e6ae068167ee565721a34a4bcc9f', '1347687d61f0fb4c9c0601a9ff4c7d60', '5dd319ab0d0dd40730b90abdf2ad27c4',
                     '70e543a626496f719f837e57a798c288', 'ab34d9ff8f1504e949e06d7c51049837', 'bafa9bc81270863eeaba9267412ce854',
                     '27f6b4127a02026ce5bb42a7686a05de', '4ceccf7b8f24316465838c5f97bc06c8', 'bef000f56d1907697a6e0922b2a5184b',
                     '55b2820aec3e9cb8af88e50068620a73', 'f6722d76cca62ebb150c1b79338c2325', 'c74c0c5231a656b95b407e995793b80a',
                     '3398b5e93b96c90557406ca461a55da0', '80cd1440a3b2a4b8f3480ee25e3e4c5d', 'b6429ded63ab3e6d62fb9542dc76a42d',
                     '1e0fdc68fd626fefd1f25bedcb848e23', '124ef47f95171e6d37e1c0e81a36a320', '1fdefb2ed5c3c04a97f8ab792988a599',
                     '61b80d4e7e0b460e5be3a957a8e1cef5', '6948c39ad21d6b986094ccfc0b0b8ee7', '84df2d6c60669f09439c9fb2ca748def',
                     '9207f2fe3454cbd45073ab2e22f82d28', 'b7826380ac8f70f9e2ce190d9bd22823'),
               '9': ('d040ced0ae3a55365fe46b498316d734', '0f518491d0a16f91bd6e4df1f9db47b2', '59a08f18d72d52eed250cc6a88aebd40',
                     '0e474a38e1c330613e406bf738723f01', '4bfe94b095e8c4b391abf42c0a4a8dc6', '1810d4ce38929acaa8a788a35b9b5e5d',
                     'e19ea6338bcbbcaf3e40017bea21c770', '2f2b034747480bdc583335a43b5cdcb7', '15497fc6422cd626d4d3639dbb01aa35',
                     '1bf0815fee3796e0b745207fbcc4e511',)}

    margin = 1
    color = (0xff,0xf7,0xff)
    nrow = 4
    ncol = 4

    def __init__(self, browser, session, codes):
        f = BytesIO(browser.open('%s.jpg' % session).content)

        super(DelubacVirtKeyboard, self).__init__(range(16), self.ncol, self.nrow, f, self.color)

        self.check_symbols(self.symbols, browser.responses_dirname)

        self.codes = codes

    def check_color(self, pixel):
        for p in pixel:
            if p < 0xd0:
                return False
        return True

    def get_string_code(self, string):
        res = []
        ndata = self.nrow * self.ncol
        for nbchar, c in enumerate(string):
            index = self.get_symbol_code(self.symbols[c])

            res.append(self.codes[(nbchar * ndata) + index])
        return ','.join(res)


class LoginPage(HTMLPage):
    VK_CLASS = DelubacVirtKeyboard

    def login(self, username, password):
        for script in self.doc.xpath('//script'):
            m = re.search("session='([^']+)'", script.text or '')
            if m:
                session = m.group(1)
            m = re.search('codes = "([^"]+)"', script.text or '')
            if m:
                codes = m.group(1).split(',')

        vk = self.VK_CLASS(self.browser, session, codes)

        form = self.get_form(name='codeident')

        form['identifiant'] = username
        form['motpasse'] = vk.get_string_code(password)
        form['CodSec'] = vk.get_string_code(password)
        form['modeClavier'] = '1'
        form['identifiantDlg'] = ''

        form.submit()

    def get_vk(self, session, codes):
        return DelubacVirtKeyboard(self.browser, session, codes)

    def on_load(self):
        error_message = CleanText(u'//td[contains(text(), "Votre adhésion au service WEB est résiliée depuis le")]')(self.doc)
        if error_message:
            raise ActionNeeded(error_message)

    @property
    def incorrect_auth(self):
        return len(self.doc.xpath('//td[contains(text(), "Authentification incorrecte")]'))


class MenuPage(LoggedPage, HTMLPage):
    def get_link(self, name):
        for script in self.doc.xpath('//script'):
            m = re.search(r"""\["%s",'([^']+)'""" % name, script.text or '', flags=re.MULTILINE)
            if m:
                return m.group(1)

        raise ParseError('Link %r not found' % name)

    @property
    def accounts_url(self):
        return self.get_link(u'Comptes')
