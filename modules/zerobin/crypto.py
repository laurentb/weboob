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

from base64 import b64decode, b64encode
from collections import OrderedDict
import math
from os import urandom

from Cryptodome.Cipher import AES
from Cryptodome.Protocol.KDF import PBKDF2
from Cryptodome.Hash import SHA256
from Cryptodome.Hash import HMAC


def log2(n):
    return math.log(n) / math.log(2)


def encrypt(plaintext):
    iv = urandom(16)
    salt = urandom(8)
    iterations = 1000
    ks = 128
    ts = 64

    hash_func = lambda k, s: HMAC.new(k, s, SHA256).digest()
    password = b64encode(urandom(32))
    key = PBKDF2(password, salt=salt, count=iterations, prf=hash_func)

    smalliv = trunc_iv(iv, plaintext, 0)

    cipher = AES.new(key, mode=AES.MODE_CCM, nonce=smalliv, mac_len=ts // 8)
    ciphertext = b''.join(cipher.encrypt_and_digest(plaintext))

    # OrderedDict because 0bin is a piece of shit requiring "iv" as the first key
    return password.decode('ascii'), OrderedDict([
        ('iv', b64encode(iv).decode('ascii')),
        ('v', 1),
        ('iter', iterations),
        ('ks', ks),
        ('ts', ts),
        ('mode', 'ccm'),
        ('adata', ''),
        ('cipher', 'aes'),
        ('salt', b64encode(salt).decode('ascii')),
        ('ct', b64encode(ciphertext).decode('ascii')),
    ])


def trunc_iv(iv, t, tl):
    ol = len(t) - tl
    if ol <= 0:
        oll = 2
    else:
        oll = int(max(2, math.ceil(log2(ol) / 8.)))
    assert oll <= 4
    if oll < 15 - len(iv):
        ivl = len(iv)
    else:
        ivl = 15 - oll
    iv = iv[:ivl]
    return iv


def decrypt(secretkey, params):
    iv = b64decode(params['iv'])
    salt = b64decode(params['salt'])
    #~ keylen = params.get('ks', 128) // 8 # FIXME use somewhere?
    taglen = params.get('ts', 64) // 8
    iterations = params.get('iter', 1000)
    data = b64decode(params['ct'])
    ciphertext = data[:-taglen]
    tag = data[-taglen:]

    if params.get('adata'):
        raise NotImplementedError('authenticated data support is not implemented')

    iv = trunc_iv(iv, ciphertext, taglen)

    hash_func = lambda k, s: HMAC.new(k, s, SHA256).digest()
    key = PBKDF2(secretkey, salt=salt, count=iterations, prf=hash_func)

    mode_str = params.get('mode', 'ccm')
    mode = dict(ccm=AES.MODE_CCM)[mode_str]
    if mode_str == 'ccm':
        cipher = AES.new(key, mode=AES.MODE_CCM, nonce=iv, mac_len=taglen)
    else:
        cipher = AES.new(key, mode=mode, iv=iv)
    decrypted = cipher.decrypt_and_verify(ciphertext, tag)
    return decrypted
