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

from datetime import date
from collections import OrderedDict
import re

from weboob.capabilities.base import find_object
from weboob.capabilities.bank import Account, AccountNotFound, CapBankTransferAddRecipient
from weboob.capabilities.contact import CapContact
from weboob.capabilities.profile import CapProfile
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value

from .web.browser import Cragr


__all__ = ['CragrModule']


class CragrModule(Module, CapBankTransferAddRecipient, CapContact, CapProfile):
    NAME = 'cragr'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.3'
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
        }.items())])
    CONFIG = BackendConfig(Value('website',  label=u'Région', choices=website_choices),
                           ValueBackendPassword('login',    label=u'N° de compte', masked=False),
                           ValueBackendPassword('password', label=u'Code personnel', regexp=r'\d{6}'))
    BROWSER = Cragr

    COMPAT_DOMAINS = {
        'm.lefil.com': 'm.ca-pyrenees-gascogne.fr',
    }

    def create_default_browser(self):
        site_conf = self.config['website'].get()
        site_conf = self.COMPAT_DOMAINS.get(site_conf, site_conf)
        return self.create_browser(site_conf,
                                   self.config['login'].get(),
                                   self.config['password'].get())

    def iter_accounts(self):
        return self.browser.get_accounts_list()

    def get_account(self, _id):
        return find_object(self.iter_accounts(), id=_id, error=AccountNotFound)

    def _history_filter(self, account, coming):
        today = date.today()

        def to_date(obj):
            if hasattr(obj, 'date'):
                return obj.date()
            return obj

        for tr in self.browser.get_history(account):
            tr_coming = to_date(tr.date) > today
            if coming == tr_coming:
                yield tr

    def iter_history(self, account):
        if account.type == Account.TYPE_CARD:
            return self._history_filter(account, False)
        return self.browser.get_history(account)

    def iter_coming(self, account):
        if account.type == Account.TYPE_CARD:
            return self._history_filter(account, True)
        raise []

    def iter_investment(self, account):
        for inv in self.browser.iter_investment(account):
            yield inv

    def iter_contacts(self):
        return self.browser.iter_advisor()

    def get_profile(self):
        if not hasattr(self.browser, 'get_profile'):
            raise NotImplementedError()
        return self.browser.get_profile()

    def iter_transfer_recipients(self, account):
        if not isinstance(account, Account):
            account = self.get_account(account)

        return self.browser.iter_transfer_recipients(account)

    def init_transfer(self, transfer, **params):
        def to_ascii(s):
            return s.encode('ascii', errors='ignore').decode('ascii')

        if transfer.label:
            transfer.label = re.sub(r'[+!]', '', to_ascii(transfer.label[:33]))

        return self.browser.init_transfer(transfer, **params)

    def execute_transfer(self, transfer, **params):
        return self.browser.execute_transfer(transfer, **params)

    def new_recipient(self, recipient, **params):
        return self.browser.new_recipient(recipient, **params)
