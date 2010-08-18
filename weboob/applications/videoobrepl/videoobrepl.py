# -*- coding: utf-8 -*-

# Copyright(C) 2010  John Obbele
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


import os
import sys
import errno
from cmd import Cmd
from subprocess import Popen, PIPE
from weboob.capabilities.video import ICapVideo
from weboob.tools.application.console import ConsoleApplication


__all__ = ['VideoobRepl']


# EVIL GLOBAL VARIABLES {{{
# shell escape strings
BOLD   = '[1m'
NC     = '[0m'    # no color

# A list of tuples: (player , play_from_stdin_cmd)
# FIXME: lookup preference in freedesktop MIME database
PLAYERS = [
    ('parole', 'parole fd://0'),
    ('totem', 'totem fd://0'),
    ('mplayer', 'mplayer -really-quiet -'),
    ('vlc', 'vlc -'),
    ('xine', 'xine stdin:/'),
]
# }}}

class DefaultOptions():
    """Dummy options object.

    Should be replaced by a proper one from optparse.
    """

    def __init__(self):
        self.lang = "fr"
        self.quality = "hd"
        self.verbose = True

class MyPlayer():
    """Black magic invoking a video player to this world.
    
    Presently, due to strong disturbances in the holidays of the ether
    world, the video player used is chosen from a static list of
    programs. See PLAYERS for more information.

    You MAY want to move it into a separate weboob.tools.applications
    module.
    """

    def __init__(self, options=DefaultOptions()):
        "@param options [object] requires the bool. attribute 'verbose'"
        self.options = options

        self.player = None
        for (binary,cmd_stdin) in PLAYERS:
            if self._find_in_path(os.environ['PATH'], binary):
                self.player = binary
                self.player_stdin = cmd_stdin
                break
        if not self.player:
            raise OSError(errno.ENOENT, "video player not found")

        if self.options.verbose:
            print "Video player is (%s,%s)" % (self.player,
                                               self.player_stdin)
                                               
        
    def play(self, video):
        """Play a video object, using programs from the PLAYERS list.
        
        This function dispatch calls to either _play_default or
        _play_rtmp for special rtmp streams using SWF verification.
        """
        if video.url.find('rtmp') == 0:
            self._play_rtmp(video)
        else:
            self._play_default(video)

    def _play_default(self, video):
        "Play video.url with the video player."
        cmd = self.player + " " + video.url
        args = cmd.split()

        print "invoking [%s]" % cmd
        os.spawnlp(os.P_NOWAIT, args[0], *args)

    def _play_rtmp(self, video):
        """"Download data with rtmpdump and pipe them to a video player.

        You need a working version of rtmpdump installed and the SWF
        object url in order to comply with SWF verification requests
        from the server. The last one is retrieved from the non-standard
        non-API compliant 'swf_player' attribute of the 'video' object.
        """

        if not self._find_in_path(os.environ['PATH'], 'rtmpdump'):
            raise OSError(errno.ENOENT, "\'rtmpdump\' binary not found")

        video_url = video.url
        try:
            player_url = video.swf_player
            rtmp = 'rtmpdump -r %s --swfVfy %s' % (video_url, player_url)

        except AttributeError:
            error("Your video object does not have a 'swf_player' "
                  "attribute. SWF verification will be disabled and "
                  "may prevent correct video playback.")

            rtmp = 'rtmpdump -r %s' % video_url

        if not self.options.verbose:
            rtmp += ' --quiet'

        print ':: Streaming from %s' % video_url
        print ':: to %s' % self.player_stdin
        p1 = Popen(rtmp.split(), stdout=PIPE)
        p2 = Popen(self.player_stdin.split(),
                   stdin=p1.stdout, stderr=PIPE)

    def _find_in_path(self,path, filename):
        for i in path.split(':'):
            if os.path.exists('/'.join([i, filename])):
                return True
        return False

def error(str):
    "Shortcut to print >>sys.stderr"
    print >> sys.stderr, "Error:", str

def print_keys_values(tuplets, indent=0, highlight=False):
    """Pretty print a list of (key, values) tuplets."""
    first_column_width = max(len(k) for (k,v) in tuplets)
    for (key,value) in tuplets:
        # calm down typography nitpickers
        key = key + ":"
        # assert first column width
        key = key + " " * (first_column_width - len(key) + 1)
        # add uniform indentation if needed
        key = " " * indent + key
        # call 911
        if highlight:
            key = BOLD + key + NC
        print key, value

