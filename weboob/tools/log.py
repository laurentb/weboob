# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

from logging import Formatter, getLogger as _getLogger
import sys


__all__ = ['getLogger', 'createColoredFormatter']


RESET_SEQ = "\033[0m"
COLOR_SEQ = "%s%%s" + RESET_SEQ

COLORS = {
    'DEBUG': COLOR_SEQ % "\033[36m",
    'INFO': "%s",
    'WARNING': COLOR_SEQ % "\033[1;1m",
    'ERROR': COLOR_SEQ % "\033[1;31m",
    'CRITICAL': COLOR_SEQ % ("\033[1;33m\033[1;41m"),
}

def getLogger(name, parent=None):
    if parent:
        name = parent.name + '.' + name
    return _getLogger(name)

class ColoredFormatter(Formatter):
    """
    Class written by airmind:
    http://stackoverflow.com/questions/384076/how-can-i-make-the-python-logging-output-to-be-colored
    """
    def format(self, record):
        levelname = record.levelname
        msg = Formatter.format(self, record)
        if levelname in COLORS:
            msg = COLORS[levelname] % msg
        return msg

def createColoredFormatter(stream, format):
    if (sys.platform != 'win32') and stream.isatty():
        return ColoredFormatter(format)
    else:
        return Formatter(format)

