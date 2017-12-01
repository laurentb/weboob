from weboob.capabilities.housing import POSTS_TYPES, HOUSE_TYPES

TYPES = {POSTS_TYPES.RENT: 'location',
         POSTS_TYPES.FURNISHED_RENT: 'location',
         POSTS_TYPES.SALE: 'vente',
         POSTS_TYPES.VIAGER: 'vente'}

RET = {HOUSE_TYPES.HOUSE: 'maison',
       HOUSE_TYPES.APART: 'appartement',
       HOUSE_TYPES.LAND: 'terrain',
       HOUSE_TYPES.PARKING: 'garage-parking',
       HOUSE_TYPES.OTHER: 'divers'}
