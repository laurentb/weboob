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


__all__ = ['AntiSpam']


class AntiSpam(object):
    def check_thread(self, thread):
        resume = thread['title']

        # Check if there is an email address in the offer.
        if re.match('^[\w\d\.\-_]+@[\w\d\.]+ vous offre la pos', resume):
            return False
        if thread['member']['pseudo'] == 'Ekaterina':
            return False

        return True

    def check_profile(self, profile):
        # The name of profile is in form #123456789
        if profile['pseudo'] == '':
            return False
        if len(profile['about1'].strip()) > 30 and profile['about1'].strip() == profile['about2'].strip():
            return False
        if profile['about1'].startswith('salut! je te donne mon msn'):
            return False
        if profile['about2'].startswith('cam to cam'):
            return False
        if profile['about2'].startswith('je suis une femme tres tres belle et je recherche un homme qui aime le sexe'):
            return False
        if profile['about2'].endswith('mmmmmmmmmmmmmmmm'):
            return False
        return True

        # ipaddr is not available anymore.
        for ipaddr in (profile['last_ip'], profile['first_ip']):
            if ipaddr.startswith('41.202.'):
                return False
            if ipaddr.startswith('41.250.'):
                return False
            if ipaddr.startswith('41.141.'):
                return False
            if ipaddr.startswith('194.177.'):
                return False
            if re.match('105\.13\d.*', ipaddr):
                return False
            if ipaddr in ('62.157.186.18', '198.36.222.8', '212.234.67.61'):
                return False
        return True

    def check_contact(self, contact):
        if not self.check_profile(contact.aum_profile):
            return False

        return True

        # ipaddr is not available anymore.
        first_ip = contact.profile['info']['IPaddr'].value.split(' ')[0]
        last_ip = contact.profile['info']['IPaddr'].value.rstrip(')')
        for ipaddr in (first_ip, last_ip):
            if ipaddr.endswith('.afnet.net'):
                return False
            if ipaddr.endswith('.iam.net.ma'):
                return False
            if ipaddr.endswith('.amsterdam.ananoos.net'):
                return False
            if ipaddr.endswith('.tedata.net'):
                return False
            if ipaddr.endswith('kupo.fr'):
                return False
            if ipaddr.endswith('.static.virginmedia.com'):
                return False
            if ipaddr.endswith('frozenway.com'):
                return False
            if ipaddr.endswith('.rev.bgtn.net'):
                return False
            if ipaddr.endswith('real-vpn.com'):
                return False
            if ipaddr.endswith('.nl.ipodah.net'):
                return False
            if ipaddr.endswith('.wanamaroc.com'):
                return False
            if ipaddr.endswith('.ukservers.com'):
                return False
            if ipaddr.endswith('.startdedicated.com'):
                return False
            if ipaddr.endswith('.clients.your-server.de'):
                return False
            if ipaddr.endswith('.cba.embratel.net.br'):
                return False
        return True

    def check_mail(self, mail):
        # Spambot with a long first-message.
        if mail['message'].find('Je veux que vous m\'ayez ecrit directement sur le mon e-mail') >= 0:
            return False
        if mail['message'].find('ilusa12010@live.fr') >= 0:
            return False
        return True
