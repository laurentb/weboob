# -*- coding: utf-8 -*-

"""
Copyright(C) 2008-2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from weboob.backends.aum.pages.base import PageBase
from weboob.capabilities.dating import Profile

from copy import deepcopy
from logging import warning
import re

class FieldBase:

    def __init__(self, key):
        self.key = key

    def put_value(self, d, value):
        raise NotImplementedError

class FieldString(FieldBase):
    def put_value(self, d, value):
        d[self.key] = unicode(value)

class FieldList(FieldBase):
    def put_value(self, d, value):
        d[self.key] = value.split(', ')

class FieldWideList(FieldBase):

    def put_value(self, d, value):
        d[self.key] += [value]

class FieldOld(FieldBase):
    regexp = re.compile(u'([0-9]+) ans( \(Née le  ([0-9]+) ([^ ]+) ([0-9]+)\))?')
    month2i = ['', 'janvier', u'février', 'mars', 'avril', 'mai', 'juin', 'juillet', u'août', 'septembre', 'octobre', 'novembre', u'décembre']

    def put_value(self, d, value):
        m = self.regexp.match(value)
        if not m:
            return

        d[self.key] = int(m.group(1))
        if not m.group(2):
            return

        try:
            d['birthday'] = (int(m.group(3)),
                             self.month2i.index(m.group(4)),
                             int(m.group(5)))
        except ValueError, e:
            print str(e)

class FieldLocation(FieldBase):
    location = re.compile('(.*) \(([0-9]{5})\), (.*)')

    def __init__(self):
        FieldBase.__init__(self, '')
    def put_value(self, d, value):
        # TODO: determine distance, or something like
        m = self.location.match(value)
        if m:
            d['location'] = m.group(1)
            d['zipcode'] = int(m.group(2))
            d['country'] = m.group(3)
        else:
            warning('Unable to parse the location "%s"' % value)
            d['location'] = unicode(value)

class FieldMeasurements(FieldBase):
    height = re.compile('([0-9]{1,3}) cm')
    weight = re.compile('([0-9]{1,3}) kg')
    # TODO: parse third parameter

    def __init__(self):
        FieldBase.__init__(self, '')
    def put_value(self, d, value):
        for s in value.split(', '):
            m = self.height.match(s)
            if m:
                d['height'] = int(m.group(1))
                continue
            m = self.weight.match(s)
            if m:
                d['weight'] = int(m.group(1))
                continue
        if d['height'] and d['weight']:
            bmi = (d['weight']/float(pow(d['height']/100.0, 2)))
            if bmi < 15.5:
                d['fat'] = 'severely underweight'
            elif bmi < 18.4:
                d['fat'] = 'underweight'
            elif bmi < 24.9:
                d['fat'] = 'normal'
            elif bmi < 30:
                d['fat'] = 'overweight'
            else:
                d['fat'] = 'obese'
            d['BMI'] = bmi

class FieldParticularSignes(FieldBase):
    def __init__(self): FieldBase.__init__(self, '')
    def put_value(self, d, value):
        for s in value.split(', '):
            if s.find('tatouages') >= 0:
                d['tatoos'] = True
            elif s.find('piercing') >= 0:
                d['piercing'] = True
            elif s.find('lunettes') >= 0:
                d['glasses'] = True
            elif s.find('rousseur') >= 0:
                d['freckle'] = True

class ProfilePage(PageBase, Profile):
    empty_table = {'details':      {'old':           0,
                                    'birthday':      (0,0,0),
                                    'zipcode':       0,
                                    'location':      '',
                                    'country':       '',
                                    'eyes':          '',
                                    'hairs':         [],
                                    'height':        0,
                                    'weight':        0,
                                    'BMI':           0,
                                    'fat':           '',
                                    'from':          '',
                                    'tatoos':        False,
                                    'piercing':      False,
                                    'freckle':       False,
                                    'glasses':       False,
                                    'job':           '',
                                    'style':         '',
                                    'alimentation':  '',
                                    'alcool':        '',
                                    'tabac':         '',
                                   },
                   'liking':       {'activities':    '',
                                    'music':         [],
                                    'cinema':        [],
                                    'books':         [],
                                    'tv':            [],
                                   },
                   'sex':          {'underwear':     [],
                                    'top':           [],
                                    'bottom':        [],
                                    'interval':      '',
                                    'practices':     [],
                                    'favorite':      '',
                                    'toys':          [],
                                   },
                   'personality':  {'snap':          '',
                                    'exciting':      '',
                                    'hate':          '',
                                    'vices':         '',
                                    'assets':        '',
                                    'fantasies':     '',
                                    'is':            [],
                                   },
                }

    tables = {'tab_0': 'details',
              'tab_1': 'liking',
              'tab_2': 'sex',
              'tab_3': 'personality'
             }

    fields =      {'details':      {'Age':                  FieldOld('old'),
                                    u'Réside à':            FieldLocation(),
                                    'Yeux':                 FieldString('eyes'),
                                    'Cheveux ':             FieldList('hairs'),
                                    'Mensurations ':        FieldMeasurements(),
                                    'Origines ':            FieldString('from'),
                                    'Signes particuliers ': FieldParticularSignes(),
                                    'Style ':               FieldString('style'),
                                    'Profession ':          FieldString('job'),
                                    'Alimentation':         FieldString('alimentation'),
                                    'Alcool':               FieldString('alcool'),
                                    'Tabac':                FieldString('tabac'),
                                   },
                   'liking':       {'Hobbies ':             FieldString('activities'),
                                    'Musique ':             FieldWideList('music'),
                                   u'Cinéma':               FieldWideList('cinema'),
                                    'Livres ':              FieldWideList('books'),
                                   u'Télé':                 FieldWideList('tv'),
                                   },
                   'sex':          {u'Sous-v\xeatements ':  FieldList('underwear'),
                                    '... en haut ':         FieldList('top'),
                                    '... en bas ':          FieldList('bottom'),
                                    u'Fréquence idéale des rapports sexuels ':
                                                            FieldString('interval'),
                                    'Pratiques sexuelles ': FieldList('practices'),
                                   u'Accessoires préférés ':FieldList('toys'),
                                   u'Position favorite ':   FieldString('favorite'),
                                   },
                   'personality':  {u'Ça la fait craquer ': FieldString('snap'),
                                    u'Ça l\'excite ':       FieldString('exciting'),
                                    u'Elle déteste ':       FieldString('hate'),
                                    'Ses vices ':           FieldString('vices'),
                                    'Ses atouts ':          FieldString('assets'),
                                    'Ses fantasmes ':       FieldString('fantasies'),
                                    'Elle est  ':           FieldList('is'),
                                   },
                }

    ID_REGEXP = re.compile('(charm|addBasket|openAlbum)\(([0-9]+)(,[\s\'\d]+)?\)')
    PHOTO_REGEXP = re.compile('http://(s|p)([0-9]+)\.adopteunmec\.com/(.*)')

    STATS2ID = {'visites':   'visits',
                'charmes':   'charms',
                'paniers':   'baskets',
                'mails':     'mails',
                'POPULARIT': 'score',
               }
    STATS_VALUE_REGEXP = re.compile('([0-9\s]+).*')

    def __repr__(self):
        if isinstance(self.name, unicode):
            name = self.name.encode('utf-8', 'backslashreplace')
        else:
            name = self.name
        return '<Profile name="%s">' % name

    def on_loaded(self):
        self.name = u''
        self.description = u''
        self.table = deepcopy(self.empty_table)
        self.id = 0
        self.photos = []
        self.status = ''
        self.stats = {'score':   0,
                      'visits':  0,
                      'charms':  0,
                      'baskets': 0,
                      'mails':   0,
                     }

        divs = self.document.getElementsByTagName('td')
        for div in divs:
            if (div.hasAttribute('style') and
                    div.getAttribute('style') == "color:#ffffff;font-size:32px;font-weight:bold;letter-spacing:-2px" and
                    hasattr(div.firstChild, 'data')):
                self.name = div.firstChild.data
            if (div.hasAttribute('style') and
                    div.getAttribute('style') == "font-size:12px;font-weight:bold" and
                    hasattr(div.firstChild, 'data')):
                self.status = div.firstChild.data
            if div.hasAttribute('background'):
                m = self.PHOTO_REGEXP.match(div.getAttribute('background'))
                if m:
                    self.photos += [re.sub(u'thumb[0-2]_', u'image', div.getAttribute('background'))]
            if div.hasAttribute('width') and str(div.getAttribute('width')) == '226':
                trs = div.getElementsByTagName('tr')
                for tr in trs:
                    tds = tr.getElementsByTagName('td')
                    if len(tds) > 2 and hasattr(tds[2].firstChild, 'data'):
                        label = tds[0].firstChild.data
                        value = tds[2].firstChild.data
                    elif len(tds) == 2:
                        label = unicode(tds[0].childNodes[1].data)
                        value = tds[1].childNodes[1].data
                    else:
                        continue

                    m = self.STATS_VALUE_REGEXP.match(value)
                    if m and self.STATS2ID.has_key(label):
                        self.stats[self.STATS2ID[label]] = int(m.group(1).replace(' ', ''))

        divs = self.document.getElementsByTagName('div')
        for div in divs:
            if div.hasAttribute('id'):
                if div.getAttribute('id') == 'about_div':
                    self.parse_description(div)

                if div.getAttribute('id').startswith('tab_'):
                    self.parse_table(div)

        for tag in ('img', 'td'):
            imgs = self.document.getElementsByTagName(tag)
            for img in imgs:
                if img.hasAttribute('onclick'):
                    m = self.ID_REGEXP.match(img.getAttribute('onclick'))
                    if m:
                        self.id = int(m.group(2))
                        break
            if self.id:
                break

    def parse_description(self, div):
        # look for description

        description = ''
        for c in div.childNodes:
            if hasattr(c, 'data'):
                description += ''.join(c.data.split('\n')) # to strip \n
            elif hasattr(c, 'tagName') and c.tagName == 'br':
                description += '\n'

        self.description = description

    def parse_table(self, div):
        d = self.table[self.tables[div.getAttribute('id')]]
        fields = self.fields[self.tables[div.getAttribute('id')]]
        table = div.getElementsByTagName('table')[1]

        field1 = None
        field2 = None

        for tr in table.getElementsByTagName('tr'):
            tds = tr.getElementsByTagName('td')
            if len(tds) != 2:
                continue

            label1 = ''
            label2 = ''
            value1 = ''
            value2 = ''
            # Check for first column
            if len(tds[0].childNodes) > 0:
                b = len(tds[0].childNodes) > 2 and tds[0].childNodes[2]
                if b and hasattr(b, 'tagName') and b.tagName == 'b':
                    for child in b.childNodes:
                        label1 += child.data
                else:
                    for child in tds[0].childNodes:
                        if child.data != u'\xa0': # strip nbsp
                            value1 += child.data
                    value2 = value2.strip()

            # Check for second column
            if len(tds[1].childNodes) > 0:
                b = tds[1].childNodes[0]
                if b and hasattr(b, 'tagName') and b.tagName == 'b':
                    for child in b.firstChild.childNodes:
                        label2 += child.data
                else:
                    for child in tds[1].childNodes:
                        if hasattr(child, 'data') and child.data != u'\xa0': # strip nbsp
                            value2 += child.data

            if label1 and value2:
                # This is a typically tuple of key/value on the line.
                try:
                    fields[label1].put_value(d, value2)
                except KeyError:
                    warning('Unable to find "%s" (%s)' % (label1, repr(label1)))
            elif label1 and label2:
                # two titles, so there will have a list of value in
                # next lines on each columns
                field1 = fields[label1]
                field2 = fields[label2]
            elif not label1 and not label1:
                # two values, so it is a line of values
                if field1 and value1:
                    field1.put_value(d, value1)
                if field2 and value2:
                    field2.put_value(d, value2)

    def get_name(self):
        return self.name

    def get_description(self):
        return self.description

    def get_table(self):
        return self.table

    def get_id(self):
        return self.id

    def get_photos(self):
        return self.photos

    def get_status(self):
        return self.status

    def is_online(self):
        return self.status.find('en ligne') >= 0

    def get_stats(self):
        return self.stats