class MyCmd(Cmd):
    """Read-Eval-Print-Loop object build from the 'cmd' framework.

    It's just a command dispatcher, so get done with it.
    """

    def __init__(self, consoleApplication, player):
        """
        @param consoleApplication an instance of ConsoleApplication
        @param player an instance of MyPlayer()
        """
        Cmd.__init__(self)
        self.prompt = BOLD + 'weboob> ' + NC
        self.intro = 'Type "help" to see available commands.'

        self.player = player

        # engine / console application initialisation
        # (loading ALL backends by default)
        self.engine = consoleApplication
        self.enabled_backends = []
        self.available_backends = []
        self.engine.load_backends(ICapVideo)
        for b in self.engine.weboob.iter_backends(caps=ICapVideo):
            self.enabled_backends.append(b)
            self.available_backends.append(b)

        self.videos = [] # videos list cache

    def do_quit(self, arg):
        """quit the command line interpreter"""
        print "Byebye !"
        return True

    def do_exit(self, arg):
        """quit the command line interpreter"""
        return self.do_quit(arg)

    def do_EOF(self, arg):
        """quit the command line interpreter when ^D is pressed"""
        print ""
        return self.do_quit(arg)

    # By default, an emptyline repeats the previous command.
    # Overriding this function disables the behaviour.
    def emptyline(self):
        pass

    # Called when command prefix is not recognized
    def default(self, line):
        error('don\'t know how to %s' % line)

    # uncomment the leading '_' to use it as a debug function
    def _completedefault(self, text, line, begidx, endidx):
        error('don\'t know how to complete '
              '(text, line, begidx, endidx) =\n'
              '(%s,%s,%d,%d)' %
              (text, line, begidx, endidx))

    def _completion_helper(self, text, choices):
        """Complete TEST with string from CHOICES."""
        if text:
            return [x for x in choices if x.startswith(text)]
        else:
            return choices

    # The global help option can be ignored as long as you are to lazy
    # to implement it yourself.
    #def do_help(self, arg): pass

    ### dedicated commands
    ### fun starts here
    ###

    # TODO: do_status
    # TODO: toggle_nsfw
    # TODO: retrieve video from page_url

    def do_backends(self, line):
        """backends ACTION [backend0 backend1] …

        ACTION is one of the following:
            - add:         enable backends
            - rm | remove: disable backends
            - only:        enable only the following backends
            - view:        list enabled and available backends
        if no arguments are given, default to 'view'
        """
        if not line:
            args = ["view"] # default behaviour
        else:
            args = line.split()

        if args[0] in ["add", "only", "rm", "remove"]:

            if args[0] == "add":
                action = self.enabled_backends.append
            elif args[0] == "only":
                self.enabled_backends = [] # reset
                action = self.enabled_backends.append
            elif args[0] == "remove" or args[0] == "rm":
                action = self.enabled_backends.remove
            else:
                return False

            for b in self.available_backends:
                if b.name in args[1:]:
                    action(b)

            self.enabled_backends.sort()

            # FIXME: do we really need it ?
            # reload engine
            self.engine.deinit()
            names = tuple(x.name for x in self.enabled_backends)
            self.engine.load_backends(ICapVideo, names=names)

        else: # else "view"
            availables = " ".join(
                x.name for x in self.available_backends)
            enabled = " ".join(
                x.name for x in self.enabled_backends)
            print_keys_values([("Available backends", str(availables)),
                              ("Enabled backends  ", str(enabled))],
                              highlight=True)

    def do_search(self, pattern):
        """search [PATTERN]
        
        Search for videos.
        If no patterns are given, display the last entries.
        """

        if pattern:
            format = u'Search pattern: %s' % pattern
        else:
            format = u'Latest videos'

        # create generator, retrieve videos and add them to self.videos
        videos_g = self.engine.do('iter_search_results',
                                  pattern=pattern, nsfw=True,
                                  max_results=10)
        self.videos = [] # reset
        for i, (backend, video) in enumerate(videos_g):
            self.videos.append((backend,video))

        
        # code factorisatorminator: display the list of videos
        self.do_ls("")

    def complete_backends(self, text, line, begidx, endidx):
        choices = None

        if line.count(' ') == 1:
            choices = ["add", "remove", "view", "only"]
        else:
            choices = [x.name for x in self.available_backends]

        if choices:
            return self._completion_helper(text, choices)


    def do_ls(self, line):
        """ls

        Re-display the last list of videos.
        """
        for i, (backend, video) in enumerate(self.videos):
            print "%s(%d) %s %s(%s)" % (BOLD, i, video.title, NC,
                                        backend.name)
            print_keys_values([
                ("url", video.url),
                ("duration", "%s seconds" % video.duration),
                ("rating", "%.2f/%.2f" % (video.rating,
                                          video.rating_max))],
                indent=4)


    def do_play(self, line):
        """play NUMBER

        Play a previously listed video.
        """
        try:
            id = int(line)
        except ValueError:
            error("invalid number")
            return False

        try:
            (backend, video) = self.videos[id]
            id = video.id
        except IndexError:
            error("unknown video number")
            return False

        # FIXME: do we really have to unload/reload backends ?
        self.engine.deinit()
        names = (backend.name,) if backend is not None else None
        self.engine.load_backends(ICapVideo, names=names)

        # XXX: copy&paste from weboob-cli,
        # don't ask me anything about it :(
        for backend, video in self.engine.do('get_video', id):
            if video is None:
                continue
            self.player.play(video)


class VideoobRepl(ConsoleApplication):
    APPNAME = 'videoob-repl'
    VERSION = '0.1'
    COPYRIGHT = 'Copyright(C) 2010 John Obbele'

    def add_application_options(self, group):
        group.add_option('-C', '--configured',
                         action='store_true',
                         help='load configured backends')

    def main(self, argv):
        player = MyPlayer(DefaultOptions())
        console = self
        MyCmd(console, player).cmdloop()
