# -*- coding: utf-8 -*-

# Copyright(C) 2008-2011  Romain Bignon
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


from html2text import unescape
import socket
from datetime import datetime
from dateutil.parser import parse as parse_dt
from collections import OrderedDict

from weboob.capabilities.contact import Contact as _Contact, ProfileNode
from weboob.tools.html import html2text
from weboob.tools.compat import unicode, basestring


class FieldBase(object):
    def __init__(self, key, key2=None):
        self.key = key
        self.key2 = key2

    def get_value(self, value, consts):
        raise NotImplementedError()


class FieldStr(FieldBase):
    def get_value(self, profile, consts):
        return html2text(unicode(profile[self.key])).strip()


class FieldBool(FieldBase):
    def get_value(self, profile, consts):
        return bool(int(profile[self.key]))


class FieldDist(FieldBase):
    def get_value(self, profile, consts):
        return '%.2f km' % float(profile[self.key])


class FieldIP(FieldBase):
    def get_hostname(self, s):
        try:
            return socket.gethostbyaddr(s)[0]
        except (socket.gaierror, socket.herror):
            return s

    def get_value(self, profile, consts):
        s = self.get_hostname(profile[self.key])
        if profile[self.key] != profile[self.key2]:
            s += ' (first %s)' % self.get_hostname(profile[self.key2])
        return s


class FieldProfileURL(FieldBase):
    def get_value(self, profile, consts):
        id = int(profile[self.key])
        if id > 0:
            return 'http://www.adopteunmec.com/index.php/profile/%d' % id
        else:
            return ''


class FieldPopu(FieldBase):
    def get_value(self, profile, consts):
        return unicode(profile['popu'][self.key])


class FieldPopuRatio(FieldBase):
    def get_value(self, profile, consts):
        v1 = float(profile['popu'][self.key])
        v2 = float(profile['popu'][self.key2])
        if v2 == 0.0:
            return 'NaN'
        else:
            return '%.2f' % (v1 / v2)


class FieldOld(FieldBase):
    def get_value(self, profile, consts):
        birthday = parse_dt(profile[self.key])
        return int((datetime.now() - birthday).days / 365.25)


class FieldList(FieldBase):
    def get_value(self, profile, consts):
        return profile[self.key]


class FieldBMI(FieldBase):
    def __init__(self, key, key2, fat=False):
        FieldBase.__init__(self, key, key2)
        self.fat = fat

    def get_value(self, profile, consts):
        height = int(profile[self.key])
        weight = int(profile[self.key2])
        if height == 0 or weight == 0:
            return ''

        bmi = (weight / float(pow(height / 100.0, 2)))
        if not self.fat:
            return bmi
        elif bmi < 15.5:
            return 'severely underweight'
        elif bmi < 18.4:
            return 'underweight'
        elif bmi < 24.9:
            return 'normal'
        elif bmi < 30:
            return 'overweight'
        else:
            return 'obese'


class FieldConst(FieldBase):
    def get_value(self, profile, consts):
        v = profile[self.key]
        if isinstance(v, (basestring,int)):
            try:
                return consts[self.key][str(v)]
            except KeyError:
                return ''
        elif isinstance(v, (tuple,list)):
            labels = []
            for i in v:
                labels.append(consts[self.key][i])
            return labels


