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

from functools import wraps
import os
import socket
import ssl as basessl
import subprocess
from tempfile import NamedTemporaryFile

try:
    import nss.ssl
    import nss.error
    import nss.nss
except ImportError:
    raise ImportError('Please install python-nss')
from requests.packages.urllib3.util.ssl_ import ssl_wrap_socket as old_ssl_wrap_socket
from weboob.tools.log import getLogger


__all__ = ['init_nss', 'inject_in_urllib3']


CTX = None
INIT_PID = None
INIT_ARGS = None
LOGGER = getLogger('weboob.browser.nss')


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


ERROR_MAP = {
    nss.error.PR_CONNECT_TIMEOUT_ERROR: (socket.timeout,),
    nss.error.PR_IO_TIMEOUT_ERROR: (socket.timeout,),
    nss.error.PR_CONNECT_RESET_ERROR: (socket.error,),
}


def wrap_callable(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except nss.error.NSPRError as e:
            if e.error_desc.startswith('(SEC_ERROR_') or e.error_desc.startswith('(SSL_ERROR_'):
                raise basessl.SSLError(0, e.error_message or e.error_desc, e)

            for k in ERROR_MAP:
                if k == e.error_code:
                    raise ERROR_MAP[k][0]

    return wrapper


class FileWrapper(object):
    def __init__(self, obj):
        self.__obj = obj

    def __getattr__(self, attr):
        ret = getattr(self.__obj, attr)
        if callable(ret):
            ret = wrap_callable(ret)
        return ret

    # for python3 only
    def readinto(self, b):
        data = self.read(len(b))
        b[:len(data)] = data
        return len(data)

    # for python3 only
    def flush(self):
        pass # nss always flushes data?


class Wrapper(object):
    def __init__(self, obj):
        self.__obj = obj

    def settimeout(self, t):
        # there is no nss option for that
        pass

    def __getattr__(self, attr):
        ret = getattr(self.__obj, attr)
        if callable(ret):
            ret = wrap_callable(ret)
        return ret

    def getpeercert(self, binary_form=False):
        # TODO return none or exception in case no cert yet?

        cert = self.__obj.get_peer_certificate()
        if binary_form:
            return cert.der_data
        else:
            return cert_to_dict(cert)

    def makefile(self, *args, **kwargs):
        return FileWrapper(self.__obj.makefile(*args, **kwargs))


def auth_cert_pinning(sock, check_sig, is_server, path):
    cert = sock.get_peer_certificate()

    expected = nss.nss.Certificate(nss.nss.read_der_from_file(path, True))
    return (expected.signed_data.data == cert.signed_data.data)


DEFAULT_CA_CERTIFICATES = (
    '/etc/ssl/certs/ca-certificates.crt',
    '/etc/pki/tls/certs/ca-bundle.crt',
)
def ssl_wrap_socket(sock, *args, **kwargs):
    if kwargs.get('certfile'):
        LOGGER.info('a client certificate is used, falling back to OpenSSL')
        # TODO implement NSS client certificate support
        return old_ssl_wrap_socket(sock, *args, **kwargs)

    reinit_if_needed()

    # TODO handle more options?
    hostname = kwargs.get('server_hostname')
    ossl_ctx = kwargs.get('ssl_context')

    # the python Socket and the NSS SSLSocket are agnostic of each other's state
    # so the Socket could close the fd, then a file could be opened,
    # obtaining the same file descriptor, then NSS would use the file, thinking
    # it's a network file descriptor... dup the fd to make it independant
    fileno = sock.fileno()
    if hasattr(sock, 'detach'):
        # socket.detach only exists in py3.
        sock.detach()
    else:
        fileno = os.dup(fileno)

    nsssock = nss.ssl.SSLSocket.import_tcp_socket(fileno)
    wrapper = Wrapper(nsssock)

    nsssock.set_certificate_db(nss.nss.get_default_certdb())
    if hostname:
        nsssock.set_hostname(hostname)
    if ossl_ctx and not ossl_ctx.verify_mode:
        nsssock.set_auth_certificate_callback(lambda *args: True)
    elif kwargs.get('ca_certs') and kwargs['ca_certs'] not in DEFAULT_CA_CERTIFICATES:
        nsssock.set_auth_certificate_callback(auth_cert_pinning, kwargs['ca_certs'])

    nsssock.reset_handshake(False) # marks handshake as not-done
    try:
        wrapper.send(b'') # performs handshake
    except:
        # If there is an exception during the handshake, correctly close the
        # duplicated/detached socket as it isn't known by the caller.
        wrapper.close()
        raise

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
    global CTX, INIT_PID, INIT_ARGS

    if CTX is not None and INIT_PID == os.getpid():
        return

    INIT_ARGS = (path, rw)

    if rw:
        flags = 0
    else:
        flags = nss.nss.NSS_INIT_READONLY

    INIT_PID = os.getpid()
    CTX = nss.nss.nss_init_context(path, flags=flags)

    nss.nss.enable_ocsp_checking()
    nss.nss.set_ocsp_failure_mode(nss.nss.ocspMode_FailureIsNotAVerificationFailure)


def add_nss_cert(path, filename):
    subprocess.check_call(['certutil', '-A', '-d', path, '-i', filename, '-n', filename, '-t', 'TC,C,T'])


def create_cert_db(path):
    try:
        subprocess.check_call(['certutil', '-N', '--empty-password', '-d', path])
    except OSError:
        raise ImportError('Please install libnss3-tools')

    cert_dir = '/etc/ssl/certs'
    for f in os.listdir(cert_dir):
        f = os.path.join(cert_dir, f)
        if os.path.isdir(f) or '.' not in f:
            continue

        with open(f) as fd:
            content = fd.read()

        separators = [
            '-----END CERTIFICATE-----',
            '-----END TRUSTED CERTIFICATE-----',
        ]
        for sep in separators:
            if sep in content:
                separator = sep
                break
        else:
            continue

        try:
            nb_certs = content.count(separator)
            if nb_certs == 1:
                add_nss_cert(path, f)
            elif nb_certs > 1:
                for cert in content.split(separator)[:-1]:
                    cert += separator
                    with NamedTemporaryFile() as fd:
                        fd.write(cert)
                        fd.flush()
                        add_nss_cert(path, fd.name)
        except subprocess.CalledProcessError:
            LOGGER.warning('Unable to handle ca file {}'.format(f))


def reinit_if_needed():
    # if we forked since NSS was initialized, we might get an exception
    # (SEC_ERROR_PKCS11_DEVICE_ERROR) A PKCS #11 module returned CKR_DEVICE_ERROR, indicating that a problem has occurred with the token or slot.
    # so we should reinit NSS

    if INIT_PID and INIT_PID != os.getpid():
        LOGGER.info('nss inited in %s but now in %s', INIT_PID, os.getpid())
        assert INIT_ARGS
        init_nss(*INIT_ARGS)
