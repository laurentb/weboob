from weboob.capabilities.housing import HOUSE_TYPES, POSTS_TYPES

QUERY_TYPES = {
    POSTS_TYPES.RENT: 2,
    POSTS_TYPES.SALE: 1,
    POSTS_TYPES.SHARING: 2,  # There is no special search for shared appartments.
    POSTS_TYPES.FURNISHED_RENT: 2,
    POSTS_TYPES.VIAGER: 1
}

QUERY_HOUSE_TYPES = {
    HOUSE_TYPES.APART: ['1'],
    HOUSE_TYPES.HOUSE: ['2'],
    HOUSE_TYPES.PARKING: ['7'],
    HOUSE_TYPES.LAND: ['3'],
    HOUSE_TYPES.OTHER: ['4', '5', '6', '8', '9', '10', '11', '12', '13', '14'],
    HOUSE_TYPES.UNKNOWN: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14']
}
