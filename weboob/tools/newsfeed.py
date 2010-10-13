import datetime
import feedparser


class Entry:
    def __init__(self, entry, url2id=None):
        if url2id:
            self.id = url2id(entry.id)
        else:
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
            #updated_parsed = entry["updated_parsed"]
            self.datetime = datetime.datetime(*entry['updated_parsed'][:7])
        else:
            self.datetime = None
        if entry.has_key("content"):
            self.content = entry["content"][0]["value"]
        else:
            self.content = None


class NewsFeed:
    def __init__(self, url, url2id=None):
        self.feed = feedparser.parse(url)
        self.url2id = url2id

    
        

    def iter_entries(self):
        for entry in self.feed['entries']:
            yield Entry(entry, self.url2id)

    def get_entry(self, id):
        for entry in self.feed['entries']:
            if entry.id == id:
                return Entry(entry, self.url2id)
            
