from weboob.capabilities.housing import Query

QUERY_TYPES = {
    Query.TYPE_RENT: 'location',
    Query.TYPE_SALE: 'achat'
}

QUERY_HOUSE_TYPES = {
    Query.HOUSE_TYPES.APART: ['appartement'],
    Query.HOUSE_TYPES.HOUSE: ['maison'],
    Query.HOUSE_TYPES.PARKING: ['parking'],
    Query.HOUSE_TYPES.LAND: ['terrain'],
    Query.HOUSE_TYPES.OTHER: ['chambre', 'appartement-meuble',
                              'local-commercial', 'immeuble']
}

AVAILABLE_TYPES = {
    Query.TYPE_RENT: ['appartement', 'maison', 'parking', 'chambre',
                      'appartement-meuble', 'local-commercial'],
    Query.TYPE_SALE: ['appartement', 'maison', 'parking', 'local-commercial',
                      'terrain', 'immeuble']
}
