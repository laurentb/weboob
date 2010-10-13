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

from .pages.contact_list import ContactItem
from .pages.profile import ProfilePage


__all__ = ['AntiSpam']


class AntiSpam(object):
    def check(self, obj):
        for key, value in self.OBJECTS.iteritems():
            if isinstance(obj, key):
                return value(self, obj)

        raise TypeError('Unsupported object %r' % obj)

    def check_contact(self, contact):
        resume = contact.get_resume()

        # Check if there is an email address in the offer.
        if re.match('[\w\d\._]+@[\w\d\.]+ vous offre la possibilit', resume):
            return False

        return True

    def check_profile(self, profile):
        # TODO
        return True

    OBJECTS = {ContactItem: check_contact,
               ProfilePage: check_profile,
              }
