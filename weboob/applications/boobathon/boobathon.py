# -*- coding: utf-8 -*-

# Copyright(C) 2011  Romain Bignon
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


from datetime import datetime
import re
import sys
from urlparse import urlsplit
from random import choice

from weboob.capabilities.content import ICapContent
from weboob.tools.application.repl import ReplApplication
from weboob.tools.ordereddict import OrderedDict


__all__ = ['Boobathon']


class Task(object):
    def __init__(self, id, backend, capability):
        self.id = id
        self.backend = backend
        self.capability = capability
        self.done = False
        self.date = None
        self.branch = u''

class Member(object):
    def __init__(self, id, name):
        self.name = name
        self.id = id
        self.tasks = []
        self.availabilities = u''
        self.repository = None
        self.hardware = u''
        self.is_me = False

class Event(object):
    def __init__(self, name, backend):
        self.my_id = backend.browser.get_userid()
        self.name = 'wiki/weboob/%s' % name
        self.description = None
        self.date = None
        self.start = None
        self.end = None
        self.duration = None
        self.location = None
        self.backend = backend
        self.members = OrderedDict()
        self.load()

    def get_me(self):
        return self.members.get(self.backend.browser.get_userid(), None)

    def load(self):
        self.content = self.backend.get_content(self.name)
        self.members.clear()
        member = None
        task_id = 0
        for line in self.content.content.split('\n'):
            line = line.strip()
            if line.startswith('h1. '):
                self.title = line[4:]
            elif line.startswith('h2. '):
                continue
            elif line.startswith('h3. '):
                m = re.match('h3. "(.*)":/users/(\d+)', line)
                if not m:
                    print 'Unable to parse user "%s"' % line
                    continue
                member = Member(int(m.group(2)), m.group(1))
                if member.id == self.my_id:
                    member.is_me = True
                self.members[member.id] = member
            elif self.description is None and len(line) > 0 and line != '{{TOC}}':
                self.description = line
            elif line.startswith('* '):
                m = re.match('\* \*(\w+)\*: (.*)', line)
                if not m:
                    print 'Unknown line "%s"' % line
                    continue
                key, value = m.group(1), m.group(2)
                if member is None:
                    if key == 'Date':
                        self.date = self.parse_datetime(value, '%Y-%m-%d')
                    elif key == 'Start':
                        self.start = self.parse_datetime(value, '%H:%M')
                    elif key == 'End':
                        self.end = self.parse_datetime(value, '%H:%M')
                    elif key == 'Duration':
                        self.duration = self.parse_datetime(value, '%H:%M')
                    elif key == 'Location':
                        self.location = value
                else:
                    if key == 'Repository':
                        m = re.match('"(.*.git)":.*', value)
                        if m:
                            member.repository = m.group(1)
                        else:
                            member.repository = value
                    elif key == 'Hardware':
                        member.hardware = value
                    elif key == 'Availabilities':
                        member.availabilities = value
            elif line.startswith('[['):
                m = re.match('\[\[(\w+)\]\]\|\[\[(\w+)\]\]\|(.*)\|', line)
                if not m:
                    print 'Unable to parse task: "%s"' % line
                    continue
                task_id += 1
                task = Task(task_id, m.group(1), m.group(2))
                member.tasks.append(task)
                mm = re.match('!/img/weboob/_done.png! (\d+):(\d+) (\w+)', m.group(3))
                if mm:
                    task.done = True
                    task.date = datetime(self.date.year,
                                         self.date.month,
                                         self.date.day,
                                         int(m.group(1)),
                                         int(m.group(2)))
                    task.branch = m.group(3)

    def parse_datetime(self, value, format):
        try:
            return datetime.strptime(value, format)
        except ValueError:
            return None

    def save(self, message):
        s = u"""h1. %s

{{TOC}}

h2. Event

%s

* *Date*: %s
* *Start*: %s
* *End*: %s
* *Duration*: %s
* *Location*: %s

h2. Attendees

""" % (self.title,
       self.description,
       self.date.strftime('%Y-%m-%d') if self.date else '_Unknown_',
       self.start.strftime('%H:%M') if self.start else '_Unknown_',
       self.end.strftime('%H:%M') if self.end else '_Unknown_',
       self.duration.strftime('%H:%M') if self.duration else '_Unknown_',
       self.location or '_Unknown_')

        for member in self.members.itervalues():
            if self.date:
                availabilities = ''
            else:
                availabilities = '* *Availabilities*: %s' % member.availabilities
            if member.repository is None:
                repository = '_Unknown_'
            elif member.repository.endswith('.git'):
                repository = '"%s":git://git.symlink.me/pub/%s ("http":http://git.symlink.me/?p=%s;a=summary)'
                repository = repository.replace('%s', member.repository)
            else:
                repository = member.repository

            s += u"""h3. "%s":/users/%d

* *Repository*: %s
* *Hardware*: %s
%s

|_.Backend|_.Capabilities|_.Done|""" % (member.name,
                                        member.id,
                                        repository,
                                        member.hardware,
                                        availabilities)

            for task in member.tasks:
                if task.done:
                    status = '!/img/weboob/_done.png! %s:%s %s' % (task.date.hour,
                                                                   task.date.minute,
                                                                   task.branch)
                else:
                    status = ' '
                s += u"""
|=.!/img/weboob/%s.png!
[[%s]]|[[%s]]|%s|""" % (task.backend.lower(), task.backend, task.capability, status)
            s += '\n\n'

        self.content.content = s
        self.backend.push_content(self.content, message)

