# -*- coding: utf-8 -*-

# Copyright(C) 2013 Julien Veyssier
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
import re

from weboob.capabilities.base import UserError
from weboob.capabilities.calendar import CATEGORIES, BaseCalendarEvent, CapCalendarEvent
from weboob.capabilities.cinema import CapCinema, Movie, Person
from weboob.capabilities.collection import CapCollection, Collection, CollectionNotFound
from weboob.capabilities.video import BaseVideo, CapVideo
from weboob.tools.backend import Module
from weboob.tools.compat import unicode

from .browser import AllocineBrowser

__all__ = ['AllocineModule']


class AllocineModule(Module, CapCinema, CapVideo, CapCalendarEvent, CapCollection):
    NAME = 'allocine'
    MAINTAINER = u'Julien Veyssier'
    EMAIL = 'julien.veyssier@aiur.fr'
    VERSION = '2.0'
    DESCRIPTION = u'AlloCiné French cinema database service'
    LICENSE = 'AGPLv3+'
    BROWSER = AllocineBrowser
    ASSOCIATED_CATEGORIES = [CATEGORIES.CINE]

    def get_movie(self, id):
        return self.browser.get_movie(id)

    def get_person(self, id):
        return self.browser.get_person(id)

    def iter_movies(self, pattern):
        return self.browser.iter_movies(pattern.encode('utf-8'))

    def iter_persons(self, pattern):
        return self.browser.iter_persons(pattern.encode('utf-8'))

    def iter_movie_persons(self, id, role=None):
        return self.browser.iter_movie_persons(id, role)

    def iter_person_movies(self, id, role=None):
        return self.browser.iter_person_movies(id, role)

    def iter_person_movies_ids(self, id):
        return self.browser.iter_person_movies_ids(id)

    def iter_movie_persons_ids(self, id):
        return self.browser.iter_movie_persons_ids(id)

    def get_person_biography(self, id):
        return self.browser.get_person_biography(id)

    def get_movie_releases(self, id, country=None):
        return self.browser.get_movie_releases(id, country)

    def fill_person(self, person, fields):
        if 'real_name' in fields or 'birth_place' in fields\
            or 'death_date' in fields or 'nationality' in fields\
            or 'short_biography' in fields or 'roles' in fields\
            or 'birth_date' in fields or 'thumbnail_url' in fields\
            or 'biography' in fields\
                or 'gender' in fields or fields is None:
            per = self.get_person(person.id)
            person.real_name = per.real_name
            person.birth_date = per.birth_date
            person.death_date = per.death_date
            person.birth_place = per.birth_place
            person.gender = per.gender
            person.nationality = per.nationality
            person.short_biography = per.short_biography
            person.short_description = per.short_description
            person.roles = per.roles
            person.biography = per.biography
            person.thumbnail_url = per.thumbnail_url

        return person

    def fill_movie(self, movie, fields):
        if 'other_titles' in fields or 'release_date' in fields\
            or 'duration' in fields or 'country' in fields\
            or 'roles' in fields or 'note' in fields\
                or 'thumbnail_url' in fields:
            mov = self.get_movie(movie.id)
            movie.other_titles = mov.other_titles
            movie.release_date = mov.release_date
            movie.duration = mov.duration
            movie.pitch = mov.pitch
            movie.country = mov.country
            movie.note = mov.note
            movie.roles = mov.roles
            movie.genres = mov.genres
            movie.short_description = mov.short_description
            movie.thumbnail_url = mov.thumbnail_url

        if 'all_release_dates' in fields:
            movie.all_release_dates = self.get_movie_releases(movie.id)

        return movie

    def fill_video(self, video, fields):
        if 'url' in fields:
            if not isinstance(video, BaseVideo):
                video = self.get_video(self, video.id)

            if hasattr(video, '_video_code'):
                video.url = unicode(self.browser.get_video_url(video._video_code))

        if 'thumbnail' in fields and video and video.thumbnail:
            video.thumbnail.data = self.browser.open(video.thumbnail.url)
        return video

    def get_video(self, _id):
        split_id = _id.split('#')
        if split_id[-1] == 'movie':
            return self.browser.get_movie_from_id(split_id[0])
        return self.browser.get_video_from_id(split_id[0], split_id[-1])

    def iter_resources(self, objs, split_path):
        if BaseVideo in objs:
            collection = self.get_collection(objs, split_path)
            if collection.path_level == 0:
                yield Collection([u'comingsoon'], u'Films prochainement au cinéma')
                yield Collection([u'nowshowing'], u'Films au cinéma')
                yield Collection([u'acshow'], u'Émissions')
                yield Collection([u'interview'], u'Interviews')
            if collection.path_level == 1:
                if collection.basename == u'acshow':
                    emissions = self.browser.get_emissions(collection.basename)
                    if emissions:
                        for emission in emissions:
                            yield emission
                elif collection.basename == u'interview':
                    videos = self.browser.get_categories_videos(collection.basename)
                    if videos:
                        for video in videos:
                            yield video
                else:
                    videos = self.browser.get_categories_movies(collection.basename)
                    if videos:
                        for video in videos:
                            yield video
            if collection.path_level == 2:
                videos = self.browser.get_categories_videos(':'.join(collection.split_path))
                if videos:
                    for video in videos:
                        yield video

    def validate_collection(self, objs, collection):
        if collection.path_level == 0:
            return
        if collection.path_level == 1 and (collection.basename in
                                           [u'comingsoon', u'nowshowing', u'acshow', u'interview']):
            return

        if collection.path_level == 2 and collection.parent_path == [u'acshow']:
            return

        raise CollectionNotFound(collection.split_path)

    def search_events(self, query):
        if CATEGORIES.CINE in query.categories:
            if query.city and re.match('\d{5}', query.city):
                events = list(self.browser.search_events(query))
                events.sort(key=lambda x: x.start_date, reverse=False)
                return events

            raise UserError('You must enter a zip code in city field')

    def get_event(self, id):
        return self.browser.get_event(id)

    def fill_event(self, event, fields):
        if 'description' in fields:
            movieCode = event.id.split('#')[2]
            movie = self.get_movie(movieCode)
            event.description = movie.pitch
        return event

    OBJECTS = {
        Person: fill_person,
        Movie: fill_movie,
        BaseVideo: fill_video,
        BaseCalendarEvent: fill_event
    }
