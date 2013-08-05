# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Christophe Benz
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


from weboob.core.bcall import IResultsCondition, ResultsConditionError


__all__ = ['ResultsCondition', 'ResultsConditionError']


class ResultsCondition(IResultsCondition):
    condition_str = None

    # TODO: NOT?
    def __init__(self, condition_str):
        condition_str = condition_str.replace(' NOT ', ' not ')

        or_list = []
        for _or in condition_str.split(' OR '):
            and_dict = {}
            for _and in _or.split(' AND '):
                if '!=' in _and:
                    k, v = _and.split('!=')
                    k = k.strip() + '!'
                elif '=' in _and:
                    k, v = _and.split('=')
                else:
                    raise ResultsConditionError(u'Could not find = or != operator in sub-expression "%s"' % _and)
                and_dict[k.strip()] = v.strip()
            or_list.append(and_dict)
        self.condition = or_list
        self.condition_str = condition_str


    def is_valid(self, obj):
        d = dict(obj.iter_fields())
        # A and B give us a list with one elements of two dicts ([{u'A': u'toto', u'B': u'charles'}]
        # A or B  give us a list with two elements of one dict  [{u'A': u'toto'}, {u'B': u'charles'}]
        # We have to return True if one element of the list is True, and to evaluate all dicts at each iteration
        for _or in self.condition:
            myeval = True
            for k, v in _or.iteritems():
                different = False
                if k.endswith('!'):
                    k = k[:-1]
                    different = True
                if k in d:
                    # We have to change the type of v, always gived as string by application
                    typed = type(d[k])
                    try:
                        myeval = (d[k] == typed(v)) != different
                    except:
                        myeval = False
                else:
                    raise ResultsConditionError(u'Field "%s" is not valid.' % k)
                # Do not try all AND conditions if one is false
                if not myeval:
                    break
            # Return True at the first OR valid condition
            if myeval:
                return True
        # If we are here, all OR conditions are False
        return False

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return self.condition_str
