# -*- coding: utf-8 -*-

# Copyright(C) 2012 Johann Broudin
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

import httplib
import socket
import ssl
import hashlib
from urlparse import urlsplit


__all__ = ['HTTPSVerifiedConnection', 'HellHTTPS']


PROXY_PORT = 8080


class HTTPSVerifiedConnection(httplib.HTTPSConnection):
    """
    This class allows communication via SSL, and will checks certificates
    """

    def __init__(self, host, port=None, key_file=None, cert_file=None,
                 ca_file=None, strict=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
                 callBack=None):
        httplib.HTTPSConnection.__init__(self, host, port, key_file,
                cert_file, strict, timeout)
        self.ca_file = ca_file
        self.callBack = callBack
        self.certificate = None

    def connect(self):
        """
        Connect to a host on a given port and check the certificate
        This is almost the same than the conect of HTTPSConnection, but adds
        some function for SSL certificate verification
        """

        sock = socket.create_connection((self.host, self.port), self.timeout)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()

        if self.ca_file:
            self.sock = ssl.wrap_socket(sock,
                                        self.key_file,
                                        self.cert_file,
                                        ca_certs = self.ca_file,
                                        cert_reqs=ssl.CERT_REQUIRED)
        else:
            self.sock = ssl.wrap_socket(sock,
                                        self.key_file,
                                        self.cert_file,
                                        cert_reqs=ssl.CERT_NONE)

        self.certificate = self.sock.getpeercert(True)
        if self.callBack:
            if not self.callBack(self.certificate):
                raise ssl.SSLError(1, "Call back verification failed")


class HellHTTPS(object):
    "This class is the library used by the weboob's CMB module"

    def __init__(self, host, port=None, proxy=None, proxy_port=None,
                 key_file=None, cert_file=None, ca_file=None, strict=None,
                 timeout=socket._GLOBAL_DEFAULT_TIMEOUT, callBack=None):
        self.proxy = proxy
        self.proxy_port = proxy_port
        if not self.proxy:
            import os
            if 'http_proxy' in os.environ:
                o = urlsplit(os.environ['http_proxy'])
                self.proxy = o.hostname
                if o.port:
                    self.proxy_port = o.port
                else:
                    self.proxy_port = PROXY_PORT
        self.host = host
        self.port = port
        if self.proxy:
            if self.proxy_port:
                pport = self.proxy_port
            else:
                pport = PROXY_PORT
            self.conn = HTTPSVerifiedConnection(proxy, pport, key_file,
                    cert_file, ca_file, strict, timeout, callBack)
        else:
            self.conn = HTTPSVerifiedConnection(host, port, key_file, cert_file,
                    ca_file, strict, timeout, callBack)

    def request(self, *args, **kwargs):
        self.conn.request(*args, **kwargs)

    def connect(self):
        # set the proxy
        # python 2.6 needs _set_tunnel, 2.7 needs set_tunnel
        if self.proxy:
            self.conn._set_tunnel(self.host, self.port)
        self.conn.connect()

    def getresponse(self, *args):
        return self.conn.getresponse(*args)

    def close(self):
        self.conn.close


# A script to find the hash that has to be used in the call back function
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 5 or len(sys.argv) < 1:
        print 'usage: python %s host [port [proxy [proxy_port]]]' % sys.argv[0]
        sys.exit(1)
    conn = HellHTTPS(*sys.argv[1:])

    conn.connect()
    conn.request('GET', '/')

    response = conn.getresponse()
    print response.status, response.reason

    pemcert = ssl.DER_cert_to_PEM_cert(conn.conn.certificate)
    certhash = hashlib.sha256(pemcert).hexdigest()

    print "Hash: %s" % certhash
    conn.close()
