# -*- coding: utf-8 -*-

from weboob.tools.backend import BaseBackend
from weboob.capabilities.messages import ICapMessages, Message, Thread
import datetime
import feedparser

    

class Article:
    def __init__(self, entry):
        self.id = entry.id
        if entry.has_key("link"):
            self.link = entry["link"]
        if entry.has_key("title"):
            self.title = entry["title"]
        else:
            self.title = None
        if entry.has_key("author"):
            self.author = entry["author"]
        else:
            self.author = None
        if entry.has_key("updated_parsed"):
            updated_parsed = entry["updated_parsed"]
            self.datetime = datetime.datetime(updated_parsed.tm_year,
                                              updated_parsed.tm_mon,
                                              updated_parsed.tm_mday,
                                              updated_parsed.tm_hour,
                                              updated_parsed.tm_min,
                                              updated_parsed.tm_sec)
        else:
            self.datetime = None
        if entry.has_key("content"):
            self.content = entry["content"][0]["value"]
        else:
            self.content = None


class NewsFeed:
    def __init__(self, url):
        self.feed = feedparser.parse(url)

    
        

    def iter_articles(self):
        for entry in self.feed['entries']:
            yield Article(entry)

    def get_article(self, id):
        for entry in self.feed['entries']:
            if entry.id == id:
                return Article(entry)
            


    

class NewsFeedBackend(BaseBackend, ICapMessages):
    NAME = 'newsfeed'
    MAINTAINER = "Clement Schreiner"
    EMAIL = "clemux@clemux.info"
    VERSION = "0.1"
    DESCRIPTION = "News feeds"
    LICENSE = "GPLv3"
    CONFIG = {'url': BaseBackend.ConfigField(description='URL to the feed'),}
    STORAGE = {'seen': {}}
    
              
    def iter_threads(self):
        for article in NewsFeed(self.config["url"]).iter_articles():
            thread = Thread(article.id)
            thread.title = article.title
            yield thread
            
        

    def get_thread(self, id):
        if isinstance(id, Thread):
            thread = id
            id = thread.id
        else:
            thread = Thread(id)
        article = NewsFeed(self.config["url"]).get_article(id)
        flags = 0
        if not thread.id in self.storage.get('seen', default={}):
            flags |= Message.IS_UNREAD
        thread.title = article.title
        thread.root = Message(thread=thread,
                              id=0,
                              title=article.title,
                              sender=article.author,
                              receiver=None,
                              date=article.datetime,
                              parent=None,
                              content=article.content,
                              flags=flags)
        return thread
                              
        

    def iter_unread_messages(self, thread=None):
        for thread in self.iter_threads():
            for m in thread.iter_all_messages():
                if m.flags & m.IS_UNREAD:
                    yield m


    def set_message_read(self, message):
        self.storage.set('seen', message.thread.id)
        self.storage.save()
