# -*- coding: utf-8 -*-

# Copyright(C) 2010-2013 Christophe Benz, Romain Bignon, Laurent Bachelier
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

# Some parts are taken from youtube-dl, licensed under the UNLICENSE.


import codecs
import zlib
import re
import os
import string
import struct
import collections
import traceback
import io

from weboob.capabilities.base import UserError
from weboob.deprecated.browser import Page, BrokenPageError, BrowserIncorrectPassword
from weboob.tools.compat import urlparse, parse_qs, urlencode
from weboob.tools.json import json


class LoginPage(Page):
    def on_loaded(self):
        errors = []
        for errdiv in self.parser.select(self.document.getroot(), 'div.errormsg'):
            errors.append(errdiv.text.encode('utf-8').strip())

        if len(errors) > 0:
            raise BrowserIncorrectPassword(', '.join(errors))

    def login(self, username, password):
        self.browser.select_form(predicate=lambda form: form.attrs.get('id', '') == 'gaia_loginform')
        self.browser['Email'] = username.encode(self.browser.ENCODING)
        self.browser['Passwd'] = password.encode(self.browser.ENCODING)
        self.browser.submit()


class LoginRedirectPage(Page):
    pass


class ForbiddenVideo(UserError):
    pass


class BaseYoutubePage(Page):
    def is_logged(self):
        try:
            self.parser.select(self.document.getroot(), 'span#yt-masthead-account-picker', 1)
        except BrokenPageError:
            return False
        else:
            return True


class ForbiddenVideoPage(BaseYoutubePage):
    def on_loaded(self):
        element = self.parser.select(self.document.getroot(), '.yt-alert-content', 1)
        raise ForbiddenVideo(element.text.strip())


class VerifyAgePage(BaseYoutubePage):
    def on_loaded(self):
        if not self.is_logged():
            raise ForbiddenVideo('This video or group may contain content that is inappropriate for some users')

        self.browser.select_form(predicate=lambda form: form.attrs.get('id', '') == 'confirm-age-form')
        self.browser.submit()


class VerifyControversyPage(BaseYoutubePage):
    def on_loaded(self):
        self.browser.select_form(predicate=lambda form: 'verify_controversy' in form.attrs.get('action', ''))
        self.browser.submit()


def determine_ext(url, default_ext=u'unknown_video'):
    guess = url.partition(u'?')[0].rpartition(u'.')[2]
    if re.match(r'^[A-Za-z0-9]+$', guess):
        return guess
    else:
        return default_ext

def uppercase_escape(s):
    unicode_escape = codecs.getdecoder('unicode_escape')
    return re.sub(
        r'\\U[0-9a-fA-F]{8}',
        lambda m: unicode_escape(m.group(0))[0],
        s)


_NO_DEFAULT = object()


