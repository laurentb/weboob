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


from weboob.tools.log import getLogger


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

  document = {};

  /* JS code checks that some PhantomJS globals aren't defined on the
   * global window object; put an empty window object, so that all these
   * tests fail.
   * It then tests the user agent against some known scrappers; just put
   * the default Tor user agent in there.
   */
  window = {};
  navigator = {
      userAgent: "Mozilla/5.0 (Windows NT 6.1; rv:52.0) Gecko/20100101 Firefox/52.0"
  };
    """

    def __init__(self, script, logger=None):
        try:
            import execjs
        except ImportError:
            raise ImportError('Please install PyExecJS')

        self.runner = execjs.get()
        self.logger = getLogger('js', logger)

        self.ctx = self.runner.compile(self.HEADER + script)

    def call(self, *args, **kwargs):
        retval = self.ctx.call(*args, **kwargs)

        self.logger.debug('Calling %s%s = %s', args[0], args[1:], retval)

        return retval
