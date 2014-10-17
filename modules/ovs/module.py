# -*- coding: utf-8 -*-

# Copyright(C) 2013      Vincent A
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

from weboob.tools.backend import Module, BackendConfig
from weboob.deprecated.browser import BrowserForbidden
from weboob.tools.value import Value, ValueBackendPassword
from weboob.capabilities.messages import CapMessages, CapMessagesPost, Message
from weboob.capabilities.contact import CapContact

from .browser import OvsBrowser


__all__ = ['OvsModule']


CITIES = {u'agen': u'Agen', u'ajaccio': u'Ajaccio', u'albi': u'Albi', u'amiens': u'Amiens',
          u'angers': u'Angers', u'angouleme': u'Angoul\xeame', u'annecy': u'Annecy', u'aurillac': u'Aurillac',
          u'auxerre': u'Auxerre', u'avignon': u'Avignon', u'bastia': u'Bastia', u'beauvais': u'Beauvais',
          u'belfort': u'Belfort', u'bergerac': u'Bergerac', u'besancon': u'Besan\xe7on',
          u'beziers': u'B\xe9ziers', u'biarritz': u'Biarritz', u'blois': u'Blois', u'bordeaux': u'Bordeaux',
          u'bourg-en-bresse': u'M\xe2con', u'bourges': u'Bourges', u'brest': u'Brest',
          u'brive-la-gaillarde': u'Brive', u'bruxelles': u'Bruxelles', u'caen': u'Caen',
          u'calais': u'Boulogne', u'carcassonne': u'Carcassonne', u'chalon-sur-saone': u'Chalon',
          u'chambery': u'Albertville', u'chantilly': u'Chantilly', u'charleroi': u'Charleroi',
          u'charleville-mezieres': u'Charleville', u'chartres': u'Chartres', u'chateauroux': u'Ch\xe2teauroux',
          u'cherbourg': u'Cherbourg', u'cholet': u'Cholet', u'clermont-ferrand': u'Clt-Ferrand',
          u'compiegne': u'Compi\xe8gne', u'dieppe': u'Dieppe', u'dijon': u'Dijon',
          u'dunkerque': u'Dunkerque', u'evreux': u'Evreux', u'frejus': u'Fr\xe9jus', u'gap': u'Gap',
          u'geneve': u'Gen\xe8ve', u'grenoble': u'Grenoble', u'la-roche-sur-yon': u'La Roche/Yon',
          u'la-rochelle': u'La Rochelle', u'lausanne': u'Lausanne', u'laval': u'Laval',
          u'le-havre': u'Le Havre', u'le-mans': u'Alen\xe7on', u'liege': u'Li\xe8ge', u'lille': u'Lille',
          u'limoges': u'Limoges', u'lorient': u'Lorient', u'luxembourg': u'Luxembourg', u'lyon': u'Lyon',
          u'marseille': u'Aix', u'metz': u'Metz', u'mons': u'Mons', u'mont-de-marsan': u'Mont de Marsan',
          u'montauban': u'Montauban', u'montlucon': u'Montlu\xe7on', u'montpellier': u'Montpellier',
          u'mulhouse': u'Colmar', u'namur': u'Namur', u'nancy': u'Nancy', u'nantes': u'Nantes',
          u'nevers': u'Nevers', u'nice': u'Cannes', u'nimes': u'N\xeemes', u'niort': u'Niort',
          u'orleans': u'Orl\xe9ans', u'paris': u'PARIS', u'pau': u'Pau', u'perigueux': u'P\xe9rigueux',
          u'perpignan': u'Perpignan', u'poitiers': u'Poitiers', u'quimper': u'Quimper', u'reims': u'Reims',
          u'rennes': u'Rennes', u'roanne': u'Roanne', u'rodez': u'Rodez', u'rouen': u'Rouen',
          u'saint-brieuc': u'St-Brieuc', u'saint-etienne': u'St-Etienne', u'saint-malo': u'St-Malo',
          u'saint-nazaire': u'St-Nazaire', u'saint-quentin': u'St-Quentin', u'saintes': u'Saintes',
          u'strasbourg': u'Strasbourg', u'tarbes': u'Tarbes', u'toulon': u'Toulon', u'toulouse': u'Toulouse',
          u'tours': u'Tours', u'troyes': u'Troyes', u'valence': u'Mont\xe9limar', u'vannes': u'Vannes',
          u'zurich': u'Zurich'}


class OvsModule(Module, CapMessages, CapMessagesPost, CapContact):
    NAME = 'ovs'
    DESCRIPTION = u'OnVaSortir website. Handles private messages only'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    VERSION = '1.1'

    CONFIG = BackendConfig(Value('username',                label='Username', default=''),
                           ValueBackendPassword('password', label='Password', default=''),
                           Value('city',                    label='City (subdomain)', default='paris', choices=CITIES))

    BROWSER = OvsBrowser

    STORAGE = {'seen': {}}

    def create_default_browser(self):
        return self.create_browser(self.config['city'].get(),
                                   self.config['username'].get(),
                                   self.config['password'].get(),
                                   parser='raw')

    # CapMessages
    def iter_threads(self):
        with self.browser:
            for thread in self.browser.iter_threads_list():
                yield thread

    def get_thread(self, id):
        with self.browser:
            thread = self.browser.get_thread(id)

            messages = [thread.root] + thread.root.children
            for message in messages:
                if not self.storage.get('seen', message.full_id, default=False):
                    message.flags |= Message.IS_UNREAD

            return thread

    def iter_unread_messages(self):
        with self.browser:
            for thread in self.iter_threads():
                # TODO reuse thread object?
                thread2 = self.get_thread(thread.id)
                messages = [thread2.root] + thread2.root.children
                for message in messages:
                    if message.flags & Message.IS_UNREAD:
                        yield message
        # TODO implement more efficiently by having a "last weboob seen" for
        # a thread and query a thread only if "last activity" returned by web
        # is later than "last weboob seen"

    def set_message_read(self, message):
        self.storage.set('seen', message.full_id, True)
        self.storage.save()

    # CapMessagesPost
    def post_message(self, message):
        if not self.browser.username:
            raise BrowserForbidden()

        with self.browser:
            thread = message.thread

            if message.parent:
                # ovs.<threadid>@*
                self.browser.post_to_thread(thread.id, message.title, message.content)
            else:
                # ovs.<recipient>@*
                self.browser.create_thread(thread.id, message.title, message.content)

    # CapContact
    def get_contact(self, id):
        return self.browser.get_contact(id)

# FIXME known bug: parsing is done in "boosted mode" which is automatically disable after some time, the "boosted mode" should be re-toggled often

# TODO support outing comments, forum messages
# TODO make an CapOuting?
