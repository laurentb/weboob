# -*- coding: utf-8 -*-

# Copyright(C) 2015      Romain Bignon
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


__all__ = ['Javascript']


class Javascript(object):
    HEADER = """
  function btoa(str) {
    var buffer
      ;

    if (str instanceof Buffer) {
      buffer = str;
    } else {
      buffer = new Buffer(str.toString(), 'binary');
    }

    return buffer.toString('base64');
  }

  function atob(str) {
    return new Buffer(str, 'base64').toString('binary');
  }

  var document = {};
    """

    def __init__(self, script):
        try:
            import execjs
        except ImportError:
            raise ImportError('Please install PyExecJS')

        self.runner = execjs.get()

        self.ctx = self.runner.compile(self.HEADER + script)

    def call(self, *args, **kwargs):
        return self.ctx.call(*args, **kwargs)
