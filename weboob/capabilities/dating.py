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


from .cap import ICap


__all__ = ['ICapDating']


class OptimizationNotFound(Exception):
    pass


class Optimization(object):
    def start(self):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()


class StatusField(object):
    FIELD_TEXT    = 0x001     # the value is a long text
    FIELD_HTML    = 0x002     # the value is HTML formated

    def __init__(self, key, label, value, flags=0):
        self.key = key
        self.label = label
        self.value = value
        self.flags = flags


class ICapDating(ICap):
    def get_status(self):
        """
        Get a list of fields
        """
        raise NotImplementedError()

    OPTIM_PROFILE_WALKER = None
    OPTIM_VISIBILITY = None

    def init_optimizations(self):
        raise NotImplementedError()

    def get_optim(self, optim):
        optim = optim.upper()
        if not hasattr(self, 'OPTIM_%s' % optim):
            raise OptimizationNotFound()

        return getattr(self, 'OPTIM_%s' % optim)

    def start_optimization(self, optim):
        optim = self.get_optim(optim)
        if not optim:
            return False

        return optim.start()

    def stop_optimization(self, optim):
        optim = self.get_optim(optim)
        if not optim:
            return False

        return optim.stop()