class Contact(_Contact):
    TABLE = OrderedDict((
                 ('_info',        OrderedDict((
                                    ('title',               FieldStr('title')),
                                    # ipaddr is not available anymore.
                                    #('IPaddr',              FieldIP('last_ip', 'first_ip')),
                                    ('admin',               FieldBool('admin')),
                                    ('ban',                 FieldBool('isBan')),
                                    ('first',               FieldStr('first_cnx')),
                                    ('godfather',           FieldProfileURL('godfather')),
                                  ))),
                 ('_stats',       OrderedDict((
                                    ('mails',               FieldPopu('mails')),
                                    ('charms',              FieldPopu('charmes')),
                                    ('visites',             FieldPopu('visites')),
                                    ('baskets',             FieldPopu('panier')),
                                    ('invits',              FieldPopu('invits')),
                                    ('bonus',               FieldPopu('bonus')),
                                    ('score',               FieldStr('points')),
                                    ('ratio',               FieldPopuRatio('mails', 'charmes')),
                                    ('mailable',            FieldBool('can_mail')),
                                  ))),
                 ('details',      OrderedDict((
                                    #('old',                 FieldStr('age')),
                                    ('old',                 FieldOld('birthdate')),
                                    ('birthday',            FieldStr('birthdate')),
                                    ('zipcode',             FieldStr('zip')),
                                    ('location',            FieldStr('city')),
                                    ('distance',            FieldDist('dist')),
                                    ('country',             FieldStr('country')),
                                    ('phone',               FieldStr('phone')),
                                    ('eyes',                FieldConst('eyes_color')),
                                    ('hair_color',          FieldConst('hair_color')),
                                    ('hair_size',           FieldConst('hair_size')),
                                    ('height',              FieldConst('size')),
                                    ('weight',              FieldConst('weight')),
                                    ('BMI',                 FieldBMI('size', 'weight')),
                                    ('fat',                 FieldBMI('size', 'weight', fat=True)),
                                    ('shape',               FieldConst('shape')),
                                    ('origins',             FieldConst('origins')),
                                    ('signs',               FieldConst('features')),
                                    ('job',                 FieldStr('job')),
                                    ('style',               FieldConst('styles')),
                                    ('food',                FieldConst('diet')),
                                    ('favorite_food',       FieldConst('favourite_food')),
                                    ('drink',               FieldConst('alcohol')),
                                    ('smoke',               FieldConst('tobacco')),
                                  ))),
                ('tastes',        OrderedDict((
                                    ('hobbies',             FieldStr('hobbies')),
                                    ('music',               FieldList('music')),
                                    ('cinema',              FieldList('cinema')),
                                    ('books',               FieldList('books')),
                                    ('tv',                  FieldList('tvs')),
                                  ))),
                ('+sex',          OrderedDict((
                                    ('underwear',           FieldConst('underwear')),
                                    ('practices',           FieldConst('sexgames')),
                                    ('favorite',            FieldConst('arousing')),
                                    ('toys',                FieldConst('sextoys')),
                                  ))),
                ('+personality',  OrderedDict((
                                    ('snap',                FieldStr('fall_for')),
                                    ('exciting',            FieldStr('turned_on_by')),
                                    ('hate',                FieldStr('cant_stand')),
                                    ('vices',               FieldStr('vices')),
                                    ('assets',              FieldStr('assets')),
                                    ('fantasies',           FieldStr('fantasies')),
                                    ('is',                  FieldConst('character')),
                                  ))),
                ('-personality',  OrderedDict((
                                    ('accessories',         FieldConst('accessories')),
                                    ('skills',              FieldConst('skills')),
                                    ('socios',              FieldConst('socios')),
                                    ('family',              FieldConst('family')),
                                    ('pets',                FieldConst('pets')),
                                  )))
        ))

    def parse_profile(self, profile, consts):
        if profile['online']:
            self.status = Contact.STATUS_ONLINE
            self.status_msg = u'online'
            self.status_msg = u'since %s' % profile['last_cnx']
        else:
            self.status = Contact.STATUS_OFFLINE
            self.status_msg = u'last connection %s' % profile['last_cnx']

        self.summary = unicode(unescape(profile.get('announce', '').strip()))
        if len(profile.get('shopping_list', '')) > 0:
            self.summary += u'\n\nLooking for:\n%s' % unescape(profile['shopping_list'].strip())

        for photo in profile['pics']:
            self.set_photo(photo.split('/')[-1],
                              url=photo + '/full',
                              thumbnail_url=photo + '/small',
                              hidden=False)
        self.profile = OrderedDict()

        if 'sex' in profile:
            for section, d in self.TABLE.items():
                flags = ProfileNode.SECTION
                if section.startswith('_'):
                    flags |= ProfileNode.HEAD
                if (section.startswith('+') and int(profile['sex']) != 1) or \
                   (section.startswith('-') and int(profile['sex']) != 0):
                    continue

                section = section.lstrip('_+-')

                s = ProfileNode(section, section.capitalize(), OrderedDict(), flags=flags)

                for key, builder in d.items():
                    try:
                        value = builder.get_value(profile, consts[int(profile['sex'])])
                    except KeyError:
                        pass
                    else:
                        s.value[key] = ProfileNode(key, key.capitalize().replace('_', ' '), value)

                self.profile[section] = s

        self._aum_profile = profile
