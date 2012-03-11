# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012  Nicolas Duhamel, Laurent Bachelier
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

from .base import IBaseCap, CapBaseObject

__all__ = ['ICapCollection', 'Collection', 'CollectionNotFound']


class CollectionNotFound(Exception):
    def __init__(self, split_path=None):
        if split_path is not None:
            msg = 'Collection not found: %s' % '/'.join(split_path)
        else:
            msg = 'Collection not found'
        Exception.__init__(self, msg)


class Collection(CapBaseObject):
    """
    A Collection is a "fake" object returned in results, which shows you can get
    more results if you go into its path.

    It is a dumb object, it must not contain callbacks to a backend.
    """
    def __init__(self, split_path, title=None, backend=None):
        self.split_path = split_path
        self.title = title
        _id = split_path[-1] if len(split_path) else None
        CapBaseObject.__init__(self, _id, backend)

    def __unicode__(self):
        if self.title and self.id:
            return u'%s (%s)' % (self.id, self.title)
        elif self.id:
            return u'%s' % self.id
        else:
            return u'Unknown collection'


class ICapCollection(IBaseCap):
    def iter_resources_flat(self, objs, split_path, clean_only=False):
        """
        Call iter_resources() to fetch all resources in the tree.
        If clean_only is True, do not explore paths, only remove them.
        split_path is used to set the starting path.
        """
        for resource in self.iter_resources(objs, split_path):
            if isinstance(resource, Collection):
                if not clean_only:
                    for res in self.iter_resources_flat(objs, resource.split_path):
                        yield res
            else:
                yield resource

    def iter_resources(self, objs, split_path):
        """
        split_path is a list, either empty (root path) or with one or many
        components.
        """
        raise NotImplementedError()

    def get_collection(self, objs, split_path):
        """
        Get a collection for a given split path.
        If the path is invalid (i.e. can't be handled by this module),
        it should return None.
        """
        collection = Collection(split_path, None, self.name)
        return self.validate_collection(objs, collection) or collection

    def validate_collection(self, objs, collection):
        """
        Tests if a collection is valid.
        For compatibility reasons, and to provide a default way, it checks if
        the collection has at least one object in it. However, it is not very
        efficient or exact, and you are encouraged to override this method.
        You can replace the collection object entirely by returning a new one.
        """
        # Root
        if len(collection.split_path) == 0:
            return
        try:
            i = self.iter_resources(objs, collection.split_path)
            i.next()
        except StopIteration:
            raise CollectionNotFound(collection.split_path)

    def _restrict_level(self, split_path, lmax=0):
        if len(split_path) > lmax:
            raise CollectionNotFound(split_path)
