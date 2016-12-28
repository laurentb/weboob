# -*- coding: utf-8 -*-

# Copyright(C) 2014 Oleg Plakhotniuk
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

from bisect import bisect_left
from cStringIO import StringIO
from collections import namedtuple
import os
import subprocess
from tempfile import mkstemp


__all__ = ['decompress_pdf', 'get_pdf_rows']


def decompress_pdf(inpdf):
    """
    Takes PDF file contents as a string and returns decompressed version
    of the file contents, suitable for text parsing.

    External dependencies:
    MuPDF (http://www.mupdf.com).
    """

    inh, inname = mkstemp(suffix='.pdf')
    outh, outname = mkstemp(suffix='.pdf')
    os.write(inh, inpdf)
    os.close(inh)
    os.close(outh)

    subprocess.call(['mutool', 'clean', '-d', inname, outname])

    with open(outname) as f:
        outpdf = f.read()
    os.remove(inname)
    os.remove(outname)
    return outpdf


# fuzzy floats to smooth comparisons because lines are actually rects
# and seemingly-contiguous lines are actually not contiguous
class ApproxFloat(float):
    APPROX_THRESHOLD = 2

    @classmethod
    def _almost_eq(cls, a, b):
        return abs(a - b) < cls.APPROX_THRESHOLD

    def __eq__(self, other):
        return self._almost_eq(self, other)

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        return self - other < 0 and self != other

    def __le__(self, other):
        return self - other <= 0 or self == other

    def __gt__(self, other):
        return not self <= other

    def __ge__(self, other):
        return not self < other


Rect = namedtuple('Rect', ('x0', 'y0', 'x1', 'y1'))
TextRect = namedtuple('TextRect', ('x0', 'y0', 'x1', 'y1', 'text'))


def lt_to_coords(obj, ltpage):
    # in a pdf, 'y' coords are bottom-to-top
    return Rect(
        ApproxFloat(min(obj.x0, obj.x1)),
        ApproxFloat(min(ltpage.y1 - obj.y0, ltpage.y1 - obj.y1)),
        ApproxFloat(max(obj.x0, obj.x1)),
        ApproxFloat(max(ltpage.y1 - obj.y0, ltpage.y1 - obj.y1))
    )


def lttext_to_multilines(obj, ltpage):
    # text lines within 'obj' are probably the same height
    x0 = min(obj.x0, obj.x1)
    y0 = min(ltpage.y1 - obj.y0, ltpage.y1 - obj.y1)
    x1 = max(obj.x0, obj.x1)
    y1 = max(ltpage.y1 - obj.y0, ltpage.y1 - obj.y1)

    lines = obj.get_text().rstrip('\n').split('\n')
    h = (y1 - y0) / len(lines)

    for n, line in enumerate(lines):
        yield TextRect(x0, y0 + n * h, x1, y0 + n * h + h, line)


def is_rect_contained_in(inner, outer):
    return (outer.x0 <= inner.x0 <= inner.x1 <= outer.x1 and
            outer.y0 <= inner.y0 <= inner.y1 <= outer.y1)


ANGLE_VERTICAL = 0
ANGLE_HORIZONTAL = 1
ANGLE_OTHER = 2


def angle(r):
    if r.x0 == r.x1:
        return ANGLE_VERTICAL
    elif r.y0 == r.y1:
        return ANGLE_HORIZONTAL
    return ANGLE_OTHER


def build_boxes(objs):
    # TODO find rects that are not drawn by 4 lines top-right-bottom-left
    boxes = []

    objs = [obj for obj in objs if angle(obj) in (ANGLE_HORIZONTAL, ANGLE_VERTICAL)]

    i = 0
    while i + 3 < len(objs):
        angles = tuple(map(angle, objs[i:i+4]))
        if angles != (ANGLE_HORIZONTAL, ANGLE_VERTICAL, ANGLE_HORIZONTAL, ANGLE_VERTICAL):
            i += 1
            continue

        if not (objs[i].x1 == objs[i+1].x1 and objs[i].y0 == objs[i+1].y0 and
                objs[i+1].x1 == objs[i+2].x1 and objs[i+1].y1 == objs[i+2].y1 and
                objs[i+2].x0 == objs[i+3].x0 and objs[i+2].y1 == objs[i+3].y1 and
                objs[i+3].x0 == objs[i].x0 and objs[i].y0 == objs[i].y0):
            i += 1
            continue

        boxes.append(Rect(objs[i].x0, objs[i].y0, objs[i+1].x0, objs[i+1].y1))
        i += 4

    return boxes


