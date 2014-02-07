# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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
import subprocess
from .ordereddict import OrderedDict
from .misc import to_unicode


__all__ = ['ValuesDict', 'Value', 'ValueBackendPassword', 'ValueInt', 'ValueFloat', 'ValueBool']


class ValuesDict(OrderedDict):
    """
    Ordered dictionarry which can take values in constructor.

    >>> ValuesDict(Value('a', label='Test'), ValueInt('b', label='Test2'))
    """
    def __init__(self, *values):
        OrderedDict.__init__(self)
        for v in values:
            self[v.id] = v


class Value(object):
    """
    Value.

    :param label: human readable description of a value
    :type label: str
    :param required: if ``True``, the backend can't load if the key isn't found in its configuration
    :type required: bool
    :param default: an optional default value, used when the key is not in config. If there is no default value and the key
                    is not found in configuration, the **required** parameter is implicitly set
    :param masked: if ``True``, the value is masked. It is useful for applications to know if this key is a password
    :type masked: bool
    :param regexp: if specified, on load the specified value is checked against this regexp, and an error is raised if it doesn't match
    :type regexp: str
    :param choices: if this parameter is set, the value must be in the list
    :param tiny: the value of choices can be entered by an user (as they are small)
    :type choices: (list,dict)
    """

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
        if isinstance(self.choices, (list, tuple)):
            self.choices = OrderedDict(((v, v) for v in self.choices))
        self.tiny = kwargs.get('tiny', None)
        self.masked = kwargs.get('masked', False)
        self.required = kwargs.get('required', self.default is None)
        self._value = kwargs.get('value', None)

    def check_valid(self, v):
        """
        Check if the given value is valid.

        :raises: ValueError
        """
        if self.default is not None and v == self.default:
            return
        if v == '' and self.default != '':
            raise ValueError('Value can\'t be empty')
        if self.regexp is not None and not re.match(self.regexp, unicode(v)):
            raise ValueError('Value "%s" does not match regexp "%s"' % (v, self.regexp))
        if self.choices is not None and not v in self.choices.iterkeys():
            raise ValueError('Value "%s" is not in list: %s' % (
                v, ', '.join(unicode(s) for s in self.choices.iterkeys())))

    def load(self, domain, v, callbacks):
        """
        Load value.

        :param domain: what is the domain of this value
        :type domain: str
        :param v: value to load
        :param callbacks: list of weboob callbacks
        :type callbacks: dict
        """
        return self.set(v)

    def set(self, v):
        """
        Set a value.
        """
        self.check_valid(v)
        if isinstance(v, str):
            v = to_unicode(v)
        self._value = v

    def dump(self):
        """
        Dump value to be stored.
        """
        return self.get()

    def get(self):
        """
        Get the value.
        """
        return self._value

    def is_command(self, v):
        """
        Test if a value begin with ` and end with `
        (`command` is used to call external programms)
        """
        return isinstance(v, basestring) and v.startswith(u'`') and v.endswith(u'`')



class ValueBackendPassword(Value):
    _domain = None
    _callbacks = {}
    _stored = True

    def __init__(self, *args, **kwargs):
        kwargs['masked'] = kwargs.pop('masked', True)
        self.noprompt = kwargs.pop('noprompt', False)
        Value.__init__(self, *args, **kwargs)

    def load(self, domain, password, callbacks):
        if self.is_command(password):
            cmd = password[1:-1]
            try:
                password = subprocess.check_output(cmd, shell=True)
            except subprocess.CalledProcessError as e:
                raise ValueError(u'The call to the external tool failed: %s' % e)
            else:
                password = password.partition('\n')[0].strip('\r\n\t')
        self.check_valid(password)
        self._domain = domain
        self._value = to_unicode(password)
        self._callbacks = callbacks

    def check_valid(self, passwd):
        if passwd == '':
            # always allow empty passwords
            return True
        return Value.check_valid(self, passwd)

    def set(self, passwd):
        if self.is_command(passwd):
            self._value = passwd
            return

        self.check_valid(passwd)
        if passwd is None:
            # no change
            return
        self._value = ''
        if passwd == '':
            return
        if self._domain is None:
            self._value = to_unicode(passwd)
            return

        try:
            raise ImportError('Keyrings are disabled (see #706)')
            import keyring
            keyring.set_password(self._domain, self.id, passwd)
        except Exception:
            self._value = to_unicode(passwd)
        else:
            self._value = ''

    def dump(self):
        if self._stored:
            return self._value
        else:
            return ''

    def get(self):
        if self._value != '' or self._domain is None:
            return self._value

        try:
            raise ImportError('Keyrings are disabled (see #706)')
            import keyring
        except ImportError:
            passwd = None
        else:
            passwd = keyring.get_password(self._domain, self.id)

        if passwd is not None:
            # Password has been read in the keyring.
            return to_unicode(passwd)

        # Prompt user to enter password by hand.
        if not self.noprompt and 'login' in self._callbacks:
            self._value = to_unicode(self._callbacks['login'](self._domain, self))
            if self._value is None:
                self._value = ''
            else:
                self._stored = False
        return self._value


class ValueInt(Value):
    def __init__(self, *args, **kwargs):
        kwargs['regexp'] = '^\d+$'
        Value.__init__(self, *args, **kwargs)

    def get(self):
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

    def get(self):
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

    def get(self):
        return (isinstance(self._value, bool) and self._value) or \
                unicode(self._value).lower() in ('y', 'yes', '1', 'true', 'on')
