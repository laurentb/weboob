# -*- coding: utf-8 -*-

# Copyright(C) 2014  Simon Murail
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


import re

from weboob.tools.browser2.filters.standard import _NO_DEFAULT, Filter, Regexp, RegexpError
from weboob.tools.exceptions import ParseError


__all__ = ['JSPayload', 'JSVar']


def _quoted(q):
    return r'{0}(?:[^{0}]|\{0})*{0}'.format(q)


class JSPayload(Filter):
    r"""
    Get Javascript code from tag's text, cleaned from all comments.

    It filters code in a such a way that corner cases are handled, such as
    comments in string literals and comments in comments.

    The following snippet is borrowed from <http://ostermiller.org/findcomment.html>:

    >>> JSPayload.filter('''someString = "An example comment: /* example */";
    ...
    ... // The comment around this code has been commented out.
    ... // /*
    ... some_code();
    ... // */''')
    'someString = "An example comment: /* example */";\n\nsome_code();\n'

    """
    _single_line_comment = '[ \t\v\f]*//.*\r?(?:\n|$)'
    _multi_line_comment = '/\*(?:.|[\r\n])*?\*/'
    _splitter = re.compile('(?:(%s|%s)|%s|%s)' % (_quoted('"'),
                                                  _quoted("'"),
                                                  _single_line_comment,
                                                  _multi_line_comment))

    @classmethod
    def filter(cls, value):
        return ''.join(filter(bool, cls._splitter.split(value)))


class JSVar(Regexp):
    r"""
    Get the init value of first found assignment value of a variable.

    It only understands literal values, but should parse them well. Values
    are converted in python values, quotes and slashes in strings are stripped.

    >>> JSVar(var='test').filter("var test = .1")
    0.1
    >>> JSVar(var='test').filter("test = 42")
    42
    >>> JSVar(var='test').filter('test = "Some \\"string\\" value"')
    'Some "string" value'
    >>> JSVar(var='test').filter("var test = false")
    False
    """
    pattern_template = r"""(?x)
        (?:var\s+)?                                   # optional var keyword
        \b%%s                                          # var name
        \s*=\s*                                       # equal sign
        (?:(?P<float>[-+]?\s*                         # float ?
               (?:(?:\d+\.\d*|\d*\.\d+)(?:[eE]\d+)?
                 |\d+[eE]\d+))
          |(?P<int>[-+]?\s*(?:0[bBxXoO])?\d+)         # int ?
          |(?P<str>(?:%s|%s))                         # str ?
          |(?P<bool>true|false)                       # bool ?
          |(?P<None>null))                            # None ?
    """ % (_quoted('"'), _quoted("'"))

    _re_spaces = re.compile(r'\s+')

    def to_python(self, m):
        values = m.groupdict()
        for t, v in values.iteritems():
            if v is not None:
                break
        if self.of_type and t != self.of_type.__name__:
            raise ParseError('Variable %r of type %s not found' % (self.var, self.of_type))
        if t in ('int', 'float'):
            v = self._re_spaces.sub('', v).lower()
            if t == 'int':
                base = {'x': 16, 'o': 8, 'b': 2}.get(v[1], 10) if v[0] == '0' else 10
                return int(v, base=base)
            return float(v)
        if t == 'str':
            return v[1:-1].decode('string_escape')
        if t == 'bool':
            return v == 'true'
        if t == 'None':
            return
        if self.default:
            return self.default
        raise ParseError('Unable to parse variable %r value' % self.var)

    def __init__(self, selector=None, var=None, of_type=None, default=_NO_DEFAULT):
        assert var is not None, 'Please specify a var parameter'
        self.var = var
        self.of_type = of_type
        pattern = self.pattern_template % var
        super(JSVar, self).__init__(selector, pattern=pattern, template=self.to_python, default=default)

    def filter(self, txt):
        try:
            return super(JSVar, self).filter(txt)
        except RegexpError:
            raise ParseError('Variable %r not found' % self.var)

