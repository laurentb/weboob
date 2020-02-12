# -*- coding: utf-8 -*-

# Copyright(C) 2011  Romain Bignon
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

from datetime import datetime, timedelta
import re
import sys
from random import choice
from collections import OrderedDict

from weboob.capabilities.content import CapContent
from weboob.tools.application.repl import ReplApplication
from weboob.tools.compat import urlsplit


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

    def __repr__(self):
        return '<Task (%s,%s)>' % (self.backend, self.capability)


class Member(object):
    def __init__(self, id, name):
        self.name = name
        self.id = id
        self.tasks = []
        self.availabilities = u''
        self.repository = None
        self.hardware = u''
        self.is_me = False

    def shortname(self):
        name = self.name
        if len(name) > 20:
            name = '%s..' % name[:18]
        return name


class Event(object):
    def __init__(self, name, backend):
        self.my_id = backend.browser.get_userid()
        self.name = 'wiki/weboob/%s' % name
        self.description = None
        self.date = None
        self.begin = None
        self.end = None
        self.location = None
        self.winner = None
        self.backend = backend
        self.members = OrderedDict()
        self.load()

    def get_me(self):
        return self.members.get(self.backend.browser.get_userid(), None)

    def currently_in_event(self):
        if not self.date or not self.begin or not self.end:
            return False

        return self.begin < datetime.now() < self.end

    def is_closed(self):
        return self.end < datetime.now()

    def format_duration(self):
        if not self.begin or not self.end:
            return None

        delta = self.end - self.begin
        return '%02d:%02d' % (delta.seconds/3600, delta.seconds%3600)

    def check_time_coherence(self):
        """
        Check if the end's day is before the begin's one, in
        case it stops at the next day (eg. 15h->1h).

        If it occures, add a day.
        """
        if self.begin > self.end:
            self.end = self.end + timedelta(1)

    def load(self):
        self.content = self.backend.get_content(self.name)
        self.members.clear()
        member = None
        for line in self.content.content.split('\n'):
            line = line.strip()
            if line.startswith('h1. '):
                self.title = line[4:]
            elif line.startswith('h3=. '):
                m = re.match('h3=. Event finished. Winner is "(.*)":/users/(\d+)\!', line)
                if not m:
                    print('Unable to parse h3=: %s' % line, file=self.stderr)
                    continue
                self.winner = Member(int(m.group(2)), m.group(1))
            elif line.startswith('h2. '):
                continue
            elif line.startswith('h3. '):
                m = re.match('h3. "(.*)":/users/(\d+)', line)
                if not m:
                    print('Unable to parse user "%s"' % line, file=self.stderr)
                    continue
                member = Member(int(m.group(2)), m.group(1))
                if member.id == self.my_id:
                    member.is_me = True
                if self.winner is not None and member.id == self.winner.id:
                    self.winner = member
                self.members[member.id] = member
            elif self.description is None and len(line) > 0 and line != '{{TOC}}':
                self.description = line
            elif line.startswith('* '):
                m = re.match('\* \*(\w+)\*: (.*)', line)
                if not m:
                    continue
                key, value = m.group(1), m.group(2)
                if member is None:
                    if key == 'Date':
                        self.date = self.parse_date(value)
                    elif key == 'Start' or key == 'Begin':
                        self.begin = self.parse_time(value)
                    elif key == 'End':
                        self.end = self.parse_time(value)
                        self.check_time_coherence()
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
                    print('Unable to parse task: "%s"' % line, file=self.stderr)
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
                                         int(mm.group(1)),
                                         int(mm.group(2)))
                    task.branch = mm.group(3)

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
        if self.winner:
            finished = u'\nh3=. Event finished. Winner is "%s":/users/%d!\n' % (self.winner.name,
                                                                                self.winner.id)
        else:
            finished = u''
        s = u"""h1. %s

{{TOC}}
%s
h2. Event

%s

* *Date*: %s
* *Begin*: %s
* *End*: %s
* *Duration*: %s
* *Location*: %s

h2. Attendees

""" % (self.title,
       finished,
       self.description,
       self.date.strftime('%Y-%m-%d') if self.date else '_Unknown_',
       self.begin.strftime('%H:%M') if self.begin else '_Unknown_',
       self.end.strftime('%H:%M') if self.end else '_Unknown_',
       self.format_duration() or '_Unknown_',
       self.location or '_Unknown_')

        for member in self.members.values():
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
                    status = '!/img/weboob/_done.png! %02d:%02d %s' % (task.date.hour,
                                                                       task.date.minute,
                                                                       task.branch)
                elif task.status == task.STATUS_PROGRESS:
                    status = '!/img/weboob/_progress.png!'
                else:
                    status = ' '
                s += u"""
|=.!/img/weboob/%s.png!:/projects/weboob/wiki/%s
[[%s]]|[[%s]]|%s|""" % (task.backend.lower(), task.backend, task.backend, task.capability, status)
            s += '\n\n'

        self.content.content = s
        self.backend.push_content(self.content, message)


