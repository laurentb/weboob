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
from .pages.contact_thread import MailParser


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
        if re.match('^[\w\d\.\-_]+@[\w\d\.]+ vous offre la pos', resume):
            return False
        if contact.get_name() == 'Ekaterina':
            return False

        return True

    def check_profile(self, profile):
        # The name of profile is in form #123456789
        if re.match('^#\d+$', profile.get_name()):
            return False
        if profile.get_name().strip().lower() == 'ajoute moi':
            return False
        # This pattern in bad french is in several spambots description.
        if re.match('.*chercher? un m.c tres ch..d.*', profile.description):
            return False
        if profile.description.find('ajouter moi plan cam') >= 0:
            return False
        if profile.description.find('plan cam sexy') >= 0:
            return False
        if profile.description.find('belle dans la cam') >= 0:
            return False
        if profile.description.find('show sex') >= 0:
            return False
        if profile.description.find('un mec tres chaude') >= 0:
            return False
        if profile.description.find('bale chatt') >= 0:
            return False
        if profile.description.find('slt tt les mec chaud') >= 0:
            return False
        if profile.description.find('cc moi  ') >= 0:
            return False
        if profile.description.find('une fille tres chaud') >= 0:
            return False
        if profile.description.find('sa va bb') == 0:
            return False
        if profile.description.startswith('msn\n\n'):
            return False
        if profile.description.endswith('Moi la bonne jeune fille gaie'):
            return False
        # Her 'Shopping-list' begins with 'hummm'
        if profile.description.endswith('Sa shopping-list :\nhummm'):
            return False
        # Part of an email address (camiliasexy1live.fr)
        if profile.description.find('sexy1live') >= 0:
            return False
        # Strange thing...
        if re.match('.*je suis tres cho\w+d.*', profile.description):
            return False
        if re.match('.*je suis tr.s chaud', profile.description):
            return False
        # Strange thing...
        if re.match('.*ma croissance de \d+ sm.*', profile.description):
            return False
        if re.match('.*mon\s{2,}msn\s{2,}moi\s{2,}ok\s{2,}.*', profile.description):
            return False
        if re.match('.*voila\s{2,}mon\s{2,}msn.*', profile.description):
            return False
        if re.match('.*cava tout+ ami.*', profile.description):
            return False
        if re.match('.*site\s{2,}de\s{2,}chat\s{2,}et mon msn.*', profile.description):
            return False
        # "ajouter  moi :  alussiahotmail.fr"
        if re.match('^ajouter  moi :\s+\w+\.\w+\n', profile.description):
            return False
        return True

    def check_mail(self, mail):
        # Spambot with a long first-message.
        if mail.content.find('Je veux que vous m\'ayez ecrit directement sur le mon e-mail') >= 0:
            return False
        return True

    OBJECTS = {ContactItem: check_contact,
               ProfilePage: check_profile,
               MailParser:  check_mail,
              }
