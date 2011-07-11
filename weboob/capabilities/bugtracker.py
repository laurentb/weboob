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

from .base import IBaseCap, CapBaseObject


__all__ = ['ICapBugTracker']


class IssueError(Exception):
    pass

class Project(CapBaseObject):
    def __init__(self, id, name):
        CapBaseObject.__init__(self, id)
        self.add_field('name', unicode, name)
        self.add_field('members', list)
        self.add_field('versions', list)
        self.add_field('categories', list)
        self.add_field('statuses', list)

    def __repr__(self):
        return '<Project %r>' % self.name

    def find_user(self, id, name):
        for user in self.members:
            if user.id == id:
                return user
        if name is None:
            return None
        return User(id, name)

    def find_version(self, id, name):
        for version in self.versions:
            if version.id == id:
                return version
        if name is None:
            return None
        return Version(id, name)

    def find_status(self, name):
        for status in self.statuses:
            if status.name == name:
                return status
        if name is None:
            return None
        return None

class User(CapBaseObject):
    def __init__(self, id, name):
        CapBaseObject.__init__(self, id)
        self.add_field('name', unicode, name)

    def __repr__(self):
        return '<User %r>' % self.name

class Version(CapBaseObject):
    def __init__(self, id, name):
        CapBaseObject.__init__(self, id)
        self.add_field('name', unicode, name)

    def __repr__(self):
        return '<Version %r>' % self.name

class Status(CapBaseObject):
    (VALUE_NEW,
     VALUE_PROGRESS,
     VALUE_RESOLVED,
     VALUE_REJECTED) = range(4)

    def __init__(self, id, name, value):
        CapBaseObject.__init__(self, id)
        self.add_field('name', unicode, name)
        self.add_field('value', int, value)

    def __repr__(self):
        return '<Status %r>' % self.name

class Attachment(CapBaseObject):
    def __init__(self, id):
        CapBaseObject.__init__(self, id)
        self.add_field('filename', basestring)
        self.add_field('url', basestring)

    def __repr__(self):
        return '<Attachment %r>' % self.filename

class Update(CapBaseObject):
    def __init__(self, id):
        CapBaseObject.__init__(self, id)
        self.add_field('author', User)
        self.add_field('date', datetime)
        self.add_field('message', unicode)
        self.add_field('attachments', (list,tuple))
        self.add_field('changes', (list,tuple))

    def __repr__(self):
        return '<Update %r>' % self.id

class Issue(CapBaseObject):
    def __init__(self, id):
        CapBaseObject.__init__(self, id)
        self.add_field('project', Project)
        self.add_field('title', unicode)
        self.add_field('body', unicode)
        self.add_field('creation', datetime)
        self.add_field('updated', datetime)
        self.add_field('attachments', (list,tuple))
        self.add_field('history', (list,tuple))
        self.add_field('author', User)
        self.add_field('assignee', User)
        self.add_field('category', unicode)
        self.add_field('version', Version)
        self.add_field('status', Status)

class Query(CapBaseObject):
    def __init__(self):
        CapBaseObject.__init__(self, '')
        self.add_field('project', unicode)
        self.add_field('title', unicode)
        self.add_field('author', unicode)
        self.add_field('assignee', unicode)
        self.add_field('version', unicode)
        self.add_field('category', unicode)
        self.add_field('status', unicode)

class ICapBugTracker(IBaseCap):
    def iter_issues(self, query):
        """
        Iter issues with optionnal patterns.

        @param  query [Query]
        @return [iter(Issue)] issues
        """
        raise NotImplementedError()

    def get_issue(self, id):
        """
        Get an issue from its ID.

        @return Issue
        """
        raise NotImplementedError()

    def create_issue(self, project):
        """
        Create an empty issue on the given project.

        @return [Issue]  the created issue.
        """
        raise NotImplementedError()

    def post_issue(self, issue):
        """
        Post an issue to create or update it.
        """
        raise NotImplementedError()

    def update_issue(self, issue, update):
        """
        Add an update to an issue.

        @param issue [id,Issue]  issue or id of issue
        @param update [Update]  an Update object
        """
        raise NotImplementedError()

    def remove_issue(self, issue):
        """
        Remove an issue.
        """
        raise NotImplementedError()

    def iter_projects(self):
        """
        Iter projects.

        @return [iter(Project)] projects
        """
        raise NotImplementedError()

    def get_project(self, id):
        """
        Get a project from its ID.

        @return [Project]
        """
        raise NotImplementedError()
