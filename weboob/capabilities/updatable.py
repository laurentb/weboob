# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""


class ICapUpdatable:
    snapshots = {}

    def take_snapshot(self, name, collection):
        if name not in self.snapshots:
            self.snapshots[name] = dict(original=set(collection))
        elif 'original' in self.snapshots[name]:
            if 'updated' in self.snapshots[name]:
                self.snapshots[name]['original'] = self.snapshots[name]['updated']
            self.snapshots[name]['updated'] = set(collection)

    def iter_new_items(self, name):
        """
        Iterates on new items from last time this function has been called.

        @param name [str]  name of the collection to iter
        @return [iter]  new items
        """
        if name not in self.snapshots:
            raise ValueError('"%s" has not been snapshot previously' % name)
        elif 'original' not in self.snapshots[name] or 'updated' not in self.snapshots[name]:
            raise ValueError('At least two snapshots are required to detect new items')
        diff = self.snapshots[name]['updated'] - self.snapshots[name]['original']
        for item in diff:
            yield item
