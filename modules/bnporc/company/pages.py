# -*- coding: utf-8 -*-

# Copyright(C) 2015      Baptiste Delpey
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

# yapf-compatible

from __future__ import unicode_literals

from io import BytesIO
import hashlib
from decimal import Decimal
from datetime import datetime

from weboob.capabilities.bank import Account
from weboob.exceptions import BrowserIncorrectPassword
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.browser.pages import HTMLPage, JsonPage, LoggedPage
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard, VirtKeyboardError


class BNPVirtKeyboard(MappedVirtKeyboard):
    symbols = {
        '0': 'ff069462836e30a39c911034048f5bb3',
        '1': '7969f04e4e82eaefa2ce7a9a23c26178',
        '2': '1e6020f97ca1c3ce3da4f39ded15d67d',
        '3': 'f84284b40aea93c24814e23e14e76cc8',
        '4': '88bab262d4b344c0ef8f06ddd01adbcf',
        '5': '0a270764fc5d8334bcb55053432b26cb',
        '6': 'e6a4444a6c752cd3e655f2883e530080',
        '7': '933d4ca5df6b2b3df2dea00a21a3fed6',
        '8': ['f28b918777d21a5fde2bffb9899e2138', 'a97e6e27159084d50f8ef00548b70252'],
        '9': 'be751b77af0d998ab4c2cfd38455b2a6',
    }

    color = (0, 0, 0)

    def __init__(self, basepage):
        img = basepage.doc.xpath('//img[@id="gridpass_img"]')[0]
        imgdata = basepage.browser.open(img.attrib['src']).content
        MappedVirtKeyboard.__init__(self, BytesIO(imgdata), basepage.doc, img, self.color, convert='RGB')
        self.check_symbols(self.symbols, basepage.browser.responses_dirname)

    def get_symbol_code(self, md5sum):
        code = MappedVirtKeyboard.get_symbol_code(self, md5sum)
        code = code.split("'")[3]
        assert code.isdigit()
        return code

    def check_color(self, pixel):
        for p in pixel:
            if p >= 200:
                return False
        return True

    def checksum(self, coords):
        """Copy of parent checksum(), but cropping (removes empty lines)"""
        x1, y1, x2, y2 = coords
        s = ''
        for y in range(y1, min(y2 + 1, self.height)):
            for x in range(x1, min(x2 + 1, self.width)):
                if self.check_color(self.pixar[x, y]):
                    s += " "
                else:
                    s += "O"
            s += "\n"
        s = '\n'.join([l for l in s.splitlines() if l.strip()])
        return hashlib.md5(s).hexdigest()


class LoginPage(HTMLPage):
    def login(self, login, password):
        try:
            vk = BNPVirtKeyboard(self)
        except VirtKeyboardError as err:
            self.logger.error("Error: %s" % err)
            return False

        form = self.get_form(name='loginPwdForm')
        form['txtAuthentMode'] = 'PASSWORD'
        form['txtPwdUserId'] = login
        form['gridpass_hidden_input'] = vk.get_string_code(password)
        form.submit()

    def on_load(self):
        if self.doc.xpath('//p[contains(text(), "Your identification is wrong.")]'):
            raise BrowserIncorrectPassword("Your identification is wrong.")


class AccountsPage(LoggedPage, JsonPage):
    FAMILY_TO_TYPE = {
        u"Compte chèque": Account.TYPE_CHECKING,
    }

    def iter_accounts(self):
        for f in self.path('tableauSoldes.listeGroupes'):
            for g in f:
                for a in g.get('listeComptes'):
                    yield Account.from_dict({
                        'id': a.get('numeroCompte'),
                        'iban': a.get('numeroCompte'),
                        'type': self.FAMILY_TO_TYPE.get(a.get('libelleType')) or Account.TYPE_UNKNOWN,
                        'label': '%s %s' % (a.get('libelleType'), a.get('libelleTitulaire')),
                        'currency': a.get('deviseTenue'),
                        'balance': Decimal(a.get('soldeComptable')) / 100,
                        'coming': Decimal(a.get('soldePrevisionnel')) / 100,
                    })


class HistoryPage(LoggedPage, JsonPage):
    CODE_TO_TYPE = {
        "AUTOP": FrenchTransaction.TYPE_UNKNOWN, # Autres opérations,
        "BOURS": FrenchTransaction.TYPE_BANK, # Bourse / Titres,
        "CARTE": FrenchTransaction.TYPE_CARD, # Cartes,
        "CHEQU": FrenchTransaction.TYPE_CHECK, # Chèques,
        "CREDD": FrenchTransaction.TYPE_UNKNOWN, # Crédits documentaires,
        "CREDI": FrenchTransaction.TYPE_UNKNOWN, # Crédits,
        "EFFET": FrenchTransaction.TYPE_UNKNOWN, # Effets,
        "ESPEC": FrenchTransaction.TYPE_UNKNOWN, # Espèces,
        "FACCB": FrenchTransaction.TYPE_UNKNOWN, # Factures / Retraits cartes,
        "ICHEQ": FrenchTransaction.TYPE_UNKNOWN, # Impayés chèques,
        "IEFFE": FrenchTransaction.TYPE_UNKNOWN, # Impayés et incidents effets,
        "IMPAY": FrenchTransaction.TYPE_UNKNOWN, # Impayés et rejets,
        "IPRLV": FrenchTransaction.TYPE_UNKNOWN, # Impayés prélèvements, TIP et télérèglements,
        "PRLVT": FrenchTransaction.TYPE_UNKNOWN, # Prélèvements, TIP et télérèglements,
        "REMCB": FrenchTransaction.TYPE_UNKNOWN, # Remises cartes,
        "RJVIR": FrenchTransaction.TYPE_ORDER, # Rejets de virements,
        "VIREM": FrenchTransaction.TYPE_ORDER, # Virements,
        "VIRIT": FrenchTransaction.TYPE_ORDER, # Virements internationaux,
        "VIRSP": FrenchTransaction.TYPE_ORDER, # Virements européens,
        "VIRTR": FrenchTransaction.TYPE_ORDER, # Virements de trésorerie,
        "VIRXX": FrenchTransaction.TYPE_ORDER, # Autres virements
    }

    def one(self, path, context=None):
        try:
            return list(self.path(path, context))[0]
        except IndexError:
            return None

    def iter_history(self):
        for op in self.get('mouvementsBDDF'):
            codeFamille = self.one('nature.codefamille', op)
            tr = FrenchTransaction.from_dict({
                'id': op.get('id'),
                'type': self.CODE_TO_TYPE.get(codeFamille) or FrenchTransaction.TYPE_UNKNOWN,
                'category': self.one('nature.libelle', op),
                'raw': ' '.join(op.get('libelle').split()) or op.get('nature')['libelle'],
                'date': datetime.fromtimestamp(op.get('dateOperation') / 1000),
                'vdate': datetime.fromtimestamp(op.get('dateValeur') / 1000),
                'amount': Decimal(self.one('montant.montant', op)) / 100,
            })
            yield tr
