from weboob.capabilities.housing import POSTS_TYPES, HOUSE_TYPES

QUERY_TYPES = {
    POSTS_TYPES.RENT: 'location',
    POSTS_TYPES.SALE: 'achat'
}

QUERY_HOUSE_TYPES = {
    HOUSE_TYPES.APART: ['appartement'],
    HOUSE_TYPES.HOUSE: ['maison'],
    HOUSE_TYPES.PARKING: ['parking'],
    HOUSE_TYPES.LAND: ['terrain'],
    HOUSE_TYPES.OTHER: ['chambre', 'appartement-meuble',
                        'local-commercial', 'immeuble']
}

AVAILABLE_TYPES = {
    POSTS_TYPES.RENT: ['appartement', 'maison', 'parking', 'chambre',
                       'appartement-meuble', 'local-commercial'],
    POSTS_TYPES.SALE: ['appartement', 'maison', 'parking', 'local-commercial',
                       'terrain', 'immeuble']
}
