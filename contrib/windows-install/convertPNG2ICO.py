#!C:\Python27\python.exe
# -*- coding: utf-8 -*-
#
# windows icon file(.ico) and cursor file(.cur) generator/writer from RGB(a) array
#
#    NOTICE: one image per file *only*, 16x16 or 32x32 or 48x48 or 64x64 *only*
#    Support 24 bit & 32 bit(RGB + alpha)
#
# Copyright 2009 ( http://creativecommons.org/licenses/by-nc-sa/2.5/cn/ )
#
# About Author
#   Blog( http://2maomao.com/blog/ )
#   Website( http://fayaa.com/tool/favicon/ )
#   Contact me via email
#
# References:
#  [1] http://en.wikipedia.org/wiki/Ico_Format
#  [2] http://en.wikipedia.org/wiki/Windows_and_OS/2_bitmap
#  [3] http://support.microsoft.com/kb/83034
#  [4] http://msdn.microsoft.com/en-us/library/ms997538(loband).aspx
#  [5] http://www.martinreddy.net/gfx/2d/BMP.txt
#  [6] http://code.google.com/p/casadebender/source/browse/python/PIL/Win32IconImagePlugin.py
#  [7] http://www.osphp.com.cn/read.php/290.htm


from PIL import Image
import sys
import os

# data: a size*size of (r,g,b,t) tuples, t for tansparency(if True)
#       (r,g,b,a) if bpp is 32
# size: could be 16 or 32 or 48 or 64, other value NOT supported
# bpp: bits per pixel, could *only* be 24 or 32!
# return: an "array" of BYTES which, if write to file, is a size*size ico file


def genico(data, size=16, bpp=24):
    from array import array
    a = array('B')
    #header(ref1&5)
    a.extend((0,0, 1,0, 1,0)) #reserved*2, icon,0, 1 image per-file,0
    #directory(ref1&5&7)
    # image-part length in bytes
    # !hack! AND bits align to 32 bits per line
    # !shit! MSDN says nothing about this
    imglen = 40+size*(size*3 + (size+16)/32*32/8)

    if bpp == 32:
        imglen += size*size #1 more byte for alpha value of each pixel
    a.extend((size,size, 0,0, 1,0, bpp,0)) #w,h, reserved*2, 1plane*2, bpp*2
    a.extend((imglen&0xff,imglen>>8,0,0, 22,0,0,0)) #bitmap-size*4,22B-offset*4
    #image BITMAPINFOHEADER(ref5)
    a.extend((40,0,0,0)) #size of data(contains header)*4
    a.extend((size,0,0,0, size*2,0,0,0))#w*4, (h+h)*4 (!shit hack! XOR+AND)
    a.extend((1,0, bpp,0, 0,0,0,0, 0,0,0,0)) #1 plane*2, 24 bits*2, no compress*4, rawBMPsize(no compress so 0)*4
    a.extend((0,1,0,0, 0,1,0,0)) #horizontal*4/vertical*4 resolution pixels/meter(WTF?)
    a.extend((0,0,0,0, 0,0,0,0)) #colors fully used, all are important
    #!no planes
    #image content(ref1&5), XOR+AND bitmaps
    AND = array('B')
    vand = 0
    vcnt = 0
    #remember that bitmap format is reversed in y-axis
    for x in range(size-1,-1,-1):
        for y in range(0, size):
            b,g,r,t_or_a = data[y*size+x]
            a.extend((r,g,b))
            if bpp == 32:
                a.append(t_or_a)
            vcnt+=1
            vand<<=1
            if (bpp==24 and t_or_a) or (bpp==32 and t_or_a<128):
                vand |= 1
            if vcnt==8:
                AND.append(vand)
                vcnt=0
                vand=0
        #!hack! AND bits align to 32 bits per line, !shit! MSDN says nothing about this
        AND.extend([0] * ((32-size%32)%32/8))
    a.extend(AND)
    return a


# x,y indicate the hotspot position
# simply set the type/hotspot(x&y) after generates the icon
def gencur(data, size=16, bpp=24, x=0, y=0):
    a = genico(data, size, bpp)
    a[3], a[10], a[12] = 2, x, y
    return a


#C:\Python27\Lib\site-packages\weboob-0.g-py2.7.egg\share\icons\hicolor\64x64\apps

if __name__ == "__main__":
    if len(sys.argv) == 2:
        png_file = sys.argv[1]

        f, e = os.path.splitext(png_file)
        ico_file = f + ".ico"

        im = Image.open(r"%s" % png_file)
        wh = 64

        rgba = im.convert("RGBA")

        data = []
        for i in range(wh):
            for j in range(wh):
                data.append(rgba.getpixel((i,j)))

        icoflow = genico(data, wh, 32)
        _file = open(ico_file, "wb")
        icoflow.tofile(_file)
        _file.close()
