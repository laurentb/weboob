
import weboob.tools.captcha.virtkeyboard as OLD

# can't import *, __all__ is incomplete...
for attr in dir(OLD):
    globals()[attr] = getattr(OLD, attr)


try:
    __all__ = OLD.__all__
except AttributeError:
    pass


class SimpleVirtualKeyboard(object):
    """Handle a virtual keyboard where "keys" are distributed on a simple grid.

    Parameters:
        :param cols: Column count of the grid
        :type cols: int
        :param rows: Row count of the grid
        :type rows: int
        :param image: File-like object to be used as data source
        :type image: file
        :param convert: Mode to which convert color of pixels, see
            :meth:`Image.Image.convert` for more information
        :param matching_symbols: symbol that match all case of image grid from left to right and top
                                 to down, European reading way.
        :type matching_symbols: iterable
        :param matching_symbols_coords: dict mapping matching website symbols to their image coords
                                        (x0, y0, x1, y1) on grid image from left to right and top to
                                        down, European reading way. It's not symbols in the image.
        :type matching_symbols_coords: dict[str:4-tuple(int)]
        :param browser: Browser of weboob session.
                        Allow to dump tiles files in same directory than session folder
        :type browser: obj(Browser)

    Attributes:
        :attribute codesep: Output separator between matching symbols
        :type codesep: str
        :param margin: Useless image pixel to cut.
                       See :func:`cut_margin`.
        :type margin: 4-tuple(int), same as HTML margin: (top, right, bottom, left).
                      or 2-tuple(int), (top = bottom, right = left),
                      or int, top = right = bottom = left
        :attribute tile_margin: Useless tile pixel to cut.
                                See :func:`cut_margin`.
        :attribute symbols: Association table between image symbols and md5s
        :type symbols: dict[str:str] or dict[str:n-tuple(str)]
        :attribute convert: Mode to which convert color of pixels, see
            :meth:`Image.Image.convert` for more information
        :attribute alter: Allow custom main image alteration. Then overwrite :func:`alter_image`.
        :type alter: boolean
    """

    codesep = ''
    margin = None
    tile_margin = None
    symbols = None
    convert = None

    def __init__(self, file, cols, rows, matching_symbols=None, matching_symbols_coords=None, browser=None):
        self.cols = cols
        self.rows = rows

        # Needed even if init is overwrite
        self.path = self.build_path(browser)

        # Get self.image
        self.load_image(file, self.margin, self.convert)

        # Get self.tiles
        self.get_tiles( matching_symbols=matching_symbols,
                        matching_symbols_coords=matching_symbols_coords)

        # Tiles processing
        self.cut_tiles(self.tile_margin)
        self.hash_md5_tiles()

    def build_path(self, browser=None):
        if browser and browser.responses_dirname:
            return browser.responses_dirname
        else:
            return tempfile.mkdtemp(prefix='weboob_session_')

    def load_image(self, file, margin=None, convert=None):
        self.image = Image.open(file)
        # Resize image if margin is given
        if margin:
            self.image = self.cut_margin(self.image, margin)
        if convert:
            self.image = self.image.convert(convert)
        # Give possibility to alter image before get tiles, overwrite :func:`alter_image`.
        self.alter_image()
        self.width, self.height = self.image.size

    def alter_image(self):
        pass

    def cut_margin(self, image, margin):
        width, height = image.size

        # Verify the magin value format
        if type(margin) is int:
            margin = (margin, margin, margin, margin)
        elif len(margin) == 2:
            margin = (margin[0], margin[1], margin[0], margin[1])
        elif len(margin) == 4:
            margin = margin
        else:
            assert (len(margin) == 3) & (len(margin) > 4), \
                "Margin format is wrong."

        assert ((margin[0] + margin[2]) < height) & ((margin[1] + margin[3]) < width), \
            "Margin is too high, there is not enough pixel to cut."

        image = image.crop((0 + margin[3],
                            0 + margin[0],
                            width - margin[1],
                            height - margin[2]
                            ))
        return image

    def get_tiles(self, matching_symbols=None, matching_symbols_coords=None):
        self.tiles = []

        # Tiles coords are given
        if matching_symbols_coords:
            for matching_symbol in matching_symbols_coords:
                self.tiles.append(Tile( matching_symbol=matching_symbol,
                                        coords=matching_symbols_coords[matching_symbol]
                                 ))
            return

        assert (not self.width%self.cols) & (not self.height%self.rows), \
            "Image width and height are not multiple of cols and rows. Please resize image with attribute `margin`."

        # Tiles coords aren't given, calculate them
        self.tileW = self.width // self.cols
        self.tileH = self.height // self.rows

        # Matching symbols aren't given, default value is range(columns*rows)
        if not matching_symbols:
            matching_symbols = ['%s' % i for i in range(self.cols*self.rows)]

        assert len(matching_symbols) == (self.cols*self.rows), \
            "Number of website matching symbols is not equal to the number of cases on the image."

        # Calculate tiles coords for each matching symbol from 1-dimension to 2-dimensions
        for index, matching_symbol in enumerate(matching_symbols):
            coords = self.get_tile_coords_in_grid(index)
            self.tiles.append(Tile(matching_symbol=matching_symbol, coords=coords))

    def get_tile_coords_in_grid(self, case_index):
        # Get the top left pixel coords of the tile
        x0 = (case_index % self.cols) * self.tileW
        y0 = (case_index // self.cols) * self.tileH

        # Get the bottom right coords of the tile
        x1 = x0 + self.tileW
        y1 = y0 + self.tileH

        coords = (x0, y0, x1, y1)
        return(coords)

    def cut_tiles(self, tile_margin=None):
        for tile in self.tiles:
            tile.image = self.image.crop(tile.coords)

        # Resize tile if margin is given
        if tile_margin:
            for tile in self.tiles:
                tile.image = self.cut_margin(tile.image, tile_margin)

    def hash_md5_tiles(self):
        for tile in self.tiles:
            tile.md5 = hashlib.md5(tile.image.tobytes()).hexdigest()

    def dump_tiles(self, path):
        for tile in self.tiles:
            tile.image.save('{}/{}.png'.format(path, tile.md5))

    def get_string_code(self, password):
        word = []

        for digit in password:
            for tile in self.tiles:
                if tile.md5 in self.symbols[digit]:
                    word.append(tile.matching_symbol)
                    break
            else:
                # Dump file only if the symbol is not found
                self.dump_tiles(self.path)
                raise VirtKeyboardError("Symbol '%s' not found; all symbol hashes are available in %s"
                                        % (digit, self.path))
        return self.codesep.join(word)
