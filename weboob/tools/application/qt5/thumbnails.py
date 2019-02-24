# -*- coding: utf-8 -*-

# Copyright(C) 2016 Vincent A
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from time import mktime

from PyQt5.QtCore import QVariant, Qt, QSize
from PyQt5.QtGui import QIcon, QPixmap, QImage
from weboob.capabilities.image import BaseImage
try:
    import vignette  # https://github.com/hydrargyrum/vignette
except ImportError:
    vignette = None


__all__ = ('try_get_thumbnail', 'store_thumbnail')


def find_url(obj):
    if isinstance(obj, BaseImage):
        return obj.url

    try:
        obj.thumbnail
    except AttributeError:
        pass
    else:
        return obj.thumbnail.url


def try_get_thumbnail(obj):
    if vignette is None:
        return

    url = find_url(obj)
    if not url:
        return

    try:
        ts = mktime(obj.date.timetuple())
    except AttributeError:
        return

    path = vignette.try_get_thumbnail(url, mtime=ts)
    if path:
        return QVariant(QIcon(QPixmap(path)))


def ideal_thumb_size(size):
    if size[0] <= 128 and size[1] <= 128:
        return 'normal', None
    if size[0] <= 256 and size[1] <= 256:
        return 'large', None
    return 'large', 256


def load_qimg(obj, *attrs):
    try:
        for attr in attrs:
            obj = getattr(obj, attr)
    except AttributeError:
        return QImage()
    if not obj:
        return QImage()

    return QImage.fromData(obj)


def store_thumbnail(obj):
    if vignette is None:
        return

    url = find_url(obj)
    if not url:
        return

    try:
        ts = mktime(obj.date.timetuple())
    except AttributeError:
        return

    path = vignette.try_get_thumbnail(url, mtime=ts)
    if path:
        # thumbnail already exists
        return

    qimg = load_qimg(obj, 'data')
    if qimg.isNull():
        qimg = load_qimg(obj, 'thumbnail', 'data')
    if qimg.isNull():
        return

    format, size = ideal_thumb_size((qimg.width(), qimg.height()))
    if size:
        qimg = qimg.scaled(QSize(size, size), Qt.KeepAspectRatio, Qt.SmoothTransformation)

    path = vignette.create_temp(format)
    qimg.save(path)
    vignette.put_thumbnail(url, format, path, mtime=ts)
