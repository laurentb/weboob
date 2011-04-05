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
    STATUS_NONE     = 0
    STATUS_PROGRESS = 1
    STATUS_DONE     = 2

    def __init__(self, backend, capability):
        self.backend = backend
        self.capability = capability
        self.status = self.STATUS_NONE
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
        self.begin = None
        self.end = None
        self.location = None
        self.backend = backend
        self.members = OrderedDict()
        self.load()

    def get_me(self):
        return self.members.get(self.backend.browser.get_userid(), None)

    def currently_in_event(self):
        if not self.date or not self.begin or not self.end:
            return False

        return self.begin < datetime.now() < self.end

    def format_duration(self):
        if not self.begin or not self.end:
            return None

        delta = self.end - self.begin
        return '%02d:%02d' % (delta.seconds/3600, delta.seconds%3600)

    def load(self):
        self.content = self.backend.get_content(self.name)
        self.members.clear()
        member = None
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
                        self.date = self.parse_date(value)
                    elif key == 'Start' or key == 'Begin':
                        self.begin = self.parse_time(value)
                    elif key == 'End':
                        self.end = self.parse_time(value)
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
                task = Task(m.group(1), m.group(2))
                member.tasks.append(task)
                if m.group(3) == '!/img/weboob/_progress.png!':
                    task.status = task.STATUS_PROGRESS
                    continue

                mm = re.match('!/img/weboob/_done.png! (\d+):(\d+) (\w+)', m.group(3))
                if mm and self.date:
                    task.status = task.STATUS_DONE
                    task.date = datetime(self.date.year,
                                         self.date.month,
                                         self.date.day,
                                         int(m.group(1)),
                                         int(m.group(2)))
                    task.branch = m.group(3)

    def parse_date(self, value):
        try:
            return datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            return None

    def parse_time(self, value):
        m = re.match('(\d+):(\d+)', value)
        if not m:
            return

        try:
            return self.date.replace(hour=int(m.group(1)),
                                     minute=int(m.group(2)))
        except ValueError:
            return None

    def save(self, message):
        s = u"""h1. %s

{{TOC}}

h2. Event

%s

* *Date*: %s
* *Begin*: %s
* *End*: %s
* *Duration*: %s
* *Location*: %s

h2. Attendees

""" % (self.title,
       self.description,
       self.date.strftime('%Y-%m-%d') if self.date else '_Unknown_',
       self.begin.strftime('%H:%M') if self.begin else '_Unknown_',
       self.end.strftime('%H:%M') if self.end else '_Unknown_',
       self.format_duration() or '_Unknown_',
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

|_.Backend|_.Capabilities|_.Status|""" % (member.name,
                                        member.id,
                                        repository,
                                        member.hardware,
                                        availabilities)

            for task in member.tasks:
                if task.status == task.STATUS_DONE:
                    status = '!/img/weboob/_done.png! %s:%s %s' % (task.date.hour,
                                                                   task.date.minute,
                                                                   task.branch)
                elif task.status == task.STATUS_PROGRESS:
                    status = '!/img/weboob/_progress.png!'
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
        self.event.begin = self.ask('Begin at (HH:MM)',
                                   default=self.event.begin.strftime('%H:%M') if self.event.begin else '',
                                   regexp='^(\d{2}:\d{2})?$')
        if self.event.begin:
            self.event.begin = datetime.strptime(self.event.begin, '%H:%M')
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
                if task.status == task.STATUS_DONE:
                    s += '##'
                elif task.status == task.STATUS_PROGRESS:
                    s += '--'
                else:
                    s += '  '
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
                if task.status == task.STATUS_DONE:
                    status = '%s#%s' % (self.BOLD, self.NC)
                elif task.status == task.STATUS_PROGRESS:
                    status = '|'
                else:
                    status = ' '
                tasks[i*2].append('%s %s' % (status, task.backend))
                tasks[i*2+1].append('%s `-%s' % (status, task.capability[3:]))

        sys.stdout.write('    ')
        for name in members:
            sys.stdout.write(' %s%-20s%s' % (self.BOLD, name, self.NC))
        sys.stdout.write('\n    ')
        for name in members:
            sys.stdout.write(' %s%-20s%s' % (self.BOLD, '-' * len(name), self.NC))
        sys.stdout.write('\n')
        for i, line in enumerate(tasks):
            if not i%2:
                sys.stdout.write(' #%-2d' % (i/2))
            else:
                sys.stdout.write('    ')
            for task in line:
                sys.stdout.write(' %-20s' % task)
            sys.stdout.write('\n')

    def do_edit(self, line):
        self.event.load()
        self.edit_event()

    def do_info(self, line):
        self.event.load()
        print self.event.title
        print '-' * len(self.event.title)
        print self.event.description
        print ''
        print 'Date:', self.event.date
        print 'Begin:', self.event.begin
        print 'End:', self.event.end
        print 'Duration:', self.event.format_duration()
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
                if task.status == task.STATUS_DONE:
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

    def do_addtask(self, line):
        self.event.load()
        mem = self.event.get_me()
        if not mem:
            print 'You have not joined this event.'
            return

        backend, capability = self.parse_command_args(line, 2, 2)
        for task in mem.tasks:
            if (task.backend,task.capability) == (backend,capability):
                print 'A task already exists for that.'
                return

        task = Task(backend, capability)
        mem.tasks.append(task)
        self.save_event('New task')

    def do_start(self, line):
        self.event.load()
        mem = self.event.get_me()
        if not mem:
            print 'You have not joined this event.'
            return

        if len(mem.tasks) == 0:
            print "You don't have any task to do."
            return

        if not self.event.currently_in_event():
            print "You can't start a task, we are not in event."
            return

        if line.isdigit():
            task_id = int(line)
        else:
            task_id = -1

        last_done = -1
        for i, task in enumerate(mem.tasks):
            if task.status == task.STATUS_DONE:
                last_done = i
            elif task.status == task.STATUS_PROGRESS:
                task.status = task.STATUS_NONE

            if i == task_id or task.status == task.STATUS_NONE:
                break
        else:
            print 'Task not found.'

        if task.status == task.STATUS_DONE:
            print 'Task is already done.'
            return

        task.status = task.STATUS_PROGRESS
        mem.tasks.remove(task)
        mem.tasks.insert(last_done, task)
        self.save_event('Started a task')

    def do_done(self, line):
        self.event.load()
        mem = self.event.get_me()
        if not mem:
            print 'You have not joined this event.'
            return

        if len(mem.tasks) == 0:
            print "You don't have any task to do."
            return

        if not self.event.currently_in_event():
            print "You can't start a task, we are not in event."
            return

        for task in mem.tasks:
            if task.status == task.STATUS_PROGRESS:
                print 'Task: %s,%s' % (task.backend, task.capability)
                task.status = task.STATUS_DONE
                task.date = datetime.now()
                task.branch = self.ask('Enter name of branch')
                self.save_event('Task accomplished')
                return

        print "There isn't any task in progress."

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
