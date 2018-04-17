import six
from collections import defaultdict, OrderedDict
from lieu.coordinates import latlon_to_decimal
from lieu.encoding import safe_decode


class AddressComponents:
    NAME = 'house'
    HOUSE_NUMBER = 'house_number'
    HOUSE_NUMBER_BASE = 'house_number_base'
    STREET = 'road'
    BUILDING = 'building'
    FLOOR = 'floor'
    UNIT = 'unit'
    SUBURB = 'suburb'
    CITY_DISTRICT = 'city_district'
    CITY = 'city'
    STATE_DISTRICT = 'state_district'
    ISLAND = 'island'
    STATE = 'state'
    COUNTRY_REGION = 'country_region'
    COUNTRY = 'country'
    WORLD_REGION = 'world_region'
    POSTAL_CODE = 'postcode'


class Coordinates:
    LATITUDE = 'lat'
    LONGITUDE = 'lon'


class EntityDetails:
    PHONE = 'phone'
    WEBSITE = 'website'
    EMAIL = 'email'
    FACEBOOK = 'facebook'
    TWITTER = 'twitter'
    INSTAGRAM = 'instagram'


class Aliases(object):
    def __init__(self, aliases):
        self.aliases = aliases
        self.priorities = {k: i for i, k in enumerate(aliases)}

    def key_priority(self, key):
        return self.priorities.get(key, len(self.priorities))

    def get(self, key, default=None):
        return self.aliases.get(key, default)

    def replace(self, components):
        replacements = defaultdict(list)
        for k in list(components):
            new_key = self.aliases.get(k)
            if new_key and new_key not in components:
                replacements[new_key].append(k)

        values = {}
        for key, source_keys in six.iteritems(replacements):
            source_keys.sort(key=self.key_priority)
            values[key] = components[source_keys[0]]
        return values


