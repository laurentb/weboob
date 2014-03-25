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

from collections import defaultdict
from logging import Formatter, getLogger as _getLogger
import sys


__all__ = ['getLogger', 'createColoredFormatter', 'settings']


RESET_SEQ = "\033[0m"
COLOR_SEQ = "%s%%s" + RESET_SEQ

COLORS = {
    'DEBUG': COLOR_SEQ % "\033[36m",
    'INFO': "%s",
    'WARNING': COLOR_SEQ % "\033[1;1m",
    'ERROR': COLOR_SEQ % "\033[1;31m",
    'CRITICAL': COLOR_SEQ % ("\033[1;33m\033[1;41m"),
}


# Global settings f logger.
settings = defaultdict(lambda: None)


def getLogger(name, parent=None):
    if parent:
        name = parent.name + '.' + name
    logger =  _getLogger(name)
    logger.settings = settings
    return logger


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
