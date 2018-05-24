# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Vincent Paredes
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

from __future__ import unicode_literals

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.capabilities.profile import Profile
from weboob.browser.filters.standard import CleanText, Format


class ProfilePage(LoggedPage, HTMLPage):
    def get_profile(self):
        pr = Profile()
        pr.email = CleanText('//span[contains(@class, "panelAccount-label") and strong[contains(text(), "Adresse email")]]/following::span[1]/strong')(self.doc)

        if 'Informations indisponibles' not in CleanText('//div[contains(@id, "Address")]')(self.doc):
            pr.address = (
                CleanText('//div[contains(@id, "Address")]//div[@class="ec-blocAddress text-primary"]')(self.doc)
                or CleanText('//div[contains(@class, "addressLine")][1]//span[@class]')(self.doc)
                or CleanText('//div[contains(@class, "row ec-blocAddressList")]')(self.doc)
            )

        phone = CleanText('//span[contains(@class, "panelAccount-label") and strong[contains(text(), "Numéro de mobile")]]/following::span[1]')(self.doc)
        if 'non renseigné' not in phone:
            pr.phone = phone

        # Civilé
        # Nom
        # Prénom
        if CleanText('//p[contains(@class, "panelAccount-label")]/span[strong[contains(text(), "Civilité")]]')(self.doc):
            pr.name = Format('%s %s %s',
                             CleanText('//p[contains(@class, "panelAccount-label")]/span[strong[contains(text(), "Civilité")]]/following::span[1]'),
                             CleanText('//p[contains(@class, "panelAccount-label")]/span[strong[contains(text(), "Nom :")]]/following::span[1]'),
                             CleanText('//p[contains(@class, "panelAccount-label")]/span[strong[contains(text(), "Prénom :")]]/following::span[1]')
                             )(self.doc)
        # Prénom / Nom
        elif CleanText('//p[contains(@class, "panelAccount-label")]/span[strong[contains(text(), "Prénom / Nom")]]')(self.doc):
            pr.name = CleanText('//p[contains(@class, "panelAccount-label")]/span[strong[contains(text(), "Prénom / Nom")]]/following::span[1]')(self.doc)
        # Nom
        else:
            pr.name = CleanText('//p[contains(@class, "panelAccount-label")]/span[strong[text()="Nom :"]]/following::span[1]')(self.doc)

        return pr
