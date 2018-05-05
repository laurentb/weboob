
import weboob.capabilities.recipe as OLD

# can't import *, __all__ is incomplete...
for attr in dir(OLD):
    globals()[attr] = getattr(OLD, attr)


class Recipe(OLD.Recipe):
    @property
    def picture_url(self):
        return getattr(self, 'picture', None) and self.picture.url

    @property
    def thumbnail_url(self):
        return getattr(self, 'picture', None) and self.picture.thumbnail and self.picture.thumbnail.url
