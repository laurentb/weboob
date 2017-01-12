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


Rect = namedtuple('Rect', ('x0', 'y0', 'x1', 'y1'))
TextRect = namedtuple('TextRect', ('x0', 'y0', 'x1', 'y1', 'text'))


def almost_eq(a, b):
    return abs(a - b) < 2


def lt_to_coords(obj, ltpage):
    # in a pdf, 'y' coords are bottom-to-top
    # in a pdf, coordinates are very often almost equal but not strictly equal

    x0 = (min(obj.x0, obj.x1))
    y0 = (min(ltpage.y1 - obj.y0, ltpage.y1 - obj.y1))
    x1 = (max(obj.x0, obj.x1))
    y1 = (max(ltpage.y1 - obj.y0, ltpage.y1 - obj.y1))

    x0 = round(x0)
    y0 = round(y0)
    x1 = round(x1)
    y1 = round(y1)

    # in a pdf, straight lines are actually rects, make them as thin as possible
    if almost_eq(x1, x0):
        x1 = x0
    if almost_eq(y1, y0):
        y1 = y0

    return Rect(x0, y0, x1, y1)


def lttext_to_multilines(obj, ltpage):
    # text lines within 'obj' are probably the same height
    x0 = (min(obj.x0, obj.x1))
    y0 = (min(ltpage.y1 - obj.y0, ltpage.y1 - obj.y1))
    x1 = (max(obj.x0, obj.x1))
    y1 = (max(ltpage.y1 - obj.y0, ltpage.y1 - obj.y1))

    lines = obj.get_text().rstrip('\n').split('\n')
    h = (y1 - y0) / len(lines)

    for n, line in enumerate(lines):
        yield TextRect((x0), (y0 + n * h), (x1), (y0 + n * h + h), line)


# fuzzy floats to smooth comparisons because lines are actually rects
# and seemingly-contiguous lines are actually not contiguous
class ApproxFloat(float):
    def __eq__(self, other):
        return almost_eq(self, other)

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


ANGLE_VERTICAL = 0
ANGLE_HORIZONTAL = 1
ANGLE_OTHER = 2


def angle(r):
    if r.x0 == r.x1:
        return ANGLE_VERTICAL
    elif r.y0 == r.y1:
        return ANGLE_HORIZONTAL
    return ANGLE_OTHER


class ApproxVecDict(dict):
    # since coords are never strictly equal, search coords around
    # store vectors and points

    def __getitem__(self, coords):
        x, y = coords
        for i in (0, -1, 1):
            for j in (0, -1, 1):
                try:
                    return super(ApproxVecDict, self).__getitem__((x+i, y+j))
                except KeyError:
                    pass
        raise KeyError()

    def get(self, k, v=None):
        try:
            return self[k]
        except KeyError:
            return v


class ApproxRectDict(dict):
    # like ApproxVecDict, but store rects
    def __getitem__(self, coords):
        x0, y0, x1, y1 = coords

        for i in (0, -1, 1):
            for j in (0, -1, 1):
                if x0 == x1:
                    for j2 in (0, -1, 1):
                        try:
                            return super(ApproxRectDict, self).__getitem__((x0+i, y0+j, x0+i, y1+j2))
                        except KeyError:
                            pass
                elif y0 == y1:
                    for i2 in (0, -1, 1):
                        try:
                            return super(ApproxRectDict, self).__getitem__((x0+i, y0+j, x1+i2, y0+j))
                        except KeyError:
                            pass
                else:
                    return super(ApproxRectDict, self).__getitem__((x0, y0, x1, y1))

        raise KeyError()


def uniq_lines(lines):
    new = ApproxRectDict()
    for line in lines:
        line = tuple(line)
        try:
            new[line]
        except KeyError:
            new[line] = None
    return [Rect(*k) for k in new.keys()]


