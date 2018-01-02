import uuid
from operator import itemgetter


class DedupeResponse(object):
    class classifications:
        NEEDS_REVIEW = 'needs_review'
        LIKELY_DUPE = 'likely_dupe'
        EXACT_DUPE = 'exact_dupe'

    class deduping_types:
        VENUE = 'venue'
        ADDRESS = 'address'

    guid_key = 'lieu:guid'

    '''Similarity threshold above which entities are considered dupes'''
    default_name_dupe_threshold = 0.9

    '''Similarity threshold above where entities need human reviews'''
    default_name_review_threshold = 0.7

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
    def explain_venue_dupe(cls, name_likely_dupe_threshold=default_name_dupe_threshold,
                           name_needs_review_threshold=default_name_review_threshold, with_unit=False):
        return {
            'type': cls.deduping_types.VENUE,
            'name_likely_dupe_threshold': name_likely_dupe_threshold,
            'name_needs_review_threshold': name_needs_review_threshold,
            'with_unit': with_unit,
        }

    @classmethod
    def explain_address_dupe(cls, with_unit=False):
        return {
            'type': cls.deduping_types.ADDRESS,
            'with_unit': with_unit
        }

    @classmethod
    def add_possible_dupe(cls, response, value, classification, name_similarity, is_canonical, explain=None):
        response.setdefault('same_as', [])
        same_as = {
            'is_canonical': is_canonical,
            'name_similarity': similarity,
            'classification': classification,
            'object': value,
        }
        if explain:
            same_as['explain'] = explain
        response['same_as'].append(same_as)

        return response

    @classmethod
    def add_possible_dupe(cls, response, value, classification, is_canonical, similarity, explain=None):
        if classification in (cls.classifications.EXACT_DUPE, cls.classifications.LIKELY_DUPE):
            key = 'same_as'
        elif classification == cls.classifications.NEEDS_REVIEW:
            key = 'possibly_same_as'
        else:
            return response

        response.setdefault(key, [])
        dupe = {
            'is_canonical': is_canonical,
            'classification': classification,
            'object': value,
        }

        if similarity is not None:
            dupe.update(similarity=min(similarity, 1.0))

        if explain:
            dupe['explain'] = explain
        response[key].append(dupe)

        return response

    @classmethod
    def create(cls, value, is_dupe=False, add_random_guid=False, same_as=[], explain=None):
        response = cls.base_response(value, is_dupe=is_dupe)
        if add_random_guid:
            cls.add_random_guid(value)
        for other, classification, is_canonical, similarity in same_as:
            cls.add_possible_dupe(response, other, classification, is_canonical, similarity, explain=explain)
            if add_random_guid:
                cls.add_random_guid(other)
        if 'possibly_same_as' in response:
            response['possibly_same_as'] = sorted(response['possibly_same_as'], key=itemgetter('similarity'), reverse=True)
        return response
