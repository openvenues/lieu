import uuid
from operator import itemgetter
from postal.dedupe import duplicate_status


class Dupe(object):
    class classifications:
        NEEDS_REVIEW = 'needs_review'
        LIKELY_DUPE = 'likely_dupe'
        EXACT_DUPE = 'exact_dupe'

    dupe_class_map = {
        duplicate_status.LIKELY_DUPLICATE: classifications.LIKELY_DUPE,
        duplicate_status.EXACT_DUPLICATE: classifications.EXACT_DUPE,
        duplicate_status.NEEDS_REVIEW: classifications.NEEDS_REVIEW,
    }

    def __init__(self, status, sim):
        self.status = status
        self.sim = sim

    def __eq__(self, other):
        return (self.status, self.sim) == (other.status, other.sim)

    def __ne__(self, other):
        return (self.status, self.sim) != (other.status, other.sim)

    def __gt__(self, other):
        return (self.status, self.sim) > (other.status, other.sim)

    def __ge__(self, other):
        return (self.status, self.sim) >= (other.status, other.sim)

    def __lt__(self, other):
        return (self.status, self.sim) < (other.status, other.sim)

    def __le__(self, other):
        return (self.status, self.sim) <= (other.status, other.sim)

    def __repr__(self):
        return u'Dupe(status={}, sim={})'.format(self.dupe_class_map.get(self.status),
                                                 self.sim)


NULL_DUPE = Dupe(duplicate_status.NON_DUPLICATE, sim=0.0)


class DedupeResponse(object):

    @classmethod
    def string_dupe_class(cls, dupe_class):
        return Dupe.dupe_class_map.get(dupe_class)

    class deduping_types:
        NAME_ADDRESS = 'name+address'
        ADDRESS = 'address'

    guid_key = 'lieu:guid'

    '''Similarity threshold above which entities are considered dupes'''
    default_name_dupe_threshold = 0.9

    '''Similarity threshold above where entities need human reviews'''
    default_name_review_threshold = 0.7

    @classmethod
    def random_guid(cls):
        return str(uuid.uuid4())

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
    def explain_name_address_dupe(cls, name_likely_dupe_threshold=default_name_dupe_threshold,
                                  name_needs_review_threshold=default_name_review_threshold, with_unit=False):
        return {
            'type': cls.deduping_types.NAME_ADDRESS,
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
    def add_possible_dupe(cls, response, value, dupe, is_canonical, explain=None):
        if dupe.status in (Dupe.classifications.EXACT_DUPE, Dupe.classifications.LIKELY_DUPE):
            key = 'same_as'
        elif dupe.status == Dupe.classifications.NEEDS_REVIEW:
            key = 'possibly_same_as'
        else:
            return response

        response.setdefault(key, [])
        dupe_response = {
            'is_canonical': is_canonical,
            'classification': dupe.status,
            'object': value,
        }

        if dupe.sim is not None:
            dupe_response.update(similarity=min(dupe.sim, 1.0))

        if explain:
            dupe_response['explain'] = explain
        response[key].append(dupe_response)

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
