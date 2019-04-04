from weboob.capabilities.housing import POSTS_TYPES, HOUSE_TYPES

QUERY_TYPES = {
    POSTS_TYPES.RENT: 'location',
    POSTS_TYPES.SALE: 'achat',
    POSTS_TYPES.FURNISHED_RENT: 'location'
}

QUERY_HOUSE_TYPES = {
    HOUSE_TYPES.APART: ['appartement', 'appartement-meuble'],
    HOUSE_TYPES.HOUSE: ['maison'],
    HOUSE_TYPES.PARKING: ['parking'],
    HOUSE_TYPES.LAND: ['terrain'],
    HOUSE_TYPES.OTHER: ['chambre', 'programme-neuf',
                        'local-commercial', 'immeuble']
}

AVAILABLE_TYPES = {
    POSTS_TYPES.RENT: ['appartement', 'maison', 'parking', 'chambre',
                       'local-commercial'],
    POSTS_TYPES.SALE: ['appartement', 'maison', 'parking', 'local-commercial',
                       'terrain', 'immeuble', 'programme-neuf'],
    POSTS_TYPES.FURNISHED_RENT: ['appartement-meuble']
}
