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


__all__ = ['ICapDating', 'Profile']


class Profile(object):
    def get_profile_text(self):
        body = u'Status: %s' % unicode(self.status)
        if self.photos:
            body += u'\nPhotos:'
            for photo in self.photos:
                body += u'\n\t\t%s' % unicode(photo)
        body += u'\nStats:'
        for label, value in self.get_stats().iteritems():
            body += u'\n\t\t%-15s %s' % (label + ':', value)
        body += u'\n\nInformations:'
        for section, d in self.get_table().iteritems():
            body += u'\n\t%s\n' % section
            for key, value in d.items():
                key = '%s:' % key
                if isinstance(value, list):
                    body += u'\t\t%-15s %s\n' % (key, u', '.join([unicode(s) for s in value]))
                elif isinstance(value, float):
                    body += u'\t\t%-15s %.2f\n' % (key, value)
                else:
                    body += u'\t\t%-15s %s\n' % (key, unicode(value))
        body += u'\n\nDescription:\n%s' % unicode(self.get_description())

        return body

class OptimizationNotFound(Exception): pass

class Optimization(object):
    def start(self):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()

class ICapDating(ICap):
    def get_profile(self, _id):
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
