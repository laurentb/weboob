# -*- coding: utf-8 -*-

# Copyright(C) 2009-2011  Romain Bignon
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


import hashlib
import sys
import Image

class TileError(Exception):
    def __init__(self, msg, tile = None):
        Exception.__init__(self, msg)
        self.tile = tile


class Captcha(object):
    def __init__(self, file):
        self.inim = Image.open(file)
        self.nx,self.ny = self.inim.size
        self.inmat = self.inim.load()
        self.map = {}

        self.tiles = [[Tile(x+5*y+1) for y in xrange(5)] for x in xrange(5)]

    def __getitem__(self, (x, y)):
        return self.inmat[x % self.nx, y % self.ny]

    def all_coords(self):
        for y in xrange(self.ny):
            for x in xrange(self.nx):
                yield x, y

    def get_codes(self, code):
        s = ''
        for c in code:
            s += '%02d' % self.map[int(c)].id
        return s

    def build_tiles(self):
        y = 1
        ty = 0
        while y < self.ny:
            x = 1
            tx = 0
            while x < self.nx:
                tile = self.tiles[tx][ty]
                for j in xrange(26):
                    l = []
                    tile.map.append(l)
                    for i in xrange(26):
                        if self[x+i,y+j] > 20:
                            l.append('.')
                            tile.valid = True
                        else:
                            l.append(' ')

                if tile.valid:
                    self.map[tile.get_num()] = tile

                x += 27
                tx += 1

            y += 27
            ty += 1

class Tile(object):
    hash = {'4a6eff78f6c6f172b75bf9fd7fd36d5d': 0,
            '70019df58ec6e96d983507de86529058': 1,
            '683a3700dbd1b9019b5ad3ca39c545d3': 2,
            '998935d6f4111bd586001468a9c705a7': 3,
            'a5cca8bf800fa505cf7ae5039b0cc73c': 4,
            '2317a585e19c4f245cdc8acda51e4542': 5,
            '956958628d014f6e6bf59d88cd254dc6': 6,
            '13c35a4e7bf18e95186311876e66dd95': 7,
            '736894876d76899a5cfecc745b095121': 8,
            'ff41cd68224bece411c7fc876ab05a1d': 9
           }

    def __init__(self, _id):
        self.id = _id
        self.valid = False
        self.map = []

    def __repr__(self):
        return "<Tile(%02d) valid=%s>" % (self.id, self.valid)

    def checksum(self):
        s = ''
        for pxls in self.map:
            for pxl in pxls:
                s += pxl
        return hashlib.md5(s).hexdigest()

    def get_num(self):
        sum = self.checksum()
        try:
            return self.hash[sum]
        except KeyError:
            raise TileError('Tile not found', self)

    def display(self):
        for pxls in self.map:
            for pxl in pxls:
                sys.stdout.write(pxl)
            sys.stdout.write('\n')
        print self.checksum()
