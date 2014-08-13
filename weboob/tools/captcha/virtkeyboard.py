# -*- coding: utf-8 -*-

# Copyright(C) 2011  Pierre Mazière
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
import tempfile
from string import maketrans

try:
    from PIL import Image
except ImportError:
    raise ImportError('Please install python-imaging')


class VirtKeyboardError(Exception):
    pass


class VirtKeyboard(object):
    """
    Handle a virtual keyboard.

    :attribute margin: Margin used by :meth:`get_symbol_coords̀` to reduce size
        of each "key" of the virtual keyboard. This attribute is always
        converted to a 4-tuple, and has the same semantic as the CSS
        ``margin`` property (top, right, bottom, right), in pixels.
    :type margin: int or float or (2|3|4)-tuple
    """
    margin = None

    def __init__(self, file=None, coords=None, color=None, convert=None):
        # file: virtual keyboard image
        # coords: dictionary <value to return>:<tuple(x1,y1,x2,y2)>
        # color: color of the symbols in the image
        #        depending on the image, it can be a single value or a tuple
        # convert: if not None, convert image to this target type (for example 'RGB')

        if file is not None:
            assert color, 'No color provided !'
            self.load_image(file, color, convert)

        if type(self.margin) in (int, float):
            self.margin = (self.margin,) * 4
        elif self.margin is not None:
            if len(self.margin) == 2:
                self.margin = self.margin + self.margin
            elif len(self.margin) == 3:
                self.margin = self.margin + (self.margin[1],)
            assert len(self.margin) == 4

        if coords is not None:
            self.load_symbols(coords)

    def load_image(self, file, color, convert=None):
        self.image = Image.open(file)

        if convert is not None:
            self.image = self.image.convert(convert)

        self.bands = self.image.getbands()
        if isinstance(color, int) and not isinstance(self.bands, str) and len(self.bands) != 1:
            raise VirtKeyboardError("Color requires %i component but only 1 is provided"
                                    % len(self.bands))
        if not isinstance(color, int) and len(color) != len(self.bands):
            raise VirtKeyboardError("Color requires %i components but %i are provided"
                                    % (len(self.bands), len(color)))
        self.color = color

        self.width, self.height = self.image.size
        self.pixar = self.image.load()

    def load_symbols(self, coords):
        self.coords = {}
        self.md5 = {}
        for i in coords:
            coord = self.get_symbol_coords(coords[i])
            if coord == (-1, -1, -1, -1):
                continue
            self.coords[i] = coord
            self.md5[i] = self.checksum(self.coords[i])

    def check_color(self, pixel):
        return pixel == self.color

    def get_symbol_coords(self, (x1, y1, x2, y2)):
        if self.margin:
            top, right, bottom, left = self.margin
            x1, y1, x2, y2 = x1 + left, y1 + top, x2 - right, y2 - bottom

        newY1 = -1
        newY2 = -1
        for y in range(y1, min(y2 + 1, self.height)):
            empty_line = True
            for x in range(x1, min(x2 + 1, self.width)):
                if self.check_color(self.pixar[x, y]):
                    empty_line = False
                    if newY1 == -1:
                        newY1 = y
                        break
                    else:
                        break
            if newY1 != -1 and not empty_line:
                newY2 = y
        newX1 = -1
        newX2 = -1
        for x in range(x1, min(x2 + 1, self.width)):
            empty_column = True
            for y in range(y1, min(y2 + 1, self.height)):
                if self.check_color(self.pixar[x, y]):
                    empty_column = False
                    if newX1 == -1:
                        newX1 = x
                        break
                    else:
                        break
            if newX1 != -1 and not empty_column:
                newX2 = x
        return (newX1, newY1, newX2, newY2)

    def checksum(self, (x1, y1, x2, y2)):
        s = ''
        for y in range(y1, min(y2 + 1, self.height)):
            for x in range(x1, min(x2 + 1, self.width)):
                if self.check_color(self.pixar[x, y]):
                    s += "."
                else:
                    s += " "
        return hashlib.md5(s).hexdigest()

    def get_symbol_code(self, md5sum):
        for i in self.md5:
            if md5sum == self.md5[i]:
                return i
        raise VirtKeyboardError('Symbol not found')

    def check_symbols(self, symbols, dirname):
        # symbols: dictionary <symbol>:<md5 value>
        for s in symbols:
            try:
                self.get_symbol_code(symbols[s])
            except VirtKeyboardError:
                if dirname is None:
                    dirname = tempfile.mkdtemp(prefix='weboob_session_')
                self.generate_MD5(dirname)
                raise VirtKeyboardError("Symbol '%s' not found; all symbol hashes are available in %s"
                                        % (s, dirname))

    def generate_MD5(self, dir):
        for i in self.coords:
            width = self.coords[i][2] - self.coords[i][0] + 1
            height = self.coords[i][3] - self.coords[i][1] + 1
            img = Image.new(''.join(self.bands), (width, height))
            matrix = img.load()
            for y in range(height):
                for x in range(width):
                    matrix[x, y] = self.pixar[self.coords[i][0] + x, self.coords[i][1] + y]
            img.save(dir + "/" + self.md5[i] + ".png")


class MappedVirtKeyboard(VirtKeyboard):
    def __init__(self, file, document, img_element, color, map_attr="onclick", convert=None):
        map_id = img_element.attrib.get("usemap")[1:]
        map = document.find("//map[@id='" + map_id + "']")
        if map is None:
            map = document.find("//map[@name='" + map_id + "']")

        coords = {}
        for area in map.getiterator("area"):
            code = area.attrib.get(map_attr)
            area_coords = []
            for coord in area.attrib.get("coords").split(','):
                area_coords.append(int(coord))
            coords[code] = tuple(area_coords)

        super(MappedVirtKeyboard, self).__init__(file, coords, color, convert)


class GridVirtKeyboard(VirtKeyboard):
    """
    Make a virtual keyboard where "keys" are distributed on a grid.
    For example: https://www.esgbl.com/part/fr/idehom.html

    Parameters:
        :param symbols: Sequence of symbols, ordered in the grid from left to
            right and up to down
        :type symbols: iterable
        :param rows: Row count of the grid
        :type rows: int
        :param cols: Column count of the grid
        :type cols: int
        :param image: File-like object to be used as data source
        :type image: file
        :param color: Color of the meaningful pixels
        :type color: 3-tuple
        :param convert: Mode to which convert color of pixels, see
            :meth:`Image.Image.convert` for more information

    Attributes:
        :attribute symbols: Association table between symbols and md5s
        :type symbols: dict
    """
    symbols = {}

    def __init__(self, symbols, rows, cols, image, color, convert=None):
        self.load_image(image, color, convert)

        tileW = float(self.width) / cols
        tileH = float(self.height) / rows
        positions = ((s, i * tileW % self.width, i / cols * tileH) \
                     for i, s in enumerate(symbols))
        coords = dict((s, tuple(map(int, (x, y, x + tileW, y + tileH)))) \
                      for (s, x, y) in positions)

        super(GridVirtKeyboard, self).__init__()

        self.load_symbols(coords)

    def load_symbols(self, coords):
        super(GridVirtKeyboard, self).load_symbols(coords)
        symbol_codes = map(self.get_symbol_code, self.symbols.itervalues())
        self._trans = maketrans(''.join(self.symbols), ''.join(symbol_codes))

    def get_string_code(self, string):
        return str(string).translate(self._trans)
