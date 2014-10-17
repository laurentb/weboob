# -*- coding: utf-8 -*-

# Copyright(C) 2010-2013 Xavier Guerrin
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


from weboob.capabilities.bank import CapBank, AccountNotFound
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.ordereddict import OrderedDict
from weboob.tools.value import ValueBackendPassword, Value

from .web.browser import Cragr
from .mobile.browser import CragrMobile


__all__ = ['CragrModule']


class CragrModule(Module, CapBank):
    NAME = 'cragr'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.1'
    DESCRIPTION = u'Crédit Agricole'
    LICENSE = 'AGPLv3+'
    website_choices = OrderedDict([(k, u'%s (%s)' % (v, k)) for k, v in sorted({
        'm.ca-alpesprovence.fr': u'Alpes Provence',
        'm.ca-alsace-vosges.fr': u'Alsace-Vosges',
        'm.ca-anjou-maine.fr': u'Anjou Maine',
        'm.ca-aquitaine.fr': u'Aquitaine',
        'm.ca-atlantique-vendee.fr': u'Atlantique Vendée',
        'm.ca-briepicardie.fr': u'Brie Picardie',
        'm.ca-cb.fr': u'Champagne Bourgogne',
        'm.ca-centrefrance.fr': u'Centre France',
        'm.ca-centreloire.fr': u'Centre Loire',
        'm.ca-centreouest.fr': u'Centre Ouest',
        'm.ca-centrest.fr': u'Centre Est',
        'm.ca-charente-perigord.fr': u'Charente Périgord',
        'm.ca-cmds.fr': u'Charente-Maritime Deux-Sèvres',
        'm.ca-corse.fr': u'Corse',
        'm.ca-cotesdarmor.fr': u'Côtes d\'Armor',
        'm.ca-des-savoie.fr': u'Des Savoie',
        'm.ca-finistere.fr': u'Finistere',
        'm.ca-franchecomte.fr': u'Franche-Comté',
        'm.ca-guadeloupe.fr': u'Guadeloupe',
        'm.ca-illeetvilaine.fr': u'Ille-et-Vilaine',
        'm.ca-languedoc.fr': u'Languedoc',
        'm.ca-loirehauteloire.fr': u'Loire Haute Loire',
        'm.ca-lorraine.fr': u'Lorraine',
        'm.ca-martinique.fr': u'Martinique Guyane',
        'm.ca-morbihan.fr': u'Morbihan',
        'm.ca-nmp.fr': u'Nord Midi-Pyrénées',
        'm.ca-nord-est.fr': u'Nord Est',
        'm.ca-norddefrance.fr': u'Nord de France',
        'm.ca-normandie-seine.fr': u'Normandie Seine',
        'm.ca-normandie.fr': u'Normandie',
        'm.ca-paris.fr': u'Ile-de-France',
        'm.ca-pca.fr': u'Provence Côte d\'Azur',
        'm.ca-reunion.fr': u'Réunion',
        'm.ca-sudmed.fr': u'Sud Méditerranée',
        'm.ca-sudrhonealpes.fr': u'Sud Rhône Alpes',
        'm.ca-toulouse31.fr': u'Toulouse 31', # m.ca-toulousain.fr redirects here
        'm.ca-tourainepoitou.fr': u'Tourraine Poitou',
        'm.ca-valdefrance.fr': u'Val de France',
        'm.lefil.com': u'Pyrénées Gascogne',
        }.iteritems())])
    CONFIG = BackendConfig(Value('website',  label=u'Région', choices=website_choices),
                           ValueBackendPassword('login',    label=u'N° de compte', masked=False),
                           ValueBackendPassword('password', label=u'Code personnel', regexp=r'\d{6}'))
    BROWSER = Cragr

    def create_default_browser(self):
        try:
            return self.create_browser(self.config['website'].get(),
                                       self.config['login'].get(),
                                       self.config['password'].get())
        except Cragr.WebsiteNotSupported:
            self.logger.debug('falling-back on mobile version')
            self.BROWSER = CragrMobile
            return self.create_browser(self.config['website'].get(),
                                       self.config['login'].get(),
                                       self.config['password'].get())

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

    def transfer(self, account, to, amount, reason=None):
        return self.browser.do_transfer(account, to, amount, reason)
