import six


class AddressComponents:
    NAME = 'house'
    HOUSE_NUMBER = 'house_number'
    STREET = 'road'
    FLOOR = 'floor'
    UNIT = 'unit'
    POSTAL_CODE = 'postcode'


class Coordinates:
    LATITUDE = 'lat'
    LONGITUDE = 'lon'


class VenueDetails:
    PHONE = 'phone'
    WEBSITE = 'website'


class Address(object):
    field_map = {
        'name': AddressComponents.NAME,
        'house': AddressComponents.NAME,
        'addr:housename': AddressComponents.NAME,
        'wof:name': AddressComponents.NAME,
        'addr:housenumber': AddressComponents.HOUSE_NUMBER,
        'house_number': AddressComponents.HOUSE_NUMBER,
        'housenumber': AddressComponents.HOUSE_NUMBER,
        'addr:street': AddressComponents.STREET,
        'street': AddressComponents.STREET,
        'addr:floor': AddressComponents.FLOOR,
        'addr:level': AddressComponents.FLOOR,
        'level': AddressComponents.FLOOR,
        'floor': AddressComponents.FLOOR,
        'addr:unit': AddressComponents.UNIT,
        'unit': AddressComponents.UNIT,
        'addr:postcode': AddressComponents.POSTAL_CODE,
        'postcode': AddressComponents.POSTAL_CODE,
        'postal_code': AddressComponents.POSTAL_CODE,
        'postalcode': AddressComponents.POSTAL_CODE,
        'phone': VenueDetails.PHONE,
        'sg:phone': VenueDetails.PHONE,
        'contact:phone': VenueDetails.PHONE,
        'telephone': VenueDetails.PHONE,
        'sg:website': VenueDetails.WEBSITE,
        'website': VenueDetails.WEBSITE,
        'contact:website': VenueDetails.WEBSITE,
    }

    @classmethod
    def from_geojson(cls, data):
        properties = data.get('properties')
        fields = {cls.field_map[k]: v for k, v in six.iteritems(properties) if k in cls.field_map}
        lon, lat = data.get('geometry', {}).get('coordinates', (None, None))
        if lat is not None:
            fields[Coordinates.LATITUDE] = lat
        if lon is not None:
            fields[Coordinates.LONGITUDE] = lon

        return fields
