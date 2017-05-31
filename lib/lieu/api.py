

class DedupeResponse(object):
    class classifications:
        LIKELY_DUPE = 'likely_dupe'
        EXACT_DUPE = 'exact_dupe'

    @classmethod
    def base_response(cls, guid, value, is_dupe):
        return {
            'guid': guid,
            'object': value,
            'is_dupe': is_dupe,
        }

    @classmethod
    def add_same_as(cls, response, guid, value, classification, is_canonical, explain=()):
        response['same_as'].setdefault([])
        response['same_as'].append({
            'is_canonical': is_canonical,
            'guid': guid,
            'classification': classification,
            'object': value,
            'explain': list(explain),
        })