class Address(object):
    field_map = Aliases(
        OrderedDict([
            ('name', AddressComponents.NAME),
            ('wof:name', AddressComponents.NAME),
            ('house', AddressComponents.NAME),
            ('addr:housename', AddressComponents.NAME),
            ('addr:housenumber', AddressComponents.HOUSE_NUMBER),
            ('addr:house_number', AddressComponents.HOUSE_NUMBER),
            ('addr:housenumber:base', AddressComponents.HOUSE_NUMBER_BASE),
            ('house_number', AddressComponents.HOUSE_NUMBER),
            ('housenumber', AddressComponents.HOUSE_NUMBER),
            ('addr:street', AddressComponents.STREET),
            ('street', AddressComponents.STREET),
            ('addr:floor', AddressComponents.FLOOR),
            ('addr:level', AddressComponents.FLOOR),
            ('level', AddressComponents.FLOOR),
            ('floor', AddressComponents.FLOOR),
            ('addr:unit', AddressComponents.UNIT),
            ('unit', AddressComponents.UNIT),
            ('neighborhood', AddressComponents.SUBURB),
            ('addr:neighborhood', AddressComponents.SUBURB),
            ('is_in:neighborhood', AddressComponents.SUBURB),
            ('neighbourhood', AddressComponents.SUBURB),
            ('addr:neighbourhood', AddressComponents.SUBURB),
            ('is_in:neighbourhood', AddressComponents.SUBURB),
            ('barangay', AddressComponents.SUBURB),
            ('addr:barangay', AddressComponents.SUBURB),
            ('is_in:barangay', AddressComponents.SUBURB),
            ('suburb', AddressComponents.SUBURB),
            ('addr:suburb', AddressComponents.SUBURB),
            ('is_in:suburb', AddressComponents.SUBURB),
            ('city', AddressComponents.CITY),
            ('addr:city', AddressComponents.CITY),
            ('is_in:city', AddressComponents.CITY),
            ('municipality', AddressComponents.CITY),
            ('addr:municipality', AddressComponents.CITY),
            ('is_in:municipality', AddressComponents.CITY),
            ('locality', AddressComponents.CITY),
            ('addr:locality', AddressComponents.CITY),
            ('is_in:locality', AddressComponents.CITY),
            ('city_district', AddressComponents.CITY_DISTRICT),
            ('addr:city_district', AddressComponents.CITY_DISTRICT),
            ('is_in:city_district', AddressComponents.CITY_DISTRICT),
            ('quarter', AddressComponents.CITY_DISTRICT),
            ('addr:quarter', AddressComponents.CITY_DISTRICT),
            ('is_in:quarter', AddressComponents.CITY_DISTRICT),
            ('county', AddressComponents.STATE_DISTRICT),
            ('addr:county', AddressComponents.STATE_DISTRICT),
            ('is_in:county', AddressComponents.STATE_DISTRICT),
            ('state_district', AddressComponents.STATE_DISTRICT),
            ('addr:state_district', AddressComponents.STATE_DISTRICT),
            ('is_in:state_district', AddressComponents.STATE_DISTRICT),
            ('island', AddressComponents.ISLAND),
            ('addr:island', AddressComponents.ISLAND),
            ('is_in:island', AddressComponents.ISLAND),
            ('state', AddressComponents.STATE),
            ('addr:state', AddressComponents.STATE),
            ('is_in:state', AddressComponents.STATE),
            ('governorate', AddressComponents.STATE),
            ('addr:governorate', AddressComponents.STATE),
            ('is_in:governorate', AddressComponents.STATE),
            ('province', AddressComponents.STATE),
            ('addr:province', AddressComponents.STATE),
            ('is_in:province', AddressComponents.STATE),
            ('region', AddressComponents.STATE),
            ('addr:region', AddressComponents.STATE),
            ('is_in:region', AddressComponents.STATE),
            ('postcode', AddressComponents.POSTAL_CODE),
            ('addr:postcode', AddressComponents.POSTAL_CODE),
            ('postal_code', AddressComponents.POSTAL_CODE),
            ('addr:postal_code', AddressComponents.POSTAL_CODE),
            ('zipcode', AddressComponents.POSTAL_CODE),
            ('addr:zipcode', AddressComponents.POSTAL_CODE),
            ('zip_code', AddressComponents.POSTAL_CODE),
            ('addr:zip_code', AddressComponents.POSTAL_CODE),
            ('zip', AddressComponents.POSTAL_CODE),
            ('addr:zip', AddressComponents.POSTAL_CODE),
            ('postalcode', AddressComponents.POSTAL_CODE),
            ('addr:postalcode', AddressComponents.POSTAL_CODE),
            ('iso:country', AddressComponents.COUNTRY),
            ('country_code', AddressComponents.COUNTRY),
            ('addr:country_code', AddressComponents.COUNTRY),
            ('is_in:country_code', AddressComponents.COUNTRY),
            ('country', AddressComponents.COUNTRY),
            ('addr:country', AddressComponents.COUNTRY),
            ('is_in:country', AddressComponents.COUNTRY),
            ('country_region', AddressComponents.COUNTRY_REGION),
            ('addr:country_region', AddressComponents.COUNTRY_REGION),
            ('is_in:country_region', AddressComponents.COUNTRY_REGION),
            ('world_region', AddressComponents.WORLD_REGION),
            ('addr:world_region', AddressComponents.WORLD_REGION),
            ('is_in:world_region', AddressComponents.WORLD_REGION),
            ('phone', EntityDetails.PHONE),
            ('telephone', EntityDetails.PHONE),
            ('sg:phone', EntityDetails.PHONE),
            ('contact:phone', EntityDetails.PHONE),
            ('sg:website', EntityDetails.WEBSITE),
            ('website', EntityDetails.WEBSITE),
            ('contact:website', EntityDetails.WEBSITE),
            ('email', EntityDetails.EMAIL),
            ('contact:email', EntityDetails.EMAIL),
        ])
    )

    @classmethod
    def from_geojson(cls, data):
        properties = data.get('properties')
        properties = {k: safe_decode(v) if k in cls.field_map.aliases else v for k, v in six.iteritems(properties)}
        fields = cls.field_map.replace(properties)
        lon, lat = data.get('geometry', {}).get('coordinates', (None, None))
        try:
            lat, lon = latlon_to_decimal(lat, lon)
        except ValueError:
            lat = lon = None

        if lat is not None:
            fields[Coordinates.LATITUDE] = lat
        if lon is not None:
            fields[Coordinates.LONGITUDE] = lon

        return fields

    @classmethod
    def have_latlon(cls, props):
        return Coordinates.LATITUDE in props and Coordinates.LONGITUDE in props
