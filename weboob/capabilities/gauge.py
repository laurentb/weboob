# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon, Florent Fourcot
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


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
