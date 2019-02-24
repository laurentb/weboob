# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

import re


class AntiSpam(object):
    def check_thread(self, thread):
        resume = thread['title']

        # Check if there is an email address in the offer.
        if re.match('^[\w\d\.\-_]+@[\w\d\.]+ vous offre la pos', resume):
            return False
        if thread['who']['pseudo'] == 'Ekaterina':
            return False

        return True

    def check_profile(self, profile):
        # The name of profile is in form #123456789
        if profile['pseudo'] == '':
            return False
        if profile['announce'].startswith('salut! je te donne mon msn'):
            return False
        if profile['shopping_list'].startswith('cam to cam'):
            return False
        if profile['shopping_list'].startswith('je suis une femme tres tres belle et je recherche un homme qui aime le sexe'):
            return False
        if profile['shopping_list'].endswith('mmmmmmmmmmmmmmmm'):
            return False
        return True

        # ipaddr is not available anymore.
        for ipaddr in (profile['last_ip'], profile['first_ip']):
            if ipaddr.startswith('41.202.'):
                return False
            if ipaddr.startswith('41.250.'):
                return False
            if ipaddr.startswith('41.251.'):
                return False
            if ipaddr.startswith('41.141.'):
                return False
            if ipaddr.startswith('194.177.'):
                return False
            if ipaddr.startswith('41.85.'):
                return False
            if ipaddr.startswith('41.86.'):
                return False
            if ipaddr.startswith('196.47.'):
                return False
            if re.match('105\.13\d.*', ipaddr):
                return False
            if ipaddr in ('62.157.186.18', '198.36.222.8', '212.234.67.61', '203.193.158.210', '41.189.34.180', '41.66.12.36', '196.47.137.21', '213.136.125.122', '41.191.87.188'):
                return False
        return True

    def check_contact(self, contact):
        if contact.id == 1:
            return True

        if not self.check_profile(contact._aum_profile):
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
            if ipaddr.endswith('.idstelcom.com'):
                return False
            if ipaddr.endswith('proxy.chg-support.com'):
                return False
            if ipaddr.endswith('.sprintsvc.net'):
                return False
            if ipaddr.endswith('.relakks.com'):
                return False
        return True

    def check_mail(self, mail):
        # Spambot with a long first-message.
        if mail['message'] is None:
            return True

        if mail['message'].find('Je veux que vous m\'ayez ecrit directement sur le mon e-mail') >= 0:
            return False
        if mail['message'].find('ilusa12010@live.fr') >= 0:
            return False
        return True
