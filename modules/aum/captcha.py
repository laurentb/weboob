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

from __future__ import print_function

import hashlib
import sys

try:
    from PIL import Image
except ImportError:
    raise ImportError('Please install python-imaging')


class CaptchaError(Exception):
    pass


class Tile(object):
    hash = {
        'bc8d52d96058478a6def26226145d53b': 'A',
        'c62ecdfddb72b2feaed96cd9fe7c2802': 'A',
        '8b61cda8a3240d8fa5f2610424271300': 'AD',
        'f5dc63d37c7ea3375d86180f0ae62d05': 'AE',
        'fd562be230da7f767f4454148632201d': 'AF',
        '1860de576d8b0d1d87edc9dcb0b2a64c': 'AG',
        '53afa108d36186e6bd23631711ec3d8c': 'AJ',
        '6f2f9a1082a9230272c45117320f159d': 'AL',
        'e14249a774d24bacc6e2bcadd7f3df65': 'AM',
        '389330dbf3d85dea2dc40c6f9cf77d52': 'AN',
        '17526a3c2261b55f9cd237c4aa195099': 'AQ',
        '7e4820a9cc6c83a9fa60ff73ceb52157': 'AW',
        '90690d1209753a2bcfeafa890082a585': 'B',
        '2cf22e9ceace03a5f8ed3999e92d877e': 'C',
        'a1d0bf1a29600a82a6aa2b8b21651b0f': 'D',
        '9bb6909d647a0be3b2e7352d37374228': 'E',
        '38120c8346f16cd07a9194283787ee5e': 'F',
        'd41ff948fbc50a628c858b8e3e9e931c': 'G',
        '4cc9322d3361eb3f9fea7fc83579e40f': 'H',
        '837cd0f04e2d47ca6975745bdd0da640': 'I',
        'da0204fa51b38414051376cc1c27ba72': 'J',
        '199b1a9f9e1df1c2eddadcc4582957d7': 'JW',
        '5e8d3d5bd5f683d84b089f2cecc1e196': 'JX',
        'bc1fcf3546057d40d2db5454caacb3a5': 'JZ',
        'c2f5866ba3bf799ece8b202492d199bf': 'K',
        '7abe4091e11921afe6dac16509999010': 'KT',
        '281ef08e623184e5621a73b9ccec7c9a': 'KX',
        'b28e3fc06411de2ac7f53569bc3b42db': 'L',
        'd58a6c26649926f1145fb4b7b42d0554': 'LT',
        '4add630c6d124899fef814211975e344': 'M',
        '9740cefe1629d6bc149a72d5f2a4586d': 'N',
        '396f816f7e78e5c98de6404f8c4bd2ee': 'O',
        '31ae7c9536b6c6a96e30a77b70e4b2fd': 'P',
        '98ad9b1c32c05e6efc06637a166e4c42': 'PA',
        'a05cce33683025fb2c6708ee06f6028e': 'Q',
        '2852f51e8939bf9664fe064f7dacf310': 'R',
        '3798513fe87e786faa67552a140fd86f': 'S',
        '350b13811e34eeb63e3d7fb4b5eade5b': 'T',
        'a01b186cbc767e17d948ed04eff114a1': 'U',
        '8405f4d80ce80c4e6e9680fcfac4fe40': 'V',
        '17ed80e9cb9a585098ae6a55d8d1f5c0': 'W',
        'ae54ca77be5561330781a08dfbaff7a7': 'W',
        'bbded6a2ba5f521bba276bb843bf4c98': 'WXT',
        'ea662dd25fc528b84b832ce71ae3de61': 'WZ',
        '4eb23916138e7c01714431dbecfe8b96': 'X',
        'c02093d35d852339ff34f2b26873bf5a': 'XW',
        '65744e0c6ce0c56d04873dfd732533a7': 'Y',
        '315fb7dba7032004bd362cf0bb076733': 'YA',
        'ce12a68a4f15657bc5297a6cf698bc0a': 'YAQ',
        '275478ea2280351f7433a0606f962175': 'Z',
    }

    def __init__(self):
        self.map = []

    def append(self, pxls):
        self.map.append(pxls)

    def display(self):
        print('-' * (len(self.map) * 2 + 2))
        for y in xrange(len(self.map[0])):
            sys.stdout.write('|')
            for x in xrange(len(self.map)):
                sys.stdout.write('%s' % ('XX' if self.map[x][y] else '  '))
            print('|')
        print('-' * (len(self.map) * 2 + 2))

    def checksum(self):
        s = ''
        for pxls in self.map:
            for pxl in pxls:
                s += '%d' % (1 if pxl else 0)
        return hashlib.md5(s).hexdigest()

    @property
    def letter(self):
        checksum = self.checksum()
        try:
            return self.hash[checksum]
        except KeyError:
            print('Unable te resolve:')
            self.display()
            print('hash: %s' % checksum)
            raise CaptchaError()


class Captcha(object):
    def __init__(self, f):
        self.img = Image.open(f)
        self.w, self.h = self.img.size
        self.map = self.img.load()

        self.tiles = []

        tile = None
        for x in xrange(self.w):
            blank = True
            pxls = []
            for y in xrange(self.h):
                pxls.append(self[x,y])
                if self[x,y] != 0:
                    blank = False

            if tile:
                if blank:
                    tile = None
                else:
                    tile.append(pxls)
            elif not blank:
                tile = Tile()
                tile.append(pxls)
                self.tiles.append(tile)

    def __getitem__(self, (x, y)):
        return self.map[x % self.w, y % self.h]

    def __iter__(self):
        for tile in self.tiles:
            yield tile

    @property
    def text(self):
        s = ''
        for tile in self.tiles:
            s += tile.letter
        return s


class Decoder(object):
    def __init__(self):
        self.hash = {}

    def process(self):
        from aum.browser import AuMBrowser
        browser = AuMBrowser('')
        browser.openurl('/register2.php')
        c = Captcha(browser.openurl('/captcha.php'))

        for tile in c:
            checksum = tile.checksum()

            if checksum in self.hash:
                print('Skipping %s' % self.hash[checksum])
                continue

            tile.display()
            print('Checksum: %s' % checksum)
            ntry = 2
            while ntry:
                sys.stdout.write('Enter the letter: ')
                l = sys.stdin.readline().strip()

                ntry -= 1
                if len(l) != 1:
                    print('Error: please enter only one letter')
                elif l in self.hash.itervalues():
                    print('Warning! This letter has already been catched!')
                else:
                    ntry = 0

            self.hash[checksum] = l

    def main(self):
        try:
            while True:
                self.process()
        except KeyboardInterrupt:
            print('')
            print('hash = {')
            l = sorted(self.hash.iteritems(), key=lambda (k,v): (v,k))
            for hash, value in l:
                print('        \'%s\': %s' % (hash, value))

            print('}')

if __name__ == '__main__':
    d = Decoder()
    d.main()
