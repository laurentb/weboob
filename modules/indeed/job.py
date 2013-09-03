# -*- coding: utf-8 -*-

# Copyright(C) 2013 Bezleputh
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

from weboob.capabilities.job import BaseJobAdvert


class IndeedJobAdvert(BaseJobAdvert):

    @classmethod
    def id2url(cls, _id):
        dico_car_part = {" ": "-",
                         "/": "-",
                         }
        for cle, valeur in dico_car_part.items():
            _id = _id.replace(cle, valeur)

        splitted_id = _id.split('|')
        return 'http://www.indeed.fr/cmp/%s/jobs/%s-%s' % (splitted_id[0], splitted_id[1], splitted_id[2])
