# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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

from weboob.capabilities.base import UserError
from weboob.browser import PagesBrowser, URL
from .pages import FilmsPage, EventPage, JsonResumePage
from weboob.browser.profiles import Firefox

__all__ = ['SenscritiqueBrowser']


class SenscritiqueBrowser(PagesBrowser):

    BASEURL = 'https://www.senscritique.com'

    films_page = URL('/everymovie/programme-tv/cette-semaine', FilmsPage)
    event_page = URL('/film/(?P<_id>.*)', EventPage)
    json_page = URL('/sc2/product/storyline/(?P<_id>.*).json', JsonResumePage)

    def set_json_header(self):
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows; U; Windows "
                                     "NT 5.1; en-US; rv:1.9.2.8) Gecko/20100722 Firefox/3.6.8"
                                     " GTB7.1 (.NET CLR 3.5.30729)",
                                     "Accept": "application/json, text/javascript, */*; q=0.01",
                                     "X-Requested-With": "XMLHttpRequest",
                                     })

    def list_events(self, date_from, date_to=None):
        return self.films_page.go().iter_films(date_from=date_from, date_to=date_to)

    def get_event(self, _id, event=None):
        if not event:
            try:
                event = self.films_page.go().iter_films(_id=_id).next()
            except StopIteration:
                raise UserError('This event (%s) does not exists' % _id)

        film_id = _id.split('#')[0]
        event = self.event_page.go(_id=film_id).get_event(obj=event)
        resume = self.get_resume(film_id)
        event.description += resume
        return event

    def get_resume(self, film_id):
        self.set_json_header()
        _id = film_id.split('/')[-1]
        resume = self.json_page.go(_id=_id).get_resume()
        self.set_profile(Firefox())
        return resume if resume else ''
