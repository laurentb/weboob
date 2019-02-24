# -*- coding: utf-8 -*-

# Copyright(C) 2012-2013 Romain Bignon
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from collections import OrderedDict
from functools import reduce

from weboob.capabilities.bank import CapBankWealth, AccountNotFound
from weboob.capabilities.contact import CapContact
from weboob.capabilities.profile import CapProfile
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value

from .browser import BanquePopulaire


__all__ = ['BanquePopulaireModule']


class BanquePopulaireModule(Module, CapBankWealth, CapContact, CapProfile):
    NAME = 'banquepopulaire'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.5'
    DESCRIPTION = u'Banque Populaire'
    LICENSE = 'AGPLv3+'
    website_choices = OrderedDict([(k, u'%s (%s)' % (v, k)) for k, v in sorted({
        'www.ibps.alpes.banquepopulaire.fr': u'Alpes',
        'www.ibps.alsace.banquepopulaire.fr': u'Alsace Lorraine Champagne',
        'www.ibps.bpalc.banquepopulaire.fr' : u'Alsace Lorraine Champagne',
        'www.ibps.bpaca.banquepopulaire.fr': u'Aquitaine Centre atlantique',
        'www.ibps.atlantique.banquepopulaire.fr': u'Atlantique',
        'www.ibps.bpgo.banquepopulaire.fr': u'Grand Ouest',
        'www.ibps.loirelyonnais.banquepopulaire.fr': u'Auvergne Rhône Alpes',
        'www.ibps.bpaura.banquepopulaire.fr': u'Auvergne Rhône Alpes',
        'www.ibps.banquedesavoie.banquepopulaire.fr': u'Banque de Savoie',
        'www.ibps.bpbfc.banquepopulaire.fr': u'Bourgogne Franche-Comté',
        'www.ibps.bretagnenormandie.cmm.groupe.banquepopulaire.fr': u'Crédit Maritime Bretagne Normandie',
        'www.ibps.atlantique.creditmaritime.groupe.banquepopulaire.fr': u'Crédit Maritime Atlantique',
        'www.ibps.sudouest.creditmaritime.groupe.banquepopulaire.fr': u'Crédit Maritime du Littoral du Sud-Ouest',
        'www.ibps.lorrainechampagne.banquepopulaire.fr': u'Lorraine Champagne',
        'www.ibps.massifcentral.banquepopulaire.fr': u'Massif central',
        'www.ibps.mediterranee.banquepopulaire.fr': u'Méditerranée',
        'www.ibps.nord.banquepopulaire.fr': u'Nord',
        'www.ibps.occitane.banquepopulaire.fr': u'Occitane',
        'www.ibps.ouest.banquepopulaire.fr': u'Ouest',
        'www.ibps.rivesparis.banquepopulaire.fr': u'Rives de Paris',
        'www.ibps.sud.banquepopulaire.fr': u'Sud',
        'www.ibps.valdefrance.banquepopulaire.fr': u'Val de France',
        }.items(), key=lambda k_v: (k_v[1], k_v[0]))])
    CONFIG = BackendConfig(Value('website',  label=u'Région', choices=website_choices),
                           ValueBackendPassword('login',    label='Identifiant', masked=False),
                           ValueBackendPassword('password', label='Mot de passee'))
    BROWSER = BanquePopulaire

    def create_default_browser(self):
        repls = [
            ('alsace', 'bpalc'),
            ('lorrainechampagne', 'bpalc'),
            ('loirelyonnais', 'bpaura'),
            ('alpes', 'bpaura'),
            ('massifcentral', 'bpaura'),
            ('atlantique.creditmaritime', 'cmgo.creditmaritime'),
            ('bretagnenormandie.cmm', 'cmgo'),
            ('atlantique.banquepopulaire', 'bpgo.banquepopulaire'),
            ('ouest.banquepopulaire', 'bpgo.banquepopulaire'),
        ]
        website = reduce(lambda a, kv: a.replace(*kv), repls, self.config['website'].get())
        return self.create_browser(website,
                                   self.config['login'].get(),
                                   self.config['password'].get(),
                                   weboob=self.weboob)

    def iter_accounts(self):
        return self.browser.get_accounts_list()

    def get_account(self, _id):
        account = self.browser.get_account(_id)
        if account:
            return account
        else:
            raise AccountNotFound()

    def iter_history(self, account):
        return self.browser.get_history(account)

    def iter_coming(self, account):
        return self.browser.get_history(account, coming=True)

    def iter_investment(self, account):
        return self.browser.get_investment(account)

    def iter_contacts(self):
        return self.browser.get_advisor()

    def get_profile(self):
        return self.browser.get_profile()