def build_rows(lines):
    points = ApproxVecDict()

    # for each top-left point, build tuple with lines going down and lines going right
    for line in lines:
        a = angle(line)
        if a not in (ANGLE_HORIZONTAL, ANGLE_VERTICAL):
            continue

        coord = (line.x0, line.y0)
        plines = points.get(coord)
        if plines is None:
            plines = points[coord] = tuple([] for _ in xrange(2))

        plines[a].append(line)

    boxes = ApproxVecDict()
    for plines in points.itervalues():
        if not (plines[ANGLE_HORIZONTAL] and plines[ANGLE_VERTICAL]):
            continue
        for hline in plines[ANGLE_HORIZONTAL]:
            try:
                vparallels = points[hline.x1, hline.y0][ANGLE_VERTICAL]
            except KeyError:
                continue
            if not vparallels:
                continue

            for vline in plines[ANGLE_VERTICAL]:
                try:
                    hparallels = points[vline.x0, vline.y1][ANGLE_HORIZONTAL]
                except KeyError:
                    continue
                if not hparallels:
                    continue

                hparallels = [hpar for hpar in hparallels if almost_eq(hpar.x1, hline.x1)]
                if not hparallels:
                    continue
                vparallels = [vpar for vpar in vparallels if almost_eq(vpar.y1, vline.y1)]
                if not vparallels:
                    continue

                assert len(hparallels) == 1 and len(vparallels) == 1
                assert almost_eq(hparallels[0].y0, vparallels[0].y1)
                assert almost_eq(vparallels[0].x0, hparallels[0].x1)

                box = Rect(hline.x0, hline.y0, hline.x1, vline.y1)
                boxes.setdefault((vline.y0, vline.y1), []).append(box)

    rows = boxes.values()
    for row in rows:
        row.sort(key=lambda box: box.x0)
    rows.sort(key=lambda row: row[0].y0)

    return rows


def find_in_table(rows, rect):
    for j, row in enumerate(rows):
        if ApproxFloat(row[0].y0) > rect.y1:
            break

        if not (ApproxFloat(row[0].y0) <= rect.y0 and ApproxFloat(row[0].y1) >= rect.y1):
            continue

        for i, box in enumerate(row):
            if ApproxFloat(box.x0) <= rect.x0 and ApproxFloat(box.x1) >= rect.x1:
                return i, j


def arrange_texts_in_rows(rows, trects):
    table = [[[] for _ in row] for row in rows]

    for trect in trects:
        pos = find_in_table(rows, trect)
        if not pos:
            continue
        table[pos[1]][pos[0]].append(trect.text)
    return table


def get_pdf_rows(data, miner_layout=True):
    """
    Takes PDF file content as string and yield table row data for each page.

    For each page in the PDF, the function yields a list of rows.
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
    from pdfminer.layout import LAParams, LTRect, LTTextBox, LTTextLine, LTLine, LTChar

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
    if miner_layout:
        device = PDFPageAggregator(rsrcmgr, laparams=LAParams())
    else:
        device = PDFPageAggregator(rsrcmgr)

    interpreter = PDFPageInterpreter(rsrcmgr, device)
    if newapi:
        pages = PDFPage.get_pages(StringIO(data), check_extractable=True)
    else:
        doc.initialize()
        pages = doc.get_pages()

    for npage, page in enumerate(pages):
        interpreter.process_page(page)
        page_layout = device.get_result()

        texts = sum([list(lttext_to_multilines(obj, page_layout)) for obj in page_layout._objs if isinstance(obj, (LTTextBox, LTTextLine, LTChar))], [])
        if not miner_layout:
            texts.sort(key=lambda t: (t.y0, t.x0))

        lines = list(uniq_lines(lt_to_coords(obj, page_layout) for obj in page_layout._objs if isinstance(obj, (LTRect, LTLine))))

        boxes = build_rows(lines)
        textrows = arrange_texts_in_rows(boxes, texts)

        yield textrows
    device.close()
