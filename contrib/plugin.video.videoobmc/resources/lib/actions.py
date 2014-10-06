# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
from . import constants

from .base.actions import BaseAction
from .menu import MenuItem, MenuItemVideo, MenuItemPath
from threading import Thread
from .videoobmc import Videoobmc

if hasattr(sys.modules["__main__"], "common_xbmc"):
    common_xbmc = sys.modules["__main__"].common_xbmc
else:
    import common_xbmc


class VideoobBaseAction(BaseAction):
    def __init__(self):
        count = common_xbmc.get_settings('nbVideoPerBackend')
        numbers = ["10", "25", "50", "100"]
        self.videoobmc = Videoobmc(count=numbers[int(count)], nsfw=common_xbmc.get_settings('nsfw'))


class DisplayMenuAction(VideoobBaseAction):
    def _do(self, param={}):
        backends = self.videoobmc.backends
        if backends:
            MenuItem(common_xbmc.get_translation('30000'), constants.SEARCH).add_to_menu()
            for backend in backends:
                icon = self.videoobmc.get_backend_icon(backend)
                MenuItem(backend, constants.DISPLAY_BACKENDS, backend=backend, iconimage=icon).add_to_menu()
            common_xbmc.end_of_directory(False)
        else:
            common_xbmc.display_error(" Please install and configure weboob")


class DisplayCollectionMenuAction(VideoobBaseAction):
    def _do(self, param={}):
        path = param.get('path') if 'path' in param.keys() else ''
        collections, videos = self.videoobmc.ls(param.get('backend'), path=path)
        threads = []

        for col in collections:
            MenuItemPath(col).add_to_menu()
        for video in videos:
            aThread = Thread(target=self.add_videos, args=(video, video.backend))
            threads.append(aThread)
            aThread.start()

        for t in threads:
            t.join()

        common_xbmc.end_of_directory(False)

    def add_videos(self, _video, backend):
        print(_video)
        video = self.videoobmc.get_video(_video, backend)
        if video:
            MenuItemVideo(video).add_to_menu()


class DownloadAction(VideoobBaseAction):
    def _do(self, param={}):
        _id = param.get('id')
        backend = param.get('backend')
        if _id:
            aThread = Thread(target=self.download, args=(_id, backend))
            aThread.start()
            common_xbmc.display_info(common_xbmc.get_translation('30301'))
        common_xbmc.end_of_directory(False)

    def download(self, _id, backend):
        dl_dir = common_xbmc.get_settings('downloadPath')
        self.videoobmc.download(_id, dl_dir if dl_dir else common_xbmc.get_addon_dir(), backend)
        common_xbmc.display_info(common_xbmc.get_translation('30302'))


class SearchAction(VideoobBaseAction):
    def _do(self, param={}):
        pattern = common_xbmc.ask_user('', common_xbmc.get_translation('30001'))
        if pattern:
            for video in self.videoobmc.search(pattern, param.get('backend')):
                MenuItemVideo(video).add_to_menu()
            common_xbmc.end_of_directory(False)


class DisplayBackendsAction(VideoobBaseAction):
    def _do(self, param={}):
        backend = param.get('backend')
        if backend:
            MenuItem('Search', constants.SEARCH, backend=backend).add_to_menu()
            DisplayCollectionMenuAction()._do(param)
        else:
            common_xbmc.end_of_directory(False)


class UpdateWeboobAction(VideoobBaseAction):
    def _do(self, param={}):
        common_xbmc.display_info(common_xbmc.get_translation('30551'))
        self.videoobmc.update()
        common_xbmc.display_info(common_xbmc.get_translation('30552'))


actions = {constants.DISPLAY_MENU: DisplayMenuAction,
           constants.DISPLAY_COLLECTION_MENU: DisplayCollectionMenuAction,
           constants.SEARCH: SearchAction,
           constants.DOWNLOAD: DownloadAction,
           constants.DISPLAY_BACKENDS: DisplayBackendsAction,
           constants.UPDATE: UpdateWeboobAction}
