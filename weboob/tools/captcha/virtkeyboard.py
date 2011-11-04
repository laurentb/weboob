# -*- coding: utf-8 -*-

# Copyright(C) 2011  Pierre Mazière
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


import hashlib
import Image

class VirtKeyboardError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)


class VirtKeyboard(object):
    def __init__(self, file,coords,color=None):
        # file: virtual keyboard image
        # coords: dictionary <value to return>:<tuple(x1,y1,x2,y2)>
        # color: color of the symbols in the image
        #        depending on the image, it can be a single value or a tuple
        self.color=color
        img=Image.open(file)
        self.bands=img.getbands()
        (self.width,self.height)=img.size
        self.pixar=img.load()
        self.coords={}
        self.md5={}
        for i in coords.keys():
            if self.color is None:
                self.coords[i]=coords[i]
            else:
                coord=self.get_symbol_coords(coords[i])
                if coord==(-1,-1,-1,-1):
                    continue
                self.coords[i]=coord
            self.md5[i]=self.checksum(self.coords[i])

    def get_symbol_coords(self,(x1,y1,x2,y2)):
        newY1=-1
        newY2=-1
        for y in range(y1,min(y2+1,self.height)):
            empty_line=True
            for x in range(x1,min(x2+1,self.width)):
                if self.pixar[x,y] == self.color:
                    empty_line=False
                    if newY1==-1:
                        newY1=y
                        break;
                    else:
                        break
            if newY1!=-1 and empty_line:
                newY2=y-1
                break
        newX1=-1
        newX2=-1
        for x in range(x1,min(x2+1,self.width)):
            empty_column=True
            for y in range(y1,min(y2+1,self.height)):
                if self.pixar[x,y] == self.color:
                    empty_column=False
                    if newX1==-1:
                        newX1=x
                        break
                    else:
                        break
            if newX1!=-1 and empty_column:
                newX2=x-1
                break
        return (newX1,newY1,newX2,newY2)

    def checksum(self,(x1,y1,x2,y2)):
        s = ''
        for y in range(y1,min(y2+1,self.height)):
            for x in range(x1,min(x2+1,self.width)):
                if self.pixar[x,y]==self.color:
                    s += "."
                else:
                    s += " "
        return hashlib.md5(s).hexdigest()

    def get_symbol_code(self,md5sum):
        for i in self.md5.keys():
            if md5sum == self.md5[i]:
                return i
        raise VirtKeyboardError('Symbol not found')

    def generate_MD5(self,dir):
        for i in self.coords.keys():
            width=self.coords[i][2]-self.coords[i][0]+1
            height=self.coords[i][3]-self.coords[i][1]+1
            img=Image.new(''.join(self.bands),(width,height))
            matrix=img.load()
            for y in range(height):
                for x in range(width):
                    matrix[x,y]=self.pixar[self.coords[i][0]+x,self.coords[i][1]+y]
            img.save(dir+"/"+self.md5[i]+".png")

