import fuzzy
import geohash
import re
import six

from postal.expand import expand_address, ADDRESS_NAME, ADDRESS_STREET, ADDRESS_UNIT, ADDRESS_LEVEL, ADDRESS_HOUSE_NUMBER

from lieu.address import AddressComponents, VenueDetails, Coordinates
from lieu.api import DedupeResponse
from lieu.similarity import ordered_word_count, soft_tfidf_similarity, jaccard_similarity
from lieu.encoding import safe_encode, safe_decode
from lieu.floats import isclose

double_metaphone = fuzzy.DMetaphone()
whitespace_regex = re.compile('[\s]+')


class AddressDeduper(object):
    DEFAULT_GEOHASH_PRECISION = 7

    @classmethod
    def component_equals(cls, c1, c2, component, no_whitespace=True):
        if not c1 or not c2:
            return False

        c1 = safe_decode(c1)
        c2 = safe_decode(c2)
        if no_whitespace and whitespace_regex.sub(u'', c1.lower()) == whitespace_regex.sub(u'', c2.lower()):
            return True

        expansions1 = expand_address(c1, address_components=component)
        expansions2 = expand_address(c2, address_components=component)

        if not no_whitespace:
            set_expansions1 = set(expansions1)
            set_expansions2 = set(expansions2)
        else:
            set_expansions1 = set([whitespace_regex.sub(u'', e1) for e1 in expansions1])
            set_expansions2 = set([whitespace_regex.sub(u'', e2) for e2 in expansions2])

        return len(set_expansions1 & set_expansions2) > 0

    @classmethod
    def is_address_dupe(cls, a1, a2):
        a1_street = a1.get(AddressComponents.STREET)
        a2_street = a2.get(AddressComponents.STREET)

        a1_house_number = a1.get(AddressComponents.HOUSE_NUMBER)
        a2_house_number = a2.get(AddressComponents.HOUSE_NUMBER)

        if not a1_street or not a2_street or not a1_house_number or not a2_house_number:
            return None

        same_street = cls.component_equals(a1_street, a2_street, ADDRESS_STREET)
        same_house_number = cls.component_equals(a1_house_number, a2_house_number, ADDRESS_HOUSE_NUMBER)

        return same_street and same_house_number

    @classmethod
    def is_sub_building_dupe(cls, a1, a2):
        for key, component in ((AddressComponents.UNIT, ADDRESS_UNIT), (AddressComponents.FLOOR, ADDRESS_LEVEL)):
            a1_field = a1.get(key)
            a2_field = a2.get(key)

            if a1_field and a2_field:
                if not cls.component_equals(a1_field, a2_field, component):
                    return False
            elif a1_field or a2_field:
                return False
        return True

    @classmethod
    def is_dupe(cls, a1, a2, with_unit=True):
        return cls.is_address_dupe(a1, a2) and (not with_unit or cls.is_sub_building_dupe(a1, a2))

    @classmethod
    def component_expansions(cls, address):
        street = address.get(AddressComponents.STREET)
        house_number = address.get(AddressComponents.HOUSE_NUMBER)

        if not (street and house_number):
            return ()

        street_expansions = expand_address(street, address_components=ADDRESS_STREET)
        house_number_expansions = expand_address(house_number, address_components=ADDRESS_HOUSE_NUMBER)

        return street_expansions, house_number_expansions

    @classmethod
    def near_dupe_hashes(cls, address, geohash_precision=DEFAULT_GEOHASH_PRECISION):
        address_expansions = cls.component_expansions(address)

        lat = address.get(Coordinates.LATITUDE)
        lon = address.get(Coordinates.LONGITUDE)
        if lat is None or lon is None or (isclose(lat, 0.0) and isclose(lon, 0.0)) or lat >= 90.0 or lat <= -90.0 or not any(address_expansions):
            return

        geo = geohash.encode(lat, lon)[:geohash_precision]
        geohash_neighbors = [geo] + geohash.neighbors(geo)

        for keys in six.itertools.product(geohash_neighbors, *address_expansions):
            yield u'|'.join(keys)


