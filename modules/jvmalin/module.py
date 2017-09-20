# -*- coding: utf-8 -*-

# Copyright(C) 2013 Alexandre Lissy
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

from weboob.capabilities.travel import CapTravel, RoadStep
from weboob.tools.backend import Module

from .browser import JVMalin


__all__ = ['JVMalinModule']


class JVMalinModule(Module, CapTravel):
    NAME = 'jvmalin'
    MAINTAINER = u'Alexandre Lissy'
    EMAIL = 'github@lissy.me'
    VERSION = '1.4'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u"Multimodal public transportation for whole Région Centre, France"
    BROWSER = JVMalin

    def iter_roadmap(self, departure, arrival, filters):
        with self.browser:
            roadmap = self.browser.get_roadmap(departure, arrival, filters)

        for s in roadmap['steps']:
            step = RoadStep(s['id'])
            step.line = s['line']
            step.start_time = s['start_time']
            step.end_time = s['end_time']
            step.departure = s['departure']
            step.arrival = s['arrival']
            step.duration = s['duration']
            yield step