class Boobathon(ReplApplication):
    APPNAME = 'boobathon'
    VERSION = '0.8'
    COPYRIGHT = 'Copyright(C) 2011 Romain Bignon'
    DESCRIPTION = 'Console application to participate to a Boobathon.'
    CAPS = ICapContent
    SYNOPSIS =  'Usage: %prog [-dqv] [-b backends] [-cnfs] boobathon\n'
    SYNOPSIS += '       %prog [--help] [--version]'

    radios = []

    def __init__(self, *args, **kwargs):
        ReplApplication.__init__(self, *args, **kwargs)

    def main(self, argv):
        if len(argv) < 2:
            print >>sys.stderr, 'Please give the name of the boobathon'
            return 1

        self.event = Event(argv[1], choice(self.weboob.backend_instances.values()))
        if self.event.description is None:
            if not self.ask("This event doesn't seem to exist. Do you want to create it?", default=True):
                return 1
            self.edit_event()

        return ReplApplication.main(self, [argv[0]])

    def save_event(self, message):
        if self.ask("Do you confirm your changes?", default=True):
            self.event.save(message)

    def edit_event(self):
        self.event.title = self.ask('Enter a title', default=self.event.title)
        self.event.description = self.ask('Enter a description', default=self.event.description)
        self.event.date = self.ask('Enter a date (yyyy-mm-dd)',
                                   default=self.event.date.strftime('%Y-%m-%d') if self.event.date else '',
                                   regexp='^(\d{4}-\d{2}-\d{2})?$')
        if self.event.date:
            self.event.date = datetime.strptime(self.event.date, '%Y-%m-%d')
        self.event.start = self.ask('Start at (HH:MM)',
                                   default=self.event.start.strftime('%H:%M') if self.event.start else '',
                                   regexp='^(\d{2}:\d{2})?$')
        if self.event.start:
            self.event.start = datetime.strptime(self.event.start, '%H:%M')
        self.event.end = self.ask('End at (HH:MM)',
                                   default=self.event.end.strftime('%H:%M') if self.event.end else '',
                                   regexp='^(\d{2}:\d{2})?$')
        if self.event.end:
            self.event.end = datetime.strptime(self.event.end, '%H:%M')
        self.event.location = self.ask('Enter a location', default=self.event.location)

        self.save_event('Event edited')

    def edit_member(self, member):
        if member.name is None:
            member.name = self.ask('Please enter your name')
        if self.event.date is None:
            member.availabilities = self.ask('Enter availabilities', default=member.availabilities)
        member.repository = self.ask('Enter your repository (ex. romain/weboob.git)', default=member.repository)
        member.hardware = self.ask('Enter your hardware', default=member.hardware)

    def do_progress(self, line):
        self.event.load()
        for member in self.event.members.itervalues():
            s = u' %s %20s %s|' % ('->' if member.is_me else '  ', member.name, self.BOLD)
            for task in member.tasks:
                if task.done:
                    s += '##'
                else:
                    s += '--'
            s += '|%s' % self.NC
            print s

    def do_tasks(self, line):
        self.event.load()
        tasks = []
        members = []
        for member in self.event.members.itervalues():
            members.append(member.name)
            for i, task in enumerate(member.tasks):
                while len(tasks) <= i*2+1:
                    tasks.append([])
                if task.done:
                    status = '%s#%s' % (self.BOLD, self.NC)
                else:
                    status = ' '
                tasks[i*2].append('%s %s' % (status, task.backend))
                tasks[i*2+1].append('%s `-%s' % (status, task.capability[3:]))

        for name in members:
            sys.stdout.write(' %s%-20s%s' % (self.BOLD, name, self.NC))
        sys.stdout.write('\n')
        for name in members:
            sys.stdout.write(' %s%-20s%s' % (self.BOLD, '-' * len(name), self.NC))
        sys.stdout.write('\n')
        for line in tasks:
            for task in line:
                sys.stdout.write(' %-20s' % task)
            sys.stdout.write('\n')

    def do_info(self, line):
        self.event.load()
        print self.event.title
        print '-' * len(self.event.title)
        print self.event.description
        print ''
        print 'Date:', self.event.date
        print 'Start:', self.event.start
        print 'End:', self.event.end
        print 'Duration:', self.event.duration
        print 'Location:', self.event.location
        print ''
        print 'There are %d members, use the "members" command to list them' % len(self.event.members)
        if self.event.get_me() is None:
            print 'To join this event, use the command "join".'

    def do_members(self, line):
        self.event.load()
        for member in self.event.members.itervalues():
            print member.name
            print '-' * len(member.name)
            print 'Repository:', member.repository
            print 'Availabilities:', member.availabilities
            print 'Hardware:', member.hardware
            accompl = 0
            for task in member.tasks:
                if task.done:
                    accompl += 1
            print '%d tasks (%d accomplished)' % (len(member.tasks), accompl)
            print ''

        print 'Use the "tasks" command to display all tasks'

    def do_join(self, line):
        self.event.load()
        if self.event.backend.browser.get_userid() in self.event.members:
            print 'You have already joined this event.'
            return

        m = Member(self.event.backend.browser.get_userid(), 'Unknown')
        self.edit_member(m)
        self.event.members[m.id] = m
        self.save_event('Joined the event')

    def do_leave(self, line):
        self.event.load()
        try:
            self.event.members.pop(self.event.backend.browser.get_userid())
        except KeyError:
            print 'You have not joined this event.'
        else:
            self.save_event('Left the event')

    def do_done(self, line):
        self.event.load()

    def load_default_backends(self):
        """
        Overload a BaseApplication method.
        """
        for instance_name, backend_name, params in self.weboob.backends_config.iter_backends():
            if backend_name != 'redmine':
                continue
            v = urlsplit(params['url'])
            if v.netloc == 'symlink.me':
                self.load_backends(names=[instance_name])
                return

        if not self.check_loaded_backends({'url': 'https://symlink.me'}):
            print 'Ok, so leave now, fag.'
            sys.exit(0)

    def is_backend_loadable(self, backend):
        """
        Overload a ConsoleApplication method.
        """
        return backend.name == 'redmine'
