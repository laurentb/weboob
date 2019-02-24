# -*- coding: utf-8 -*-

# Copyright(C) 2013-2014      Florent Fourcot
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

from weboob.capabilities.parcel import Event, ParcelNotFound
from weboob.browser import PagesBrowser, URL
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.standard import CleanText, Date, Eval, Regexp
from weboob.browser.pages import HTMLPage
from weboob.browser.profiles import Firefox


__all__ = ['ColissimoBrowser']


class TrackingPage(HTMLPage):
    @method
    class iter_infos(ListElement):
        item_xpath = '//div[has-class("results-suivi")]//table/tbody/tr'

        class item(ItemElement):
            klass = Event

            obj_date = Date(CleanText('td[1]'), dayfirst=True)
            obj_activity = CleanText('td[2]')
            obj_location = Eval(
                lambda a, b: a or b,
                Regexp(
                    CleanText('td[3]//a/@title'),
                    r"Horaires et adresse - (.+)",
                    r"\1",
                    default=None
                ),
                CleanText('td[3]'),
            )

    def get_error(self):
        return CleanText('//div[has-class("error-suivi")]')(self.doc)


class ColissimoBrowser(PagesBrowser):
    BASEURL = 'https://www.laposte.fr'
    PROFILE = Firefox()

    tracking_url = URL('/particulier/outils/suivre-vos-envois\?code=(?P<_id>.*)', TrackingPage)

    def get_tracking_info(self, _id):
        self.tracking_url.stay_or_go(_id=_id)
        events = list(self.page.iter_infos())
        if len(events) == 0:
            error = self.page.get_error()
            raise ParcelNotFound(u"Parcel not found: {}".format(error))
        return events
