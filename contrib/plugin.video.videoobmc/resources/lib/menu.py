# -*- coding: utf-8 -*-
import sys
from . import constants

from datetime import datetime, timedelta
from .base.menu import BaseMenuItem, BaseMenuLink

if hasattr(sys.modules["__main__"], "common_xbmc"):
    common_xbmc = sys.modules["__main__"].common_xbmc
else:
    import common_xbmc


class MenuItem(BaseMenuItem):
    params = {}

    def __init__(self, name, action, iconimage="DefaultFolder.png", backend=''):
        BaseMenuItem.__init__(self, name, action, iconimage)
        self.params['backend'] = backend


class MenuItemPath(MenuItem):

    def __init__(self, collection, action=constants.DISPLAY_COLLECTION_MENU, iconimage="DefaultFolder.png"):
        MenuItem.__init__(self, collection.title, action, iconimage, collection.fullid.split('@')[-1])
        self.params["path"] = '/'.join(collection.split_path)


class MenuItemVideo(BaseMenuLink):
    def __init__(self, video, iconimage="DefaultFolder.png"):
        name = '[%s] %s' % (video.backend, video.title)
        BaseMenuLink.__init__(self, name, video.url, constants.VIDEO,
                              video.thumbnail.url if video.thumbnail.url else iconimage)
        self.video = video
        self.params["id"] = self.video.id

    def createVideoContextMenu(self):
        cm = []

        #Information
        cm.append((common_xbmc.get_translation('30110'), "XBMC.Action(Info)"))

        #Téléchargement
        url = "%s?action=%s&id=%s&backend=%s" % (sys.argv[0], constants.DOWNLOAD, self.video.id, self.video.backend)
        cm.append((common_xbmc.get_translation('30100'), "XBMC.PlayMedia(%s)" % (url)))

        return cm

    def create_info_labels(self):
        date, year = self.format_date(self.video.date)

        duration = 0
        if self.video.duration:
            duration = u'%s' % str(self.video.duration.total_seconds()/60) if isinstance(self.video.duration, timedelta) else self.video.duration

        description = u'%s' % self.video.description

        return {"Title": self.video.title,
                "Year": year,
                "Plot": description,
                "PlotOutline": description[0:30] if len(description) > 30 else description,
                "Director": self.video.author if self.video.author else 'Unknown',
                "Duration": duration,
                "Date": date}

    def format_date(self, video_date):
        date = datetime.now().strftime("%d/%m/%Y")
        if video_date:
            date = video_date.strftime("%d/%m/%Y")

        year = date.split('/')[-1]
        return date, year
