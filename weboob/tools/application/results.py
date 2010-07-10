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


__all__ = ['Results', 'ResultsCondition', 'ResultsConditionException']


class Results(object):
    def __init__(self, name=u'', header=None):
        self.name = name
        self._groups = []
        self._items = []
        self.header = header

    def add_item(self, item):
        self._items.append(item)

    def add_items(self, items):
        self._items.extend(items)

    def iter_items(self):
        return iter(self._items)

    def deep_iter_items(self):
        for i in self._items:
            yield i
        for g in self._groups:
            for i in g.iter_items():
                yield i

    def add_group(self, group):
        self._groups.append(group)

    def get_group(self, name):
        l = [group for group in self._groups if group.name == name]
        if l:
            return l[0]
        else:
            return None

    def get_or_create_group(self, name, group_class=None):
        if group_class is None:
            group_class = Results
        group = self.get_group(name)
        if group:
            return group
        else:
            new_group = group_class(name)
            self.add_group(new_group)
            return new_group

    def iter_groups(self):
        return iter(self._groups)


class ResultsCondition(object):
    def __init__(self, condition_str):
        condition_str = condition_str.replace('OR', 'or') \
                                     .replace('AND', 'and') \
                                     .replace('NOT', 'not')
        or_list = []
        try:
            for _or in condition_str.split('or'):
                and_dict = {}
                for _and in _or.split('and'):
                    if '!=' in _and:
                        k, v = _and.split('!=')
                        k += '!'
                    elif '=' in _and:
                        k, v = _and.split('=')
                    else:
                        raise ResultsConditionException(u'Could not find = or != operator in sub-expression "%s"' % _and)
                    and_dict[k] = v
                or_list.append(and_dict)
        except:
            raise ResultsConditionException(u'Could not parse condition expression "%s"' % condition_str)
        self.condition = or_list

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


class ResultsConditionException(Exception):
    pass
