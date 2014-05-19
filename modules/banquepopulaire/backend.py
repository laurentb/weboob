# -*- coding: utf-8 -*-

# Copyright(C) 2012-2013 Romain Bignon
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


from weboob.capabilities.bank import ICapBank, AccountNotFound
from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.ordereddict import OrderedDict
from weboob.tools.value import ValueBackendPassword, Value

from .browser import BanquePopulaire


__all__ = ['BanquePopulaireBackend']


class BanquePopulaireBackend(BaseBackend, ICapBank):
    NAME = 'banquepopulaire'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '0.j'
    DESCRIPTION = u'Banque Populaire'
    LICENSE = 'AGPLv3+'
    website_choices = OrderedDict([(k, u'%s (%s)' % (v, k)) for k, v in sorted({
        'www.ibps.alpes.banquepopulaire.fr': u'Alpes',
        'www.ibps.alsace.banquepopulaire.fr': u'Alsace',
        'www.ibps.bpaca.banquepopulaire.fr': u'Aquitaine Centre atlantique',
        'www.ibps.atlantique.banquepopulaire.fr': u'Atlantique',
        'www.ibps.bpbfc.banquepopulaire.fr': u'Bourgogne-Franche Comté',
        'www.ibps.bretagnenormandie.cmm.groupe.banquepopulaire.fr': u'Crédit Maritime Bretagne Normandie',
        'www.ibps.atlantique.creditmaritime.groupe.banquepopulaire.fr': u'Crédit Maritime Atlantique',
        'www.ibps.sudouest.creditmaritime.groupe.banquepopulaire.fr': u'Crédit Maritime du Littoral du Sud-Ouest',
        'www.ibps.cotedazur.banquepopulaire.fr': u'Côte d\'azur',
        'www.ibps.loirelyonnais.banquepopulaire.fr': u'Loire et Lyonnais',
        'www.ibps.lorrainechampagne.banquepopulaire.fr': u'Lorraine Champagne',
        'www.ibps.massifcentral.banquepopulaire.fr': u'Massif central',
        'www.ibps.nord.banquepopulaire.fr': u'Nord',
        'www.ibps.occitane.banquepopulaire.fr': u'Occitane',
        'www.ibps.ouest.banquepopulaire.fr': u'Ouest',
        'www.ibps.provencecorse.banquepopulaire.fr': u'Provence et Corse',
        'www.ibps.rivesparis.banquepopulaire.fr': u'Rives de Paris',
        'www.ibps.sud.banquepopulaire.fr': u'Sud',
        'www.ibps.valdefrance.banquepopulaire.fr': u'Val de France',
        }.iteritems(), key=lambda (k, v): (v, k))])
    CONFIG = BackendConfig(Value('website',  label=u'Région', choices=website_choices),
                           ValueBackendPassword('login',    label='Identifiant', masked=False),
                           ValueBackendPassword('password', label='Mot de passee'))
    BROWSER = BanquePopulaire

    def create_default_browser(self):
        return self.create_browser(self.config['website'].get(),
                                   self.config['login'].get(),
                                   self.config['password'].get())

    def iter_accounts(self):
        with self.browser:
            return self.browser.get_accounts_list()

    def get_account(self, _id):
        with self.browser:
            account = self.browser.get_account(_id)

        if account:
            return account
        else:
            raise AccountNotFound()

    def iter_history(self, account):
        with self.browser:
            return self.browser.get_history(account)

    def iter_coming(self, account):
        with self.browser:
            return self.browser.get_history(account, coming=True)
