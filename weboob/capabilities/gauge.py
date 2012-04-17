# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012  Romain Bignon, Florent Fourcot
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


from .base import IBaseCap, CapBaseObject, StringField, FloatField, DateField


__all__ = ['Gauge', 'GaugeMeasure', 'ICapWaterLevel']


class Gauge(CapBaseObject):
    """
    Gauge class.
    """
    name =      StringField('Name of gauge')
    river =     StringField('What river')
    level =     FloatField('Level of gauge')
    flow =      FloatField('Flow of gauge')
    lastdate =  DateField('Last measure')
    forecast =  StringField('Forecast')

class GaugeMeasure(CapBaseObject):
    """
    Measure of a gauge.
    """
    level =     FloatField('Level of measure')
    flow =      FloatField('Flow of measure')
    date =      DateField('Date of measure')

    def __init__(self):
        CapBaseObject.__init__(self, None)

class ICapWaterLevel(IBaseCap):
    def iter_gauge_history(self, id):
        """
        Get history of a gauge.

        :param id: ID of the river
        :type id: str
        :rtype: iter[:class:`GaugeMeasure`]
        """
        raise NotImplementedError()

    def get_last_measure(self, id):
        """
        Get last measure of the gauge.

        :param id: ID of the gauge
        :type id: str
        :rtype: :class:`GaugeMeasure`
        """
        raise NotImplementedError()

    def iter_gauges(self, pattern=None):
        """
        Iter gauges.

        :param pattern: if specified, used to search gauges
        :type pattern: str
        :rtype: iter[:class:`Gauge`]
        """
        raise NotImplementedError()
