
import weboob.capabilities.housing as OLD

# can't import *, __all__ is incomplete...
for attr in dir(OLD):
    globals()[attr] = getattr(OLD, attr)


__all__ = OLD.__all__


ENERGY_CLASS = enum(A=u'A', B=u'B', C=u'C', D=u'D', E=u'E', F=u'F', G=u'G')


POSTS_TYPES = enum(RENT=u'RENT',
                   SALE=u'SALE',
                   SHARING=u'SHARING',
                   FURNISHED_RENT=u'FURNISHED_RENT',
                   VIAGER=u'VIAGER')


ADVERT_TYPES = enum(PROFESSIONAL=u'Professional', PERSONAL=u'Personal')


HOUSE_TYPES = enum(APART=u'Apartment',
                   HOUSE=u'House',
                   PARKING=u'Parking',
                   LAND=u'Land',
                   OTHER=u'Other',
                   UNKNOWN=u'Unknown')

