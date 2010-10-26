# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
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


import re
from .ordereddict import OrderedDict


__all__ = ['ValuesDict', 'Value', 'ValueInt', 'ValueBool', 'ValueFloat']


class ValuesDict(OrderedDict):
    def __init__(self, *values):
        OrderedDict.__init__(self)
        for v in values:
            self[v.id] = v

class Value(object):
    def __init__(self, *args, **kwargs):
        if len(args) > 0:
            self.id = args[0]
        else:
            self.id = ''
        self.label = kwargs.get('label', kwargs.get('description', None))
        self.description = kwargs.get('description', kwargs.get('label', None))
        self.default = kwargs.get('default', None)
        self.regexp = kwargs.get('regexp', None)
        self.choices = kwargs.get('choices', None)
        if isinstance(self.choices, (list,tuple)):
            self.choices = dict(((v, v) for v in self.choices))
        self.masked = kwargs.get('masked', False)
        self.required = kwargs.get('required', self.default is None)
        self._value = kwargs.get('value', None)

    def check_valid(self, v):
        if v == '' and self.default != '':
            raise ValueError('Value can\'t be empty')
        if self.regexp is not None and not re.match(self.regexp, unicode(v)):
            raise ValueError('Value "%s" does not match regexp "%s"' % (v, self.regexp))
        if self.choices is not None and not v in self.choices.iterkeys():
            raise ValueError('Value "%s" is not in list: %s' % (v, ', '.join([unicode(s) for s in self.choices.iterkeys()])))

    def set_value(self, v):
        self.check_valid(v)
        self._value = v

    @property
    def value(self):
        return self._value

class ValueInt(Value):
    def __init__(self, *args, **kwargs):
        kwargs['regexp'] = '^\d+$'
        Value.__init__(self, *args, **kwargs)

    @property
    def value(self):
        return int(self._value)

class ValueFloat(Value):
    def __init__(self, *args, **kwargs):
        kwargs['regexp'] = '^[\d\.]+$'
        Value.__init__(self, *args, **kwargs)

    def check_valid(self, v):
        try:
            float(v)
        except ValueError:
            raise ValueError('Value "%s" is not a float value')

    @property
    def value(self):
        return float(self._value)

class ValueBool(Value):
    def __init__(self, *args, **kwargs):
        kwargs['choices'] = {'y': 'True', 'n': 'False'}
        Value.__init__(self, *args, **kwargs)

    def check_valid(self, v):
        if not isinstance(v, bool) and \
           not unicode(v).lower() in ('y', 'yes', '1', 'true',  'on',
                                      'n', 'no',  '0', 'false', 'off'):
            raise ValueError('Value "%s" is not a boolean (y/n)' % v)

    @property
    def value(self):
        return (isinstance(self._value, bool) and self._value) or \
                unicode(self._value).lower() in ('y', 'yes', '1', 'true', 'on')
