# -*- coding: utf-8 -*-

# Copyright(C) 2017      Mickaël Thomas
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

from dateutil.parser import parse as parse_date

from weboob.capabilities.parcel import Event, ParcelNotFound
from weboob.browser.browsers import DomainBrowser


__all__ = ['RelaiscolisBrowser']


class RelaiscolisBrowser(DomainBrowser):
    BASEURL = 'https://www.relaiscolis.com'

    def iter_events(self, merchant, code, name):
        data = dict(
            codeEnseigne=merchant,
            nomClient=name,
            typeRecherche='EXP',
            valeur=code
        )
        # Ref: https://www.relaiscolis.com/js/lib/suivi.js
        req = self.open('/suivi-de-colis/index/tracking/', data=data)
        resp = None
        try:
            resp = req.json()
            if resp and 'error' in resp:
                raise ParcelNotFound(resp['error']['msg'])
        except (ValueError, KeyError):
            self.raise_for_status(req)
            raise
        else:
            self.raise_for_status(req)

        def ensure_list(data):
            if isinstance(data, list):
                return data
            return [data]

        parcel_data = ensure_list(resp['Colis']['Colis'])[-1]
        events_data = ensure_list(parcel_data['ListEvenements'].get('Evenement', []))

        final_location = None
        try:
            relay = resp['Relais']['Relais']
            name = relay['Nom'].strip()
            city = relay['Commune'].strip()
            final_location = ' '.join((name, city))
        except KeyError:
            pass

        for event_data in events_data:
            event = Event()
            event.date = parse_date(event_data['Date'].strip())
            event.activity = event_data['Libelle'].strip()

            if final_location and (
                    "Votre colis est disponible" in event.activity):
                event.location = final_location
            yield event

    def get_merchants(self):
        req = self.open('/suivi-de-colis/index/getEnseignes/')
        resp = req.json()

        return OrderedDict(
            (merchant['Code'], '{Nom} ({Code})'.format(**merchant))
            for merchant in resp
            if merchant['Nom']
        )