class Boobathon(ReplApplication):
    APPNAME = 'boobathon'
    VERSION = '2.0'
    COPYRIGHT = 'Copyright(C) 2011-YEAR Romain Bignon'
    DESCRIPTION = 'Console application to participate to a Boobathon.'
    SHORT_DESCRIPTION = "participate in a Boobathon"
    CAPS = CapContent
    SYNOPSIS =  'Usage: %prog [-dqv] [-b backends] [-cnfs] boobathon\n'
    SYNOPSIS += '       %prog [--help] [--version]'

    radios = []

    def __init__(self, *args, **kwargs):
        super(Boobathon, self).__init__(*args, **kwargs)

    def main(self, argv):
        if len(argv) < 2:
            print('Please give the name of the boobathon', file=self.stderr)
            return 1

        self.event = Event(argv[1], choice(list(self.weboob.backend_instances.values())))
        if self.event.description is None:
            if not self.ask("This event doesn't seem to exist. Do you want to create it?", default=True):
                return 1
            self.edit_event()
            self.save_event('Event created')

        return ReplApplication.main(self, [argv[0]])

    def save_event(self, message):
        if self.ask("Do you confirm your changes?", default=True):
            self.event.save(message)
            return True
        return False

    def edit_event(self):
        self.event.title = self.ask('Enter a title', default=self.event.title)
        self.event.description = self.ask('Enter a description', default=self.event.description)
        self.event.date = self.ask('Enter a date (yyyy-mm-dd)',
                                   default=self.event.date.strftime('%Y-%m-%d') if self.event.date else '',
                                   regexp='^(\d{4}-\d{2}-\d{2})?$')
        if self.event.date:
            self.event.date = datetime.strptime(self.event.date, '%Y-%m-%d')

        s = self.ask('Begin at (HH:MM)',
                     default=self.event.begin.strftime('%H:%M') if self.event.begin else '',
                     regexp='^(\d{2}:\d{2})?$')
        if s:
            h, m = s.split(':')
            self.event.begin = self.event.date.replace(hour=int(h), minute=int(m))
        s = self.ask('End at (HH:MM)',
                     default=self.event.end.strftime('%H:%M') if self.event.end else '',
                     regexp='^(\d{2}:\d{2})?$')
        if s:
            h, m = s.split(':')
            self.event.end = self.event.date.replace(hour=int(h), minute=int(m))
            self.event.check_time_coherence()

        self.event.location = self.ask('Enter a location', default=self.event.location)

    def edit_member(self, member):
        if member.name is None:
            firstname = self.ask('Enter your firstname')
            lastname = self.ask('Enter your lastname')
            member.name = '%s %s' % (firstname, lastname)
        else:
            member.name = self.ask('Enter your name', default=member.name)
        if self.event.date is None:
            member.availabilities = self.ask('Enter availabilities', default=member.availabilities)
        member.repository = self.ask('Enter your repository (ex. romain/weboob.git)', default=member.repository)
        member.hardware = self.ask('Enter your hardware', default=member.hardware)

    def do_progress(self, line):
        """
        progress

        Display progress of members.
        """
        self.event.load()
        for member in self.event.members.values():
            if member.is_me and member is self.event.winner:
                status = '\o/ ->'
            elif member.is_me:
                status = '    ->'
            elif member is self.event.winner:
                status = '   \o/'
            else:
                status = '      '
            s = u' %s%20s %s|' % (status, member.shortname(), self.BOLD)
            for task in member.tasks:
                if task.status == task.STATUS_DONE:
                    s += '##'
                elif task.status == task.STATUS_PROGRESS:
                    s += u'=>'
                else:
                    s += '  '
            s += '|%s' % self.NC
            print(s)

        print('')
        now = datetime.now()
        if self.event.begin > now:
            d = self.event.begin - now
            msg = 'The event will start in %d days, %02d:%02d:%02d'
        elif self.event.end < now:
            d = now - self.event.end
            msg = 'The event is finished since %d days, %02d:%02d:%02d'
        else:
            tot = (self.event.end - self.event.begin).seconds
            cur = (datetime.now() - self.event.begin).seconds
            pct = cur*20/tot
            progress = ''
            for i in range(20):
                if i < pct:
                    progress += '='
                elif i == pct:
                    progress += '>'
                else:
                    progress += ' '
            print('Event started: %s |%s| %s' % (self.event.begin.strftime('%H:%M'),
                                                 progress,
                                                 self.event.end.strftime('%H:%M')))
            d = self.event.end - now
            msg = 'The event will be finished in %d days, %02d:%02d:%02d'

        print(msg % (d.days, d.seconds/3600, d.seconds%3600/60, d.seconds%60))

    def do_tasks(self, line):
        """
        tasks

        Display all tasks of members.
        """
        self.event.load()

        stop = False
        i = -2
        while not stop:
            if i >= 0 and not i%2:
                self.stdout.write(' #%-2d' % (i/2))
            else:
                self.stdout.write('    ')
            if i >= 0 and i%2:
                # second line of task, see if we'll stop
                stop = True
            for mem in self.event.members.values():
                if len(mem.tasks) > (i/2+1):
                    # there are more tasks, don't stop now
                    stop = False
                if i == -2:
                    self.stdout.write(' %s%-20s%s' % (self.BOLD, mem.shortname().encode('utf-8'), self.NC))
                elif i == -1:
                    self.stdout.write(' %s%-20s%s' % (self.BOLD, '-' * len(mem.shortname()), self.NC))
                elif len(mem.tasks) <= (i/2):
                    self.stdout.write(' ' * (20+1))
                else:
                    task = mem.tasks[i/2]
                    if task.status == task.STATUS_DONE:
                        status = u'#'
                    elif task.status == task.STATUS_PROGRESS:
                        if not i%2:
                            status = u'|' #1st line
                        else:
                            status = u'v' #2nd line
                    else:
                        status = u' '

                    if not i%2: #1st line
                        line = u'%s %s' % (status, task.backend)
                    else: #2nd line
                        line = u'%s `-%s' % (status, task.capability[3:])
                    self.stdout.write((u' %-20s' % line).encode('utf-8'))
            self.stdout.write('\n')
            i += 1

    def complete_close(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            self.event.load()
            return [member.name for member in self.event.members.values()]

    def do_close(self, name):
        """
        close WINNER

        Close the event and set the winner.
        """
        self.event.load()

        for member in self.event.members.values():
            if member.name == name:
                self.event.winner = member
                if self.save_event('Close event'):
                    print('Event is now closed. Winner is %s!' % self.event.winner.name)
                return

        print('"%s" not found' % name, file=self.stderr)
        return 3

    def complete_edit(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return ['event', 'me']

    def do_edit(self, line):
        """
        edit [event | me]

        Edit information about you or about event.
        """
        if not line:
            print('Syntax: edit [event | me]', file=self.stderr)
            return 2

        self.event.load()
        if line == 'event':
            self.edit_event()
            self.save_event('Event edited')
        elif line == 'me':
            mem = self.event.get_me()
            if not mem:
                print('You haven\'t joined the event.', file=self.stderr)
                return 1
            self.edit_member(mem)
            self.save_event('Member edited')
        else:
            print('Unable to edit "%s"' % line, file=self.stderr)
            return 1

    def do_info(self, line):
        """
        info

        Display information about this event.
        """
        self.event.load()
        print(self.event.title)
        print('-' * len(self.event.title))
        print(self.event.description)
        print('')
        print('Date:', self.event.date.strftime('%Y-%m-%d') if self.event.date else 'Unknown')
        print('Begin:', self.event.begin.strftime('%H:%M') if self.event.begin else 'Unknown')
        print('End:', self.event.end.strftime('%H:%M') if self.event.end else 'Unknown')
        print('Duration:', self.event.format_duration() or 'Unknown')
        print('Location:', self.event.location or 'Unknown')
        print('')
        print('There are %d members, use the "members" command to list them' % len(self.event.members))
        if self.event.get_me() is None:
            print('To join this event, use the command "join".')

    def do_members(self, line):
        """
        members

        Display members information.
        """
        self.event.load()
        for member in self.event.members.values():
            print(member.name)
            print('-' * len(member.name))
            print('Repository:', member.repository)
            if self.event.date is None:
                print('Availabilities:', member.availabilities)
            print('Hardware:', member.hardware)
            accompl = 0
            for task in member.tasks:
                if task.status == task.STATUS_DONE:
                    accompl += 1
            print('%d tasks (%d accomplished)' % (len(member.tasks), accompl))
            if member is self.event.winner:
                print('=== %s is the winner!' % member.name)
            print('')

        print('Use the "tasks" command to display all tasks')

    def do_join(self, line):
        """
        join

        Join this event.
        """
        self.event.load()
        if self.event.backend.browser.get_userid() in self.event.members:
            print('You have already joined this event.', file=self.stderr)
            return 1

        if self.event.is_closed():
            print("Boobathon is closed.", file=self.stderr)
            return 1

        m = Member(self.event.backend.browser.get_userid(), None)
        self.edit_member(m)
        self.event.members[m.id] = m
        self.save_event('Joined the event')

    def do_leave(self, line):
        """
        leave

        Leave this event.
        """
        self.event.load()

        if self.event.currently_in_event():
            print('Unable to leave during the event, loser!', file=self.stderr)
            return 1

        if self.event.is_closed():
            print("Boobathon is closed.", file=self.stderr)
            return 1

        try:
            self.event.members.pop(self.event.backend.browser.get_userid())
        except KeyError:
            print("You have not joined this event.", file=self.stderr)
            return 1
        else:
            self.save_event('Left the event')

    def do_remtask(self, line):
        """
        remtask TASK_ID

        Remove a task.
        """
        self.event.load()
        mem = self.event.get_me()
        if not mem:
            print("You have not joined this event.", file=self.stderr)
            return 1

        if self.event.is_closed():
            print("Boobathon is closed.", file=self.stderr)
            return 1

        try:
            task_id = int(line)
        except ValueError:
            print('The task ID should be a number', file=self.stderr)
            return 2

        try:
            task = mem.tasks.pop(task_id)
        except IndexError:
            print('Unable to find task #%d' % task_id, file=self.stderr)
            return 1
        else:
            print('Removing task #%d (%s,%s).' % (task_id, task.backend, task.capability))
            self.save_event('Remove task')

    def do_addtask(self, line):
        """
        addtask BACKEND CAPABILITY

        Add a new task.
        """
        self.event.load()
        mem = self.event.get_me()
        if not mem:
            print("You have not joined this event.", file=self.stderr)
            return 1

        if self.event.is_closed():
            print("Boobathon is closed.", file=self.stderr)
            return 1

        backend, capability = self.parse_command_args(line, 2, 2)
        if not backend[0].isupper():
            print('The backend name "%s" needs to start with a capital.' % backend, file=self.stderr)
            return 2
        if not capability.startswith('Cap') or not capability[3].isupper():
            print('"%s" is not a proper capability name (must start with Cap).' % capability, file=self.stderr)
            return 2

        for task in mem.tasks:
            if (task.backend,task.capability) == (backend,capability):
                print("A task already exists for that.", file=self.stderr)
                return 1

        task = Task(backend, capability)
        mem.tasks.append(task)
        self.save_event('New task')

    def do_start(self, line):
        """
        start [TASK_ID]

        Start a task. If you don't give a task ID, the first available
        task will be taken.
        """
        self.event.load()
        mem = self.event.get_me()
        if not mem:
            print("You have not joined this event.", file=self.stderr)
            return 1

        if len(mem.tasks) == 0:
            print("You don't have any task to do.", file=self.stderr)
            return 1

        if not self.event.currently_in_event():
            print("You can't start a task, we are not in event.", file=self.stderr)
            return 1

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
                print('Task #%s (%s,%s) canceled.' % (i, task.backend, task.capability))

            if (i == task_id or task_id < 0) and task.status == task.STATUS_NONE:
                break
        else:
            print('Task not found.', file=self.stderr)
            return 3

        if task.status == task.STATUS_DONE:
            print('Task is already done.', file=self.stderr)
            return 1

        task.status = task.STATUS_PROGRESS
        mem.tasks.remove(task)
        mem.tasks.insert(last_done + 1, task)
        self.save_event('Started a task')

    def do_done(self, line):
        """
        done

        Set the current task as done.
        """
        self.event.load()
        mem = self.event.get_me()
        if not mem:
            print("You have not joined this event.", file=self.stderr)
            return 1

        if self.event.is_closed():
            print("Boobathon is closed.", file=self.stderr)
            return 1

        for i, task in enumerate(mem.tasks):
            if task.status == task.STATUS_PROGRESS:
                print('Task (%s,%s) done! (%d%%)' % (task.backend, task.capability, (i+1)*100/len(mem.tasks)))
                if self.event.currently_in_event():
                    task.status = task.STATUS_DONE
                    task.date = datetime.now()
                    task.branch = self.ask('Enter name of branch')
                    self.save_event('Task accomplished')
                else:
                    task.status = task.STATUS_NONE
                    print('Oops, you are out of event. Canceling the task...', file=self.stderr)
                    self.save_event('Cancel task')
                    return 1
                return

        print("There isn't any task in progress.", file=self.stderr)
        return 1

    def do_cancel(self, line):
        """
        cancel

        Cancel the current task.
        """
        self.event.load()
        mem = self.event.get_me()
        if not mem:
            print("You have not joined this event.", file=self.stderr)
            return 1

        if self.event.is_closed():
            print("Boobathon is closed.", file=self.stderr)
            return 1

        for task in mem.tasks:
            if task.status == task.STATUS_PROGRESS:
                print('Task (%s,%s) canceled.' % (task.backend, task.capability))
                task.status = task.STATUS_NONE
                self.save_event('Cancel task')
                return

        print("There isn't any task in progress.", file=self.stderr)
        return 1

    def load_default_backends(self):
        """
        Overload a Application method.
        """
        for backend_name, module_name, params in self.weboob.backends_config.iter_backends():
            if module_name != 'redmine':
                continue
            v = urlsplit(params['url'])
            if v.netloc == 'symlink.me':
                self.load_backends(names=[backend_name])
                return

        if not self.check_loaded_backends({'url': 'https://symlink.me'}):
            print("Ok, so leave now.")
            sys.exit(0)

    def is_module_loadable(self, module):
        """
        Overload a ConsoleApplication method.
        """
        return module.name == 'redmine'
