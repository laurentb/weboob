# -*- coding: utf-8 -*-

from weboob.tools.capabilities.bank.transactions import FrenchTransaction

import re

class Transaction(FrenchTransaction):
    PATTERNS = [
        # Money arrives on the account:
        (re.compile('^VIR\. O/ .* MOTIF: ?(?P<text>.*)$'), FrenchTransaction.TYPE_TRANSFER),
        # Money leaves the account:
        (re.compile('^.* VIREMENT SEPA FAVEUR (?P<text>.*)$'), FrenchTransaction.TYPE_TRANSFER),
        # Taxes
        (re.compile('^TAXE SUR .*$'), FrenchTransaction.TYPE_BANK),
        (re.compile(u'^Prélèvements Sociaux.*$'), FrenchTransaction.TYPE_BANK),
        # Interest income
        (re.compile(u'^Intérêts Créditeurs.*$'), FrenchTransaction.TYPE_BANK),
        (re.compile(u'^REMISE DE CHEQUES.*$'), FrenchTransaction.TYPE_DEPOSIT),
        (re.compile(u'^VIREMENT D\'ORDRE DE LA NEF.*$'), FrenchTransaction.TYPE_DEPOSIT),
        (re.compile(u'^MISE A JOUR STOCK.*$'), FrenchTransaction.TYPE_ORDER)
    ]
