# -*- coding: utf-8 -*-

# Copyright(C) 2018 Quentin Defenouillere
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.


from __future__ import unicode_literals


from weboob.browser import URL, LoginBrowser, need_login
from .pages import BandPage, SearchBandsPage, LoginPage, FavoritesPage, SuggestionsPage, AlbumPage

__all__ = ['MetalArchivesBrowser']

class MetalArchivesBrowser(LoginBrowser):
    """
    Browsing the Metal Archives website.
    """

    BASEURL = 'https://www.metal-archives.com/'
    login = URL('authentication/login', LoginPage)
    bands = URL('search/ajax-band-search/\?field=name&query=(?P<pattern>.*)', SearchBandsPage)
    band = URL('bands/Band/(?P<band_id>.*)', BandPage)
    albums = URL('band/discography/id/(?P<band_id>.*)/tab/all', AlbumPage)
    favorites = URL('bookmark/ajax-list/type/band\?sEcho=1', FavoritesPage)
    suggested = URL('band/ajax-recommendations/id/(?P<band_id>.*)\?showMoreSimilar=1', SuggestionsPage)

    def do_login(self):
        d = {
            'loginUsername': self.username,
            'loginPassword': self.password
        }
        self.login.go(data=d)

    def iter_band_search(self, pattern):
        for band in self.bands.go(pattern=pattern).iter_bands():
            yield band

    def get_info(self, id):
        return self.band.go(band_id=id).get_info()

    def get_albums(self, id):
        for album in self.albums.go(band_id=id).iter_albums():
            yield album

    @need_login
    def get_favorites(self):
        for favorite in self.favorites.go().iter_favorites():
            yield favorite

    @need_login
    def get_suggestions(self, bands):
        return self.suggested.go().iter_suggestions()

    @need_login
    def suggestions(self, band_list):
        # Offers band suggestions depending on your favorite bands.
        if not band_list:
            self.logger.warning('In order to get band suggestions, you first need to add some favorite artists of the Metal Archives website.')
            return

        similar_bands = []
        for band in band_list:
            # Gets all the similar artists of your favorite bands:
            similar_bands.extend(self.suggested.go(band_id=band).iter_suggestions())

        if not similar_bands:
            self.logger.warning('Your favorite artists did not contain any similar bands.')
            return

        suggestions = {}
        suggested_bands = {}
        for band in similar_bands:
            if band.id in band_list:
                # Skip the artists that are already in the favorite band list
                continue
            else:
                # Adds the similar artist to the suggestions dictionary if it is not already in the favorite bands:
                if band.url not in suggestions:
                    # Creates a counter for each new similar artist in the suggestions:
                    suggestions[band.url] = 1
                    suggested_bands[band.url] = band
                else:
                    # Increments '+1' if the similar artist is already in the suggestions:
                    suggestions[band.url] += 1

        suggestion_list = []
        for band in range(13):  # This maximum can be modified if you want more or less band suggestions
            best_suggestion = max(suggestions, key=suggestions.get)
            suggestion_list.append(suggested_bands.get(best_suggestion))
            suggestions.pop(best_suggestion)

        assert suggestion_list, 'Failed to return any suggestions from your favorite artists.'

        # The top 13 similar artists to your favorite bands
        for band in suggestion_list:
            yield band
