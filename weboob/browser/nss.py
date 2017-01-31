# -*- coding: utf-8 -*-

# Copyright(C) 2016      Vincent A
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

"""Module to use NSS instead of OpenSSL in urllib3/requests."""

# create db:
#   mkdir pki
#   certutil -N -d pki

# import certificate:
#   find -L /etc/ssl/certs -name "*.pem" | while read f; do certutil -A -d pki -i $f -n $f -t TCu,Cu,Tu; done

from __future__ import absolute_import

import os
import subprocess

try:
    import nss.ssl
    import nss.error
    import nss.nss
except ImportError:
    raise ImportError('Please install python-nss')


__all__ = ['init_nss', 'inject_in_urllib3']


def cert_to_dict(cert):
    # see https://docs.python.org/2/library/ssl.html#ssl.SSLSocket.getpeercert
    # and https://github.com/kennethreitz/requests/blob/master/requests/packages/urllib3/contrib/pyopenssl.py

    mappings = {
        nss.nss.certDNSName: 'DNS',
        nss.nss.certIPAddress: 'IP Address',
        # TODO support more types
    }

    altnames = []
    try:
        ext = cert.get_extension(nss.nss.SEC_OID_X509_SUBJECT_ALT_NAME)
    except KeyError:
        pass
    else:
        for entry in nss.nss.x509_alt_name(ext.value, nss.nss.AsObject):
            key = mappings[entry.type_enum]
            altnames.append((key, entry.name))

    ret = {
        'subject': [
            [('commonName', cert.subject.common_name)],
            [('localityName', cert.subject.locality_name)],
            [('organizationName', cert.subject.org_name)],
            [('organizationalUnitName', cert.subject.org_unit_name)],
            [('emailAddress', cert.subject.email_address)],
        ],
        'subjectAltName': altnames,
        'issuer': [
            [('countryName', cert.issuer.country_name)],
            [('organizationName', cert.issuer.org_name)],
            [('organizationalUnitName', cert.issuer.org_unit_name)],
            [('commonName', cert.issuer.common_name)],
        ],
        # TODO serialNumber, notBefore, notAfter
        'version': cert.version,
    }

    return ret


class FileWrapper(object):
    def __init__(self, obj):
        self.__obj = obj

    def __getattr__(self, attr):
        ret = getattr(self.__obj, attr)
        if callable(ret):
            ret = wrap_callable(ret)
        return ret


class Wrapper(object):
    def __init__(self, obj):
        self.__obj = obj

    def settimeout(self, t):
        # there is no nss option for that
        pass

    def __getattr__(self, attr):
        return getattr(self.__obj, attr)

    def getpeercert(self, binary_form=False):
        # TODO return none or exception in case no cert yet?

        cert = self.__obj.get_peer_certificate()
        if binary_form:
            return cert.der_data
        else:
            return cert_to_dict(cert)

    def makefile(self, *args, **kwargs):
        return FileWrapper(self.__obj.makefile(*args, **kwargs))


def ssl_wrap_socket(sock, *args, **kwargs):
    # TODO handle more options?
    hostname = kwargs.get('server_hostname')
    ossl_ctx = kwargs.get('ssl_context')

    # the python Socket and the NSS SSLSocket are agnostic of each other's state
    # so the Socket could close the fd, then a file could be opened,
    # obtaining the same file descriptor, then NSS would use the file, thinking
    # it's a network file descriptor... dup the fd to make it independant
    fileno = os.dup(sock.fileno())

    nsssock = nss.ssl.SSLSocket.import_tcp_socket(fileno)
    wrapper = Wrapper(nsssock)

    nsssock.set_certificate_db(nss.nss.get_default_certdb())
    if hostname:
        nsssock.set_hostname(hostname)
    if ossl_ctx and not ossl_ctx.verify_mode:
        nsssock.set_auth_certificate_callback(lambda *args: True)

    nsssock.reset_handshake(False) # marks handshake as not-done
    wrapper.send('') # performs handshake

    return wrapper


def inject_in_urllib3():
    import urllib3.util.ssl_
    import urllib3.connection
    # on some distros, requests comes with its own urllib3 version
    import requests.packages.urllib3.util.ssl_
    import requests.packages.urllib3.connection

    for pkg in (urllib3, requests.packages.urllib3):
        pkg.util.ssl_.ssl_wrap_socket = ssl_wrap_socket
        pkg.util.ssl_wrap_socket = ssl_wrap_socket
        pkg.connection.ssl_wrap_socket = ssl_wrap_socket


def init_nss(path, rw=False):
    if nss.nss.nss_is_initialized():
        return

    if rw:
        nss.nss.nss_init_read_write(path)
    else:
        nss.nss.nss_init(path)

    nss.nss.enable_ocsp_checking()


def create_cert_db(path):
    subprocess.check_call(['certutil', '-N', '--empty-password', '-d', path])
    cert_dir = '/etc/ssl/certs'
    for f in os.listdir(cert_dir):
        f = os.path.join(cert_dir, f)
        if os.path.isdir(f):
            continue
        subprocess.check_call(['certutil', '-A', '-d', path, '-i', f, '-n', f, '-t', 'TCu,Cu,Tu'])
