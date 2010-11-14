# -*- coding: utf-8 -*-

# Copyright(C) 2010  Christophe Benz
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


__all__ = ['ResultsCondition', 'ResultsConditionException']


class ResultsCondition(object):
    condition_str = None

    def __init__(self, condition_str):
        condition_str = condition_str.replace(' OR ', ' or ') \
                                     .replace(' AND ', ' and ') \
                                     .replace(' NOT ', ' not ')
        or_list = []
        for _or in condition_str.split(' or '):
            and_dict = {}
            for _and in _or.split(' and '):
                if '!=' in _and:
                    k, v = _and.split('!=')
                    k = k.strip() + '!'
                elif '=' in _and:
                    k, v = _and.split('=')
                else:
                    raise ResultsConditionException(u'Could not find = or != operator in sub-expression "%s"' % _and)
                and_dict[k.strip()] = v.strip()
            or_list.append(and_dict)
        self.condition = or_list
        self.condition_str = condition_str

    def is_valid(self, d):
        for _or in self.condition:
            for k, v in _or.iteritems():
                if k.endswith('!'):
                    k = k[:-1]
                    different = True
                else:
                    different = False
                if k in d:
                    if different:
                        if d[k] == v:
                            return False
                    else:
                        if d[k] != v:
                            return False
                else:
                    raise ResultsConditionException(u'Field "%s" is not valid.' % k)
        return True

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return self.condition_str


class ResultsConditionException(Exception):
    pass