class VideoPage(BaseYoutubePage):
    _formats = {
        '5': {'ext': 'flv', 'width': 400, 'height': 240},
        '6': {'ext': 'flv', 'width': 450, 'height': 270},
        '13': {'ext': '3gp'},
        '17': {'ext': '3gp', 'width': 176, 'height': 144},
        '18': {'ext': 'mp4', 'width': 640, 'height': 360},
        '22': {'ext': 'mp4', 'width': 1280, 'height': 720},
        '34': {'ext': 'flv', 'width': 640, 'height': 360},
        '35': {'ext': 'flv', 'width': 854, 'height': 480},
        '36': {'ext': '3gp', 'width': 320, 'height': 240},
        '37': {'ext': 'mp4', 'width': 1920, 'height': 1080},
        '38': {'ext': 'mp4', 'width': 4096, 'height': 3072},
        '43': {'ext': 'webm', 'width': 640, 'height': 360},
        '44': {'ext': 'webm', 'width': 854, 'height': 480},
        '45': {'ext': 'webm', 'width': 1280, 'height': 720},
        '46': {'ext': 'webm', 'width': 1920, 'height': 1080},


        # 3d videos
        '82': {'ext': 'mp4', 'height': 360, 'resolution': '360p', 'format_note': '3D', 'preference': -20},
        '83': {'ext': 'mp4', 'height': 480, 'resolution': '480p', 'format_note': '3D', 'preference': -20},
        '84': {'ext': 'mp4', 'height': 720, 'resolution': '720p', 'format_note': '3D', 'preference': -20},
        '85': {'ext': 'mp4', 'height': 1080, 'resolution': '1080p', 'format_note': '3D', 'preference': -20},
        '100': {'ext': 'webm', 'height': 360, 'resolution': '360p', 'format_note': '3D', 'preference': -20},
        '101': {'ext': 'webm', 'height': 480, 'resolution': '480p', 'format_note': '3D', 'preference': -20},
        '102': {'ext': 'webm', 'height': 720, 'resolution': '720p', 'format_note': '3D', 'preference': -20},

        # Apple HTTP Live Streaming
        '92': {'ext': 'mp4', 'height': 240, 'resolution': '240p', 'format_note': 'HLS', 'preference': -10},
        '93': {'ext': 'mp4', 'height': 360, 'resolution': '360p', 'format_note': 'HLS', 'preference': -10},
        '94': {'ext': 'mp4', 'height': 480, 'resolution': '480p', 'format_note': 'HLS', 'preference': -10},
        '95': {'ext': 'mp4', 'height': 720, 'resolution': '720p', 'format_note': 'HLS', 'preference': -10},
        '96': {'ext': 'mp4', 'height': 1080, 'resolution': '1080p', 'format_note': 'HLS', 'preference': -10},
        '132': {'ext': 'mp4', 'height': 240, 'resolution': '240p', 'format_note': 'HLS', 'preference': -10},
        '151': {'ext': 'mp4', 'height': 72, 'resolution': '72p', 'format_note': 'HLS', 'preference': -10},

        # DASH mp4 video
        '133': {'ext': 'mp4', 'height': 240, 'resolution': '240p', 'format_note': 'DASH video', 'preference': -40},
        '134': {'ext': 'mp4', 'height': 360, 'resolution': '360p', 'format_note': 'DASH video', 'preference': -40},
        '135': {'ext': 'mp4', 'height': 480, 'resolution': '480p', 'format_note': 'DASH video', 'preference': -40},
        '136': {'ext': 'mp4', 'height': 720, 'resolution': '720p', 'format_note': 'DASH video', 'preference': -40},
        '137': {'ext': 'mp4', 'height': 1080, 'resolution': '1080p', 'format_note': 'DASH video', 'preference': -40},
        '138': {'ext': 'mp4', 'format_note': 'DASH video', 'acodec': 'none', 'preference': -40},  # Height can vary (https://github.com/rg3/youtube-dl/issues/4559)
        '160': {'ext': 'mp4', 'height': 192, 'resolution': '192p', 'format_note': 'DASH video', 'preference': -40},
        '264': {'ext': 'mp4', 'height': 1440, 'resolution': '1440p', 'format_note': 'DASH video', 'preference': -40},
        '298': {'ext': 'mp4', 'height': 720, 'format_note': 'DASH video', 'acodec': 'none', 'preference': -40, 'fps': 60, 'vcodec': 'h264'},
        '299': {'ext': 'mp4', 'height': 1080, 'format_note': 'DASH video', 'acodec': 'none', 'preference': -40, 'fps': 60, 'vcodec': 'h264'},
        '266': {'ext': 'mp4', 'height': 2160, 'format_note': 'DASH video', 'acodec': 'none', 'preference': -40, 'vcodec': 'h264'},

        # Dash mp4 audio
        '139': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'aac', 'vcodec': 'none', 'abr': 48, 'preference': -50, 'container': 'm4a_dash'},
        '140': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'aac', 'vcodec': 'none', 'abr': 128, 'preference': -50, 'container': 'm4a_dash'},
        '141': {'ext': 'm4a', 'format_note': 'DASH audio', 'acodec': 'aac', 'vcodec': 'none', 'abr': 256, 'preference': -50, 'container': 'm4a_dash'},

        # Dash webm
        '167': {'ext': 'webm', 'height': 360, 'width': 640, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'VP8', 'acodec': 'none', 'preference': -40},
        '168': {'ext': 'webm', 'height': 480, 'width': 854, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'VP8', 'acodec': 'none', 'preference': -40},
        '169': {'ext': 'webm', 'height': 720, 'width': 1280, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'VP8', 'acodec': 'none', 'preference': -40},
        '170': {'ext': 'webm', 'height': 1080, 'width': 1920, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'VP8', 'acodec': 'none', 'preference': -40},
        '218': {'ext': 'webm', 'height': 480, 'width': 854, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'VP8', 'acodec': 'none', 'preference': -40},
        '219': {'ext': 'webm', 'height': 480, 'width': 854, 'format_note': 'DASH video', 'container': 'webm', 'vcodec': 'VP8', 'acodec': 'none', 'preference': -40},
        '278': {'ext': 'webm', 'height': 144, 'format_note': 'DASH video', 'acodec': 'none', 'preference': -40, 'container': 'webm', 'vcodec': 'VP9'},
        '242': {'ext': 'webm', 'height': 240, 'resolution': '240p', 'format_note': 'DASH webm', 'preference': -40},
        '243': {'ext': 'webm', 'height': 360, 'resolution': '360p', 'format_note': 'DASH webm', 'preference': -40},
        '244': {'ext': 'webm', 'height': 480, 'resolution': '480p', 'format_note': 'DASH webm', 'preference': -40},
        '245': {'ext': 'webm', 'height': 480, 'resolution': '480p', 'format_note': 'DASH webm', 'preference': -40},
        '246': {'ext': 'webm', 'height': 480, 'resolution': '480p', 'format_note': 'DASH webm', 'preference': -40},
        '247': {'ext': 'webm', 'height': 720, 'resolution': '720p', 'format_note': 'DASH webm', 'preference': -40},
        '248': {'ext': 'webm', 'height': 1080, 'resolution': '1080p', 'format_note': 'DASH webm', 'preference': -40},
        '271': {'ext': 'webm', 'height': 1440, 'format_note': 'DASH video', 'acodec': 'none', 'preference': -40},
        '272': {'ext': 'webm', 'height': 2160, 'format_note': 'DASH video', 'acodec': 'none', 'preference': -40},
        '302': {'ext': 'webm', 'height': 720, 'format_note': 'DASH video', 'acodec': 'none', 'preference': -40, 'fps': 60, 'vcodec': 'VP9'},
        '303': {'ext': 'webm', 'height': 1080, 'format_note': 'DASH video', 'acodec': 'none', 'preference': -40, 'fps': 60, 'vcodec': 'VP9'},
        '308': {'ext': 'webm', 'height': 1440, 'format_note': 'DASH video', 'acodec': 'none', 'preference': -40, 'fps': 60, 'vcodec': 'VP9'},
        '313': {'ext': 'webm', 'height': 2160, 'format_note': 'DASH video', 'acodec': 'none', 'preference': -40, 'vcodec': 'VP9'},
        '315': {'ext': 'webm', 'height': 2160, 'format_note': 'DASH video', 'acodec': 'none', 'preference': -40, 'fps': 60, 'vcodec': 'VP9'},

        # Dash webm audio
        '171': {'ext': 'webm', 'vcodec': 'none', 'format_note': 'DASH audio', 'abr': 128, 'preference': -50},
        '172': {'ext': 'webm', 'vcodec': 'none', 'format_note': 'DASH webm audio', 'abr': 256, 'preference': -50},

        # Dash webm audio with opus inside
        '249': {'ext': 'webm', 'vcodec': 'none', 'format_note': 'DASH audio', 'acodec': 'opus', 'abr': 50, 'preference': -50},
        '250': {'ext': 'webm', 'vcodec': 'none', 'format_note': 'DASH audio', 'acodec': 'opus', 'abr': 70, 'preference': -50},
        '251': {'ext': 'webm', 'vcodec': 'none', 'format_note': 'DASH audio', 'acodec': 'opus', 'abr': 160, 'preference': -50},

        # RTMP (unnamed)
        '_rtmp': {'protocol': 'rtmp'},
    }

    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        self._player_cache = {}

    def _signature_cache_id(self, example_sig):
        """ Return a string representation of a signature """
        return '.'.join(unicode(len(part)) for part in example_sig.split('.'))

    def _extract_signature_function(self, video_id, player_url, example_sig):
        id_m = re.match(
            r'.*?-(?P<id>[a-zA-Z0-9_-]+)(?:/watch_as3|/html5player)?\.(?P<ext>[a-z]+)$',
            player_url)
        if not id_m:
            raise BrokenPageError('Cannot identify player %r' % player_url)
        player_type = id_m.group('ext')
        player_id = id_m.group('id')

        # Read from filesystem cache
        func_id = '%s_%s_%s' % (
            player_type, player_id, self._signature_cache_id(example_sig))

        assert os.path.basename(func_id) == func_id

        if player_type == 'js':
            code = self.browser.readurl(player_url)
            res = self._parse_sig_js(code)
        elif player_type == 'swf':
            urlh = self.browser.openurl(player_url)
            code = urlh.read()
            res = self._parse_sig_swf(code)
        else:
            assert False, 'Invalid player type %r' % player_type

        return res

    def _parse_sig_js(self, jscode):
        funcname = self._search_regex(
            r'\.sig\|\|([a-zA-Z0-9$]+)\(', jscode,
            u'Initial JS player signature function name')

        functions = {}
        objects = {}
        code = jscode

        def argidx(varname):
            return string.lowercase.index(varname)

        def interpret_statement(stmt, local_vars, allow_recursion=20):
            if allow_recursion < 0:
                raise BrokenPageError(u'Recursion limit reached')

            if stmt.startswith(u'var '):
                stmt = stmt[len(u'var '):]
            ass_m = re.match(r'^(?P<out>[a-z]+)(?:\[(?P<index>[^\]]+)\])?' +
                             r'=(?P<expr>.*)$', stmt)
            if ass_m:
                if ass_m.groupdict().get('index'):
                    def assign(val):
                        lvar = local_vars[ass_m.group('out')]
                        idx = interpret_expression(ass_m.group('index'),
                                                   local_vars, allow_recursion)
                        assert isinstance(idx, int)
                        lvar[idx] = val
                        return val
                    expr = ass_m.group('expr')
                else:
                    def assign(val):
                        local_vars[ass_m.group('out')] = val
                        return val
                    expr = ass_m.group('expr')
            elif stmt.startswith(u'return '):
                assign = lambda v: v
                expr = stmt[len(u'return '):]
            else:
                # Try interpreting it as an expression
                expr = stmt
                assign = lambda v: v

            v = interpret_expression(expr, local_vars, allow_recursion)
            return assign(v)

        def extract_object(objname):
            obj = {}
            obj_m = re.search(
                (r'(?:var\s+)?%s\s*=\s*\{' % re.escape(objname)) +
                r'\s*(?P<fields>([a-zA-Z$0-9]+\s*:\s*function\(.*?\)\s*\{.*?\})*)' +
                r'\}\s*;',
                code)
            fields = obj_m.group('fields')
            # Currently, it only supports function definitions
            fields_m = re.finditer(
                r'(?P<key>[a-zA-Z$0-9]+)\s*:\s*function'
                r'\((?P<args>[a-z,]+)\){(?P<code>[^}]+)}',
                fields)
            for f in fields_m:
                argnames = f.group('args').split(',')
                obj[f.group('key')] = build_function(argnames, f.group('code'))

            return obj

        def build_function(argnames, code):
            def resf(args):
                local_vars = dict(zip(argnames, args))
                for stmt in code.split(';'):
                    res = interpret_statement(stmt, local_vars)
                return res
            return resf

        def interpret_expression(expr, local_vars, allow_recursion):
            if expr.isdigit():
                return int(expr)

            if expr.isalpha():
                return local_vars[expr]

            try:
                return json.loads(expr)
            except ValueError:
                pass

            m = re.match(r'^(?P<var>[a-zA-Z0-9_]+)\.(?P<member>[^(]+)(?:\(+(?P<args>[^()]*)\))?$', expr)
            if m:
                variable = m.group('var')
                member = m.group('member')
                arg_str = m.group('args')

                if variable in local_vars:
                    obj = local_vars[variable]
                else:
                    if variable not in objects:
                        objects[variable] = extract_object(variable)
                    obj = objects[variable]

                if arg_str is None:
                    # Member access
                    if member == 'length':
                        return len(obj)
                    return obj[member]

                assert expr.endswith(')')
                # Function call
                if arg_str == '':
                    argvals = tuple()
                else:
                    argvals = tuple([
                        interpret_expression(v, local_vars, allow_recursion)
                        for v in arg_str.split(',')])

                if member == 'split':
                    assert argvals == ('',)
                    return list(obj)
                if member == 'join':
                    assert len(argvals) == 1
                    return argvals[0].join(obj)
                if member == 'reverse':
                    assert len(argvals) == 0
                    obj.reverse()
                    return obj
                if member == 'slice':
                    assert len(argvals) == 1
                    return obj[argvals[0]:]
                if member == 'splice':
                    assert isinstance(obj, list)
                    index, howMany = argvals
                    res = []
                    for i in range(index, min(index + howMany, len(obj))):
                        res.append(obj.pop(index))
                    return res

                return obj[member](argvals)

            m = re.match(
                r'^(?P<in>[a-z]+)\[(?P<idx>.+)\]$', expr)
            if m:
                val = local_vars[m.group('in')]
                idx = interpret_expression(
                    m.group('idx'), local_vars, allow_recursion - 1)
                return val[idx]

            m = re.match(r'^(?P<a>.+?)(?P<op>[%])(?P<b>.+?)$', expr)
            if m:
                a = interpret_expression(
                    m.group('a'), local_vars, allow_recursion)
                b = interpret_expression(
                    m.group('b'), local_vars, allow_recursion)
                return a % b

            m = re.match(
                r'^(?P<func>[a-zA-Z$]+)\((?P<args>[a-z0-9,]+)\)$', expr)
            if m:
                fname = m.group('func')
                argvals = tuple([
                    int(v) if v.isdigit() else local_vars[v]
                    for v in m.group('args').split(',')])
                if fname not in functions:
                    functions[fname] = extract_function(fname)
                return functions[fname](argvals)
            raise BrokenPageError(u'Unsupported JS expression %r' % expr)

        def extract_function(funcname):
            func_m = re.search(
                r'function ' + re.escape(funcname) +
                r'\((?P<args>[a-z,]+)\){(?P<code>[^}]+)}',
                jscode)
            argnames = func_m.group('args').split(',')

            def resf(args):
                local_vars = dict(zip(argnames, args))
                for stmt in func_m.group('code').split(';'):
                    res = interpret_statement(stmt, local_vars)
                return res
            return resf

        initial_function = extract_function(funcname)
        return lambda s: initial_function([s])

    def _parse_sig_swf(self, file_contents):
        if file_contents[1:3] != b'WS':
            raise BrokenPageError(
                u'Not an SWF file; header is %r' % file_contents[:3])
        if file_contents[:1] == b'C':
            content = zlib.decompress(file_contents[8:])
        else:
            raise NotImplementedError(u'Unsupported compression format %r' %
                                      file_contents[:1])

        def extract_tags(content):
            pos = 0
            while pos < len(content):
                header16 = struct.unpack('<H', content[pos:pos+2])[0]
                pos += 2
                tag_code = header16 >> 6
                tag_len = header16 & 0x3f
                if tag_len == 0x3f:
                    tag_len = struct.unpack('<I', content[pos:pos+4])[0]
                    pos += 4
                assert pos+tag_len <= len(content)
                yield (tag_code, content[pos:pos+tag_len])
                pos += tag_len

        code_tag = next(tag
                        for tag_code, tag in extract_tags(content)
                        if tag_code == 82)
        p = code_tag.index(b'\0', 4) + 1
        code_reader = io.BytesIO(code_tag[p:])

        # Parse ABC (AVM2 ByteCode)
        def read_int(reader=None):
            if reader is None:
                reader = code_reader
            res = 0
            shift = 0
            for _ in range(5):
                buf = reader.read(1)
                assert len(buf) == 1
                b = struct.unpack('<B', buf)[0]
                res = res | ((b & 0x7f) << shift)
                if b & 0x80 == 0:
                    break
                shift += 7
            return res

        def u30(reader=None):
            res = read_int(reader)
            assert res & 0xf0000000 == 0
            return res
        u32 = read_int

        def s32(reader=None):
            v = read_int(reader)
            if v & 0x80000000 != 0:
                v = - ((v ^ 0xffffffff) + 1)
            return v

        def read_string(reader=None):
            if reader is None:
                reader = code_reader
            slen = u30(reader)
            resb = reader.read(slen)
            assert len(resb) == slen
            return resb.decode('utf-8')

        def read_bytes(count, reader=None):
            if reader is None:
                reader = code_reader
            resb = reader.read(count)
            assert len(resb) == count
            return resb

        def read_byte(reader=None):
            resb = read_bytes(1, reader=reader)
            res = struct.unpack('<B', resb)[0]
            return res

        # minor_version + major_version
        read_bytes(2 + 2)

        # Constant pool
        int_count = u30()
        for _c in range(1, int_count):
            s32()
        uint_count = u30()
        for _c in range(1, uint_count):
            u32()
        double_count = u30()
        read_bytes((double_count-1) * 8)
        string_count = u30()
        constant_strings = [u'']
        for _c in range(1, string_count):
            s = read_string()
            constant_strings.append(s)
        namespace_count = u30()
        for _c in range(1, namespace_count):
            read_bytes(1)  # kind
            u30()  # name
        ns_set_count = u30()
        for _c in range(1, ns_set_count):
            count = u30()
            for _c2 in range(count):
                u30()
        multiname_count = u30()
        MULTINAME_SIZES = {
            0x07: 2,  # QName
            0x0d: 2,  # QNameA
            0x0f: 1,  # RTQName
            0x10: 1,  # RTQNameA
            0x11: 0,  # RTQNameL
            0x12: 0,  # RTQNameLA
            0x09: 2,  # Multiname
            0x0e: 2,  # MultinameA
            0x1b: 1,  # MultinameL
            0x1c: 1,  # MultinameLA
        }
        multinames = [u'']
        for _c in range(1, multiname_count):
            kind = u30()
            assert kind in MULTINAME_SIZES, u'Invalid multiname kind %r' % kind
            if kind == 0x07:
                u30()  # namespace_idx
                name_idx = u30()
                multinames.append(constant_strings[name_idx])
            else:
                multinames.append('[MULTINAME kind: %d]' % kind)
                for _c2 in range(MULTINAME_SIZES[kind]):
                    u30()

        # Methods
        method_count = u30()
        MethodInfo = collections.namedtuple(
            'MethodInfo',
            ['NEED_ARGUMENTS', 'NEED_REST'])
        method_infos = []
        for method_id in range(method_count):
            param_count = u30()
            u30()  # return type
            for _ in range(param_count):
                u30()  # param type
            u30()  # name index (always 0 for youtube)
            flags = read_byte()
            if flags & 0x08 != 0:
                # Options present
                option_count = u30()
                for c in range(option_count):
                    u30()  # val
                    read_bytes(1)  # kind
            if flags & 0x80 != 0:
                # Param names present
                for _ in range(param_count):
                    u30()  # param name
            mi = MethodInfo(flags & 0x01 != 0, flags & 0x04 != 0)
            method_infos.append(mi)

        # Metadata
        metadata_count = u30()
        for _c in range(metadata_count):
            u30()  # name
            item_count = u30()
            for _c2 in range(item_count):
                u30()  # key
                u30()  # value

        def parse_traits_info():
            trait_name_idx = u30()
            kind_full = read_byte()
            kind = kind_full & 0x0f
            attrs = kind_full >> 4
            methods = {}
            if kind in [0x00, 0x06]:  # Slot or Const
                u30()  # Slot id
                u30()  # type_name_idx
                vindex = u30()
                if vindex != 0:
                    read_byte()  # vkind
            elif kind in [0x01, 0x02, 0x03]:  # Method / Getter / Setter
                u30()  # disp_id
                method_idx = u30()
                methods[multinames[trait_name_idx]] = method_idx
            elif kind == 0x04:  # Class
                u30()  # slot_id
                u30()  # classi
            elif kind == 0x05:  # Function
                u30()  # slot_id
                function_idx = u30()
                methods[function_idx] = multinames[trait_name_idx]
            else:
                raise BrokenPageError(u'Unsupported trait kind %d' % kind)

            if attrs & 0x4 != 0:  # Metadata present
                metadata_count = u30()
                for _c3 in range(metadata_count):
                    u30()  # metadata index

            return methods

        # Classes
        TARGET_CLASSNAME = u'SignatureDecipher'
        searched_idx = multinames.index(TARGET_CLASSNAME)
        searched_class_id = None
        class_count = u30()
        for class_id in range(class_count):
            name_idx = u30()
            if name_idx == searched_idx:
                # We found the class we're looking for!
                searched_class_id = class_id
            u30()  # super_name idx
            flags = read_byte()
            if flags & 0x08 != 0:  # Protected namespace is present
                u30()  # protected_ns_idx
            intrf_count = u30()
            for _c2 in range(intrf_count):
                u30()
            u30()  # iinit
            trait_count = u30()
            for _c2 in range(trait_count):
                parse_traits_info()

        if searched_class_id is None:
            raise BrokenPageError(u'Target class %r not found' %
                                 TARGET_CLASSNAME)

        method_names = {}
        method_idxs = {}
        for class_id in range(class_count):
            u30()  # cinit
            trait_count = u30()
            for _c2 in range(trait_count):
                trait_methods = parse_traits_info()
                if class_id == searched_class_id:
                    method_names.update(trait_methods.items())
                    method_idxs.update(dict(
                        (idx, name)
                        for name, idx in trait_methods.items()))

        # Scripts
        script_count = u30()
        for _c in range(script_count):
            u30()  # init
            trait_count = u30()
            for _c2 in range(trait_count):
                parse_traits_info()

        # Method bodies
        method_body_count = u30()
        Method = collections.namedtuple('Method', ['code', 'local_count'])
        methods = {}
        for _c in range(method_body_count):
            method_idx = u30()
            u30()  # max_stack
            local_count = u30()
            u30()  # init_scope_depth
            u30()  # max_scope_depth
            code_length = u30()
            code = read_bytes(code_length)
            if method_idx in method_idxs:
                m = Method(code, local_count)
                methods[method_idxs[method_idx]] = m
            exception_count = u30()
            for _c2 in range(exception_count):
                u30()  # from
                u30()  # to
                u30()  # target
                u30()  # exc_type
                u30()  # var_name
            trait_count = u30()
            for _c2 in range(trait_count):
                parse_traits_info()

        assert p + code_reader.tell() == len(code_tag)
        assert len(methods) == len(method_idxs)

        method_pyfunctions = {}

        def extract_function(func_name):
            if func_name in method_pyfunctions:
                return method_pyfunctions[func_name]
            if func_name not in methods:
                raise BrokenPageError(u'Cannot find function %r' % func_name)
            m = methods[func_name]

            def resfunc(args):
                registers = ['(this)'] + list(args) + [None] * m.local_count
                stack = []
                coder = io.BytesIO(m.code)
                while True:
                    opcode = struct.unpack('!B', coder.read(1))[0]
                    if opcode == 36:  # pushbyte
                        v = struct.unpack('!B', coder.read(1))[0]
                        stack.append(v)
                    elif opcode == 44:  # pushstring
                        idx = u30(coder)
                        stack.append(constant_strings[idx])
                    elif opcode == 48:  # pushscope
                        # We don't implement the scope register, so we'll just
                        # ignore the popped value
                        stack.pop()
                    elif opcode == 70:  # callproperty
                        index = u30(coder)
                        mname = multinames[index]
                        arg_count = u30(coder)
                        args = list(reversed(
                            [stack.pop() for _ in range(arg_count)]))
                        obj = stack.pop()
                        if mname == u'split':
                            assert len(args) == 1
                            assert isinstance(args[0], unicode)
                            assert isinstance(obj, unicode)
                            if args[0] == u'':
                                res = list(obj)
                            else:
                                res = obj.split(args[0])
                            stack.append(res)
                        elif mname == u'slice':
                            assert len(args) == 1
                            assert isinstance(args[0], int)
                            assert isinstance(obj, list)
                            res = obj[args[0]:]
                            stack.append(res)
                        elif mname == u'join':
                            assert len(args) == 1
                            assert isinstance(args[0], unicode)
                            assert isinstance(obj, list)
                            res = args[0].join(obj)
                            stack.append(res)
                        elif mname in method_pyfunctions:
                            stack.append(method_pyfunctions[mname](args))
                        else:
                            raise NotImplementedError(
                                u'Unsupported property %r on %r'
                                % (mname, obj))
                    elif opcode == 72:  # returnvalue
                        res = stack.pop()
                        return res
                    elif opcode == 79:  # callpropvoid
                        index = u30(coder)
                        mname = multinames[index]
                        arg_count = u30(coder)
                        args = list(reversed(
                            [stack.pop() for _ in range(arg_count)]))
                        obj = stack.pop()
                        if mname == u'reverse':
                            assert isinstance(obj, list)
                            obj.reverse()
                        else:
                            raise NotImplementedError(
                                u'Unsupported (void) property %r on %r'
                                % (mname, obj))
                    elif opcode == 93:  # findpropstrict
                        index = u30(coder)
                        mname = multinames[index]
                        res = extract_function(mname)
                        stack.append(res)
                    elif opcode == 97:  # setproperty
                        index = u30(coder)
                        value = stack.pop()
                        idx = stack.pop()
                        obj = stack.pop()
                        assert isinstance(obj, list)
                        assert isinstance(idx, int)
                        obj[idx] = value
                    elif opcode == 98:  # getlocal
                        index = u30(coder)
                        stack.append(registers[index])
                    elif opcode == 99:  # setlocal
                        index = u30(coder)
                        value = stack.pop()
                        registers[index] = value
                    elif opcode == 102:  # getproperty
                        index = u30(coder)
                        pname = multinames[index]
                        if pname == u'length':
                            obj = stack.pop()
                            assert isinstance(obj, list)
                            stack.append(len(obj))
                        else:  # Assume attribute access
                            idx = stack.pop()
                            assert isinstance(idx, int)
                            obj = stack.pop()
                            assert isinstance(obj, list)
                            stack.append(obj[idx])
                    elif opcode == 128:  # coerce
                        u30(coder)
                    elif opcode == 133:  # coerce_s
                        assert isinstance(stack[-1], (type(None), unicode))
                    elif opcode == 164:  # modulo
                        value2 = stack.pop()
                        value1 = stack.pop()
                        res = value1 % value2
                        stack.append(res)
                    elif opcode == 208:  # getlocal_0
                        stack.append(registers[0])
                    elif opcode == 209:  # getlocal_1
                        stack.append(registers[1])
                    elif opcode == 210:  # getlocal_2
                        stack.append(registers[2])
                    elif opcode == 211:  # getlocal_3
                        stack.append(registers[3])
                    elif opcode == 214:  # setlocal_2
                        registers[2] = stack.pop()
                    elif opcode == 215:  # setlocal_3
                        registers[3] = stack.pop()
                    else:
                        raise NotImplementedError(
                            u'Unsupported opcode %d' % opcode)

            method_pyfunctions[func_name] = resfunc
            return resfunc

        initial_function = extract_function(u'decipher')
        return lambda s: initial_function([s])

    def _decrypt_signature(self, s, video_id, player_url, age_gate=False):
        """Turn the encrypted s field into a working signature"""

        if player_url is not None:
            if player_url.startswith(u'//'):
                player_url = u'https:' + player_url
            try:
                player_id = (player_url, len(s))
                if player_id not in self._player_cache:
                    func = self._extract_signature_function(
                        video_id, player_url, s
                    )
                    self._player_cache[player_id] = func
                func = self._player_cache[player_id]
                return func(s)
            except Exception:
                tb = traceback.format_exc()
                raise BrokenPageError(u'Automatic signature extraction failed: %s' % tb)

        return self._static_decrypt_signature(
            s, video_id, player_url, age_gate)

    def _static_decrypt_signature(self, s, video_id, player_url, age_gate):
        if age_gate:
            # The videos with age protection use another player, so the
            # algorithms can be different.
            if len(s) == 86:
                return s[2:63] + s[82] + s[64:82] + s[63]

        if len(s) == 93:
            return s[86:29:-1] + s[88] + s[28:5:-1]
        elif len(s) == 92:
            return s[25] + s[3:25] + s[0] + s[26:42] + s[79] + s[43:79] + s[91] + s[80:83]
        elif len(s) == 91:
            return s[84:27:-1] + s[86] + s[26:5:-1]
        elif len(s) == 90:
            return s[25] + s[3:25] + s[2] + s[26:40] + s[77] + s[41:77] + s[89] + s[78:81]
        elif len(s) == 89:
            return s[84:78:-1] + s[87] + s[77:60:-1] + s[0] + s[59:3:-1]
        elif len(s) == 88:
            return s[7:28] + s[87] + s[29:45] + s[55] + s[46:55] + s[2] + s[56:87] + s[28]
        elif len(s) == 87:
            return s[6:27] + s[4] + s[28:39] + s[27] + s[40:59] + s[2] + s[60:]
        elif len(s) == 86:
            return s[80:72:-1] + s[16] + s[71:39:-1] + s[72] + s[38:16:-1] + s[82] + s[15::-1]
        elif len(s) == 85:
            return s[3:11] + s[0] + s[12:55] + s[84] + s[56:84]
        elif len(s) == 84:
            return s[78:70:-1] + s[14] + s[69:37:-1] + s[70] + s[36:14:-1] + s[80] + s[:14][::-1]
        elif len(s) == 83:
            return s[80:63:-1] + s[0] + s[62:0:-1] + s[63]
        elif len(s) == 82:
            return s[80:37:-1] + s[7] + s[36:7:-1] + s[0] + s[6:0:-1] + s[37]
        elif len(s) == 81:
            return s[56] + s[79:56:-1] + s[41] + s[55:41:-1] + s[80] + s[40:34:-1] + s[0] + s[33:29:-1] + s[34] + s[28:9:-1] + s[29] + s[8:0:-1] + s[9]
        elif len(s) == 80:
            return s[1:19] + s[0] + s[20:68] + s[19] + s[69:80]
        elif len(s) == 79:
            return s[54] + s[77:54:-1] + s[39] + s[53:39:-1] + s[78] + s[38:34:-1] + s[0] + s[33:29:-1] + s[34] + s[28:9:-1] + s[29] + s[8:0:-1] + s[9]

        else:
            raise BrokenPageError(u'Unable to decrypt signature, key length %d not supported; retrying might work' % (len(s)))

    def _parse_dash_manifest(self, video_id, dash_manifest_url, player_url, age_gate):
        def decrypt_sig(mobj):
            s = mobj.group(1)
            dec_s = self._decrypt_signature(s, video_id, player_url, age_gate)
            return '/signature/%s' % dec_s

        def int_or_none(v, default=None):
            try:
                return int(v)
            except (ValueError,TypeError):
                return default

        dash_manifest_url = re.sub(r'/s/([\w\.]+)', decrypt_sig, dash_manifest_url)
        dash_doc = self.browser.get_document(self.browser.openurl(dash_manifest_url))

        formats = []
        for r in dash_doc.findall('.//{urn:mpeg:DASH:schema:MPD:2011}Representation'):
            url_el = r.find('{urn:mpeg:DASH:schema:MPD:2011}BaseURL')
            if url_el is None:
                continue
            format_id = r.attrib['id']
            video_url = url_el.text
            filesize = int_or_none(url_el.attrib.get('{http://youtube.com/yt/2012/10/10}contentLength'))
            f = {
                'format_id': format_id,
                'url': video_url,
                'width': int_or_none(r.attrib.get('width')),
                'height': int_or_none(r.attrib.get('height')),
                'tbr': int_or_none(r.attrib.get('bandwidth'), 1000),
                'asr': int_or_none(r.attrib.get('audioSamplingRate')),
                'filesize': filesize,
                'fps': int_or_none(r.attrib.get('frameRate')),
            }
            try:
                existing_format = next(
                    fo for fo in formats
                    if fo['format_id'] == format_id)
            except StopIteration:
                f.update(self._formats.get(format_id, {}).items())
                formats.append(f)
            else:
                existing_format.update(f)
        return formats


    def _extract_from_m3u8(self, manifest_url, video_id):
        url_map = {}

        def _get_urls(_manifest):
            lines = _manifest.split('\n')
            urls = filter(lambda l: l and not l.startswith('#'), lines)
            return urls
        manifest = self.browser.readurl(manifest_url)
        formats_urls = _get_urls(manifest)
        for format_url in formats_urls:
            itag = self._search_regex(r'itag/(\d+?)/', format_url, 'itag')
            url_map[itag] = format_url
        return url_map

    def get_video_url(self, video):
        video_id = video.id
        video_webpage = ' '.join([self.parser.tocleanstring(el) for el in self.document.xpath('//script')])

        # Attempt to extract SWF player URL
        mobj = re.search(r'swfConfig.*?"(https?:\\/\\/.*?watch.*?-.*?\.swf)"', video_webpage)
        if mobj is not None:
            player_url = re.sub(r'\\(.)', r'\1', mobj.group(1))
        else:
            player_url = None

        # Get video info
        if re.search(r'player-age-gate-content">', video_webpage) is not None:
            age_gate = True
            # We simulate the access to the video from www.youtube.com/v/{video_id}
            # this can be viewed without login into Youtube
            url = 'https://www.youtube.com/embed/%s' % video_id
            embed_webpage = self.browser.readurl(url)
            data = urlencode({
                'video_id': video_id,
                'eurl': 'https://youtube.googleapis.com/v/' + video_id,
                'sts': self._search_regex(
                    r'"sts"\s*:\s*(\d+)', embed_webpage, 'sts', default=''),
            })

            video_info_url = 'https://www.youtube.com/get_video_info?' + data
            video_info_webpage = self.browser.readurl(video_info_url)
            video_info = parse_qs(video_info_webpage)
        else:
            age_gate = False
            try:
                # Try looking directly into the video webpage
                mobj = re.search(r';ytplayer\.config\s*=\s*({.*?});', video_webpage)
                if not mobj:
                    raise ValueError('Could not find ytplayer.config')  # caught below
                json_code = uppercase_escape(mobj.group(1))
                ytplayer_config = json.loads(json_code)
                args = ytplayer_config['args']
                # Convert to the same format returned by compat_parse_qs
                video_info = dict((k, [v]) for k, v in args.items())
                if 'url_encoded_fmt_stream_map' not in args:
                    raise ValueError('No stream_map present')  # caught below
            except ValueError:
                # We fallback to the get_video_info pages (used by the embed page)
                for el_type in ['&el=embedded', '&el=detailpage', '&el=vevo', '']:
                    video_info_url = ('https://www.youtube.com/get_video_info?&video_id=%s%s&ps=default&eurl=&gl=US&hl=en'
                            % (video_id, el_type))
                    video_info_webpage = self.browser.readurl(video_info_url)
                    video_info = parse_qs(video_info_webpage)
                    if 'token' in video_info:
                        break
        if 'token' not in video_info:
            if 'reason' in video_info:
                raise UserError(video_info['reason'][0])
            else:
                raise BrokenPageError(u'"token" parameter not in video info for unknown reason')

        # Check for "rental" videos
        if 'ypc_video_rental_bar_text' in video_info and 'author' not in video_info:
            raise UserError(u'"rental" videos not supported')

        def _map_to_format_list(urlmap):
            formats = []
            for itag, video_real_url in urlmap.items():
                dct = {
                    'format_id': itag,
                    'url': video_real_url,
                    'player_url': player_url,
                }
                if itag in self._formats:
                    dct.update(self._formats[itag])
                formats.append(dct)
            return formats

        if 'conn' in video_info and video_info['conn'][0].startswith('rtmp'):
            formats = [{
                'format_id': '_rtmp',
                'protocol': 'rtmp',
                'url': video_info['conn'][0],
                'player_url': player_url,
            }]
        elif len(video_info.get('url_encoded_fmt_stream_map', [''])[0]) >= 1 or len(video_info.get('adaptive_fmts', [''])[0]) >= 1:
            encoded_url_map = video_info.get('url_encoded_fmt_stream_map', [''])[0] + ',' + video_info.get('adaptive_fmts', [''])[0]

            if 'rtmpe%3Dyes' in encoded_url_map:
                raise BrokenPageError('rtmpe downloads are not supported, see https://github.com/rg3/youtube-dl/issues/343 for more information.', expected=True)
            url_map = {}
            for url_data_str in encoded_url_map.split(','):
                url_data = parse_qs(url_data_str)
                if 'itag' not in url_data or 'url' not in url_data:
                    continue
                format_id = url_data['itag'][0]
                url = url_data['url'][0]

                if 'sig' in url_data:
                    url += '&signature=' + url_data['sig'][0]
                elif 's' in url_data:
                    encrypted_sig = url_data['s'][0]

                    jsplayer_url_json = self._search_regex(
                        r'"assets":.+?"js":\s*("[^"]+")',
                        embed_webpage if age_gate else video_webpage, 'JS player URL')
                    player_url = json.loads(jsplayer_url_json)
                    if player_url is None:
                        player_url_json = self._search_regex(
                            r'ytplayer\.config.*?"url"\s*:\s*("[^"]+")',
                            video_webpage, 'age gate player URL')
                        player_url = json.loads(player_url_json)

                    signature = self._decrypt_signature(
                        encrypted_sig, video_id, player_url, age_gate)
                    url += '&signature=' + signature
                if 'ratebypass' not in url:
                    url += '&ratebypass=yes'
                url_map[format_id] = url

            formats = _map_to_format_list(url_map)
        elif video_info.get('hlsvp'):
            manifest_url = video_info['hlsvp'][0]
            url_map = self._extract_from_m3u8(manifest_url, video_id)
            formats = _map_to_format_list(url_map)
        else:
            raise BrokenPageError(u'no conn, hlsvp or url_encoded_fmt_stream_map information found in video info')

        dash_mpd = video_info.get('dashmpd')
        if dash_mpd:
            dash_manifest_url = dash_mpd[0]
            try:
                dash_formats = self._parse_dash_manifest(
                    video_id, dash_manifest_url, player_url, age_gate)
            except (BrokenPageError, KeyError) as e:
                self.logger.info( 'Skipping DASH manifest: %r' % e)
            else:
                    # Hide the formats we found through non-DASH
                    dash_keys = set(df['format_id'] for df in dash_formats)
                    for f in formats:
                        if f['format_id'] in dash_keys:
                            f['format_id'] = 'nondash-%s' % f['format_id']
                            f['preference'] = f.get('preference', 0) - 10000
                    formats.extend(dash_formats)

        # Check for malformed aspect ratio
        stretched_m = re.search(
            r'<meta\s+property="og:video:tag".*?content="yt:stretch=(?P<w>[0-9]+):(?P<h>[0-9]+)">',
            video_webpage)
        if stretched_m:
            ratio = float(stretched_m.group('w')) / float(stretched_m.group('h'))
            for f in formats:
                if f.get('vcodec') != 'none':
                    f['stretched_ratio'] = ratio

        self._sort_formats(formats)

        best = formats[-1]
        return best['url'], best['ext']

    def _sort_formats(self, formats):
        if not formats:
            raise BrokenPageError(u'No video formats found')

        def _formats_key(f):
            # TODO remove the following workaround
            if not f.get('ext') and 'url' in f:
                f['ext'] = determine_ext(f['url'])

            preference = f.get('preference')
            if preference is None:
                proto = f.get('protocol')
                if proto is None:
                    proto = urlparse(f.get('url', '')).scheme

                preference = 0 if proto in ['http', 'https'] else -0.1
                if f.get('ext') in ['f4f', 'f4m']:  # Not yet supported
                    preference -= 0.5

            if f.get('vcodec') == 'none':  # audio only
                ORDER = [u'webm', u'opus', u'ogg', u'mp3', u'aac', u'm4a']
                ext_preference = 0
                try:
                    audio_ext_preference = ORDER.index(f['ext'])
                except ValueError:
                    audio_ext_preference = -1
            else:
                ORDER = [u'webm', u'flv', u'mp4']
                try:
                    ext_preference = ORDER.index(f['ext'])
                except ValueError:
                    ext_preference = -1
                audio_ext_preference = 0

            return (
                preference,
                f.get('quality') if f.get('quality') is not None else -1,
                f.get('height') if f.get('height') is not None else -1,
                f.get('width') if f.get('width') is not None else -1,
                ext_preference,
                f.get('tbr') if f.get('tbr') is not None else -1,
                f.get('vbr') if f.get('vbr') is not None else -1,
                f.get('abr') if f.get('abr') is not None else -1,
                audio_ext_preference,
                f.get('filesize') if f.get('filesize') is not None else -1,
                f.get('format_id'),
            )
        formats.sort(key=_formats_key)

    def _search_regex(self, pattern, text, name, default=_NO_DEFAULT, fatal=True, flags=0):
        """
        Perform a regex search on the given string, using a single or a list of
        patterns returning the first matching group.
        In case of failure return a default value or raise a WARNING or a
        RegexNotFoundError, depending on fatal, specifying the field name.
        """
        if isinstance(pattern, (str, unicode, type(re.compile('')))):
            mobj = re.search(pattern, text, flags)
        else:
            for p in pattern:
                mobj = re.search(p, text, flags)
                if mobj:
                    break

        if mobj:
            # return the first matching group
            return next(g for g in mobj.groups() if g is not None)
        elif default is not _NO_DEFAULT:
            return default
        elif fatal:
            raise BrokenPageError(u'Unable to extract %s' % name)
        else:
            self.logger.warning(u'unable to extract %s' % name)
            return None
