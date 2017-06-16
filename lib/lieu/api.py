import uuid

from lieu.dedupe import NameDeduper


class DedupeResponse(object):
    class classifications:
        LIKELY_DUPE = 'likely_dupe'
        EXACT_DUPE = 'exact_dupe'

    class deduping_types:
        VENUE = 'venue'
        ADDRESS = 'address'

    guid_key = 'lieu:guid'

    @classmethod
    def random_guid(cls):
        return uuid.uuid4().get_hex()

    @classmethod
    def add_guid(cls, value, guid):
        props = value.get('properties', {})
        if cls.guid_key not in props:
            props[cls.guid_key] = guid
        return value

    @classmethod
    def add_random_guid(cls, value):
        props = value.get('properties', {})
        if cls.guid_key not in props:
            props[cls.guid_key] = cls.random_guid()
        return value

    @classmethod
    def base_response(cls, value, is_dupe):
        return {
            'object': value,
            'is_dupe': is_dupe,
        }

    @classmethod
    def explain_venue_dupe(cls, name_dupe_threshold=NameDeduper.default_dupe_threshold, with_unit=False):
        return {
            'type': cls.deduping_types.VENUE,
            'name_dupe_threshold': name_dupe_threshold,
            'with_unit': with_unit,
        }

    @classmethod
    def explain_address_dupe(cls, with_unit=False):
        return {
            'type': cls.deduping_types.ADDRESS,
            'with_unit': with_unit
        }

    @classmethod
    def add_same_as(cls, response, value, classification, is_canonical, explain=None):
        response.setdefault('same_as', [])
        same_as = {
            'is_canonical': is_canonical,
            'classification': classification,
            'object': value,
        }
        if explain:
            same_as['explain'] = explain
        response['same_as'].append(same_as)

        return response