class NameDeduper(object):
    '''
    Base class for deduping geographic entity names e.g. for matching names
    from different databases (concordances).

    By default uses Soft TFIDF similarity (see similarity.py)
    for non-ideographic names and Jaccard similarity with word frequencies
    for ideographic names.

    See class attributes for options.
    '''

    ignore_parentheticals = True

    @classmethod
    def tokenize(cls, s):
        return s.split()

    paren_regex = re.compile('\(.*\)')

    @classmethod
    def content_tokens(cls, s):
        if cls.ignore_parentheticals:
            tokens = cls.paren_regex.sub(u'', s)
        return cls.tokenize(s.lower())

    @classmethod
    def compare_ideographs(cls, s1, s2):
        tokens1 = cls.content_tokens(s1)
        tokens2 = cls.content_tokens(s2)

        if u''.join(tokens1) == u''.join(tokens2):
            return 1.0
        else:
            # Many Han/Hangul characters are common, shouldn't use IDF
            return jaccard_similarity(tokens1, tokens2)

    @classmethod
    def compare_in_memory(cls, tokens1, tokens2, tfidf):
        # Test exact equality, also handles things like Cabbage Town == Cabbagetown
        token_counts1 = ordered_word_count(tokens1)
        token_counts2 = ordered_word_count(tokens2)

        tfidf1 = tfidf.tfidf_vector(token_counts1)
        tfidf2 = tfidf.tfidf_vector(token_counts2)

        tfidf1_norm = tfidf.normalized_tfidf_vector(tfidf1)
        tfidf2_norm = tfidf.normalized_tfidf_vector(tfidf2)

        return soft_tfidf_similarity(tfidf1_norm, tfidf2_norm)


class VenueDeduper(AddressDeduper):
    DEFAULT_GEOHASH_PRECISION = 6

    @classmethod
    def name_similarity(cls, a1_name, a2_name, tfidf):
        a1_name_tokens = NameDeduper.content_tokens(a1_name)
        a2_name_tokens = NameDeduper.content_tokens(a2_name)

        return NameDeduper.compare_in_memory(a1_name_tokens, a2_name_tokens, tfidf)

    @classmethod
    def dupe_class_and_sim(cls, a1, a2, tfidf=None, name_dupe_threshold=DedupeResponse.default_name_dupe_threshold,
                           name_review_threshold=DedupeResponse.default_name_review_threshold, with_unit=False):
        a1_name = a1.get(AddressComponents.NAME)
        a2_name = a2.get(AddressComponents.NAME)
        if not a1_name or not a2_name:
            return None, 0.0

        same_address = cls.is_address_dupe(a1, a2)
        if not same_address:
            return None, 0.0

        if with_unit:
            same_unit = cls.is_sub_building_dupe(a1, a2)
            if not same_unit:
                return None, 0.0

        exact_same_name = cls.is_exact_name_dupe(a1_name, a2_name)
        if exact_same_name:
            return DedupeResponse.classifications.EXACT_DUPE, 1.0
        elif tfidf:
            name_sim = cls.name_similarity(a1_name, a2_name, tfidf)
            if name_sim >= name_dupe_threshold:
                return DedupeResponse.classifications.LIKELY_DUPE, name_sim
            elif name_sim >= name_review_threshold:
                return DedupeResponse.classifications.NEEDS_REVIEW, name_sim

        return None, 0.0

    @classmethod
    def is_dupe(cls, a1, a2, tfidf=None, name_dupe_threshold=DedupeResponse.default_name_dupe_threshold, with_unit=False):
        dupe_class, sim = cls.dupe_class_and_sim(a1, a2, tfidf=tfidf, name_dupe_threshold=name_dupe_threshold, with_unit=with_unit)
        return dupe_class in (DedupeResponse.classifications.EXACT_DUPE, DedupeResponse.classifications.LIKELY_DUPE)

    @classmethod
    def is_exact_name_dupe(cls, name1, name2):
        return cls.component_equals(name1, name2, ADDRESS_NAME)

    @classmethod
    def name_word_hashes(cls, name):
        name_expanded_words = set()

        for n in expand_address(name, address_components=ADDRESS_NAME):
            tokens = NameDeduper.tokenize(n)
            for t in tokens:
                dm = set([e for e in double_metaphone(safe_encode(t)) if e is not None])
                if dm:
                    name_expanded_words |= dm
                else:
                    name_expanded_words.add(t)

        return name_expanded_words

    @classmethod
    def component_expansions(cls, address):
        name = address.get(AddressComponents.NAME)

        if not name:
            return ()

        expansions = super(cls, VenueDeduper).component_expansions(address)
        if not expansions:
            return ()

        name_expanded_words = cls.name_word_hashes(name)

        return (list(name_expanded_words),) + expansions