class OrderedMap(object):
    # keys are ordered by total ordering on key objects

    def __init__(self):
        self.data = []

    def __setitem__(self, k, v):
        pos = bisect_left(self.data, (k,))
        try:
            if self.data[pos][0] == k:
                self.data[pos] = (k, v)
                return
        except IndexError:
            pass
        self.data.insert(pos, (k, v))

    def __getitem__(self, k):
        pos = bisect_left(self.data, (k,))
        if pos >= len(self.data):
            raise KeyError()
        elif self.data[pos][0] == k:
            return self.data[pos][1]
        else:
            raise KeyError()

    def __delitem__(self, k):
        pos = bisect_left(self.data, (k,))
        if pos >= len(self.data):
            raise KeyError()
        elif self.data[pos][0] == k:
            del self.data[pos]
        else:
            raise IndexError()

    def setdefault(self, k, v):
        try:
            return self[k]
        except KeyError:
            self[k] = v
            return v

    def __iter__(self):
        return iter(t[1] for t in self.data)


def build_rows(boxes):
    rows = OrderedMap()
    for box in boxes:
        row = rows.setdefault((box.y0, box.y1), [])
        row.append(box)

    for row in rows:
        row.sort(key=lambda box: box.x0)
    return rows


def arrange_texts_in_rows(trects, rows):
    trows = {}
    for trect in trects:
        for nrow, row in enumerate(rows):
            for ncell, cell in enumerate(row):
                if is_rect_contained_in(trect, cell):
                    if nrow not in trows:
                        trows[nrow] = [[] for _ in row]
                    trows[nrow][ncell].append(trect.text)
    return trows


def get_pdf_rows(data):
    """
    Takes PDF file content as string and yield table row data for each page.

    A dict is yielded for each page. Each dict contains rows as values.
    Each row is a list of cells. Each cell is a list of strings present in the cell.
    Note that the rows may belong to different tables.

    There are no logic tables in PDF format, so this parses PDF drawing instructions
    and tries to find rectangles and arrange them in rows, then arrange text in
    the rectangles.

    External dependencies:
    PDFMiner (http://www.unixuser.org/~euske/python/pdfminer/index.html).
    """

    try:
        from pdfminer.pdfparser import PDFParser, PDFSyntaxError
    except ImportError:
        raise ImportError('Please install python-pdfminer')

    try:
        from pdfminer.pdfdocument import PDFDocument
        from pdfminer.pdfpage import PDFPage
        newapi = True
    except ImportError:
        from pdfminer.pdfparser import PDFDocument
        newapi = False
    from pdfminer.converter import PDFPageAggregator
    from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
    from pdfminer.layout import LAParams, LTRect, LTTextBox, LTTextLine

    parser = PDFParser(StringIO(data))
    try:
        if newapi:
            doc = PDFDocument(parser)
        else:
            doc = PDFDocument()
            parser.set_document(doc)
            doc.set_parser(parser)
    except PDFSyntaxError:
        return

    rsrcmgr = PDFResourceManager()
    device = PDFPageAggregator(rsrcmgr, laparams=LAParams())

    interpreter = PDFPageInterpreter(rsrcmgr, device)
    if newapi:
        pages = PDFPage.get_pages(StringIO(data), check_extractable=True)
    else:
        doc.initialize()
        pages = doc.get_pages()

    for npage, page in enumerate(pages):
        interpreter.process_page(page)
        page_layout = device.get_result()

        texts = sum([list(lttext_to_multilines(obj, page_layout)) for obj in page_layout._objs if isinstance(obj, (LTTextBox, LTTextLine))], [])
        lines = [lt_to_coords(obj, page_layout) for obj in page_layout._objs if isinstance(obj, LTRect)]

        boxes = build_boxes(lines)
        rows = build_rows(boxes)
        textrows = arrange_texts_in_rows(texts, rows)

        yield textrows
    device.close()
