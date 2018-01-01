import fuzzy
import geohash
import re
import six

from postal.near_dupe import near_dupe_hashes
from postal.dedupe import place_languages, duplicate_status, is_name_duplicate, is_street_duplicate, is_house_number_duplicate, is_po_box_duplicate, is_unit_duplicate, is_floor_duplicate, is_postal_code_duplicate, is_toponym_duplicate, is_name_duplicate_fuzzy, is_street_duplicate
from postal.tokenize import tokenize
from postal.token_types import token_types

from lieu.address import AddressComponents, VenueDetails, Coordinates
from lieu.api import DedupeResponse
from lieu.similarity import ordered_word_count, soft_tfidf_similarity, jaccard_similarity
from lieu.encoding import safe_encode, safe_decode
from lieu.floats import isclose

whitespace_regex = re.compile('[\s]+')


class AddressDeduper(object):
    DEFAULT_GEOHASH_PRECISION = 7

    address_only_keys = True
    name_only_keys = False
    name_and_address_keys = False
    with_name = False

    @classmethod
    def is_address_dupe(cls, a1, a2, languages=None):
        a1_street = a1.get(AddressComponents.STREET)
        a2_street = a2.get(AddressComponents.STREET)

        a1_house_number = a1.get(AddressComponents.HOUSE_NUMBER)
        a2_house_number = a2.get(AddressComponents.HOUSE_NUMBER)

        if not a1_street or not a2_street or not a1_house_number or not a2_house_number:
            return None

        same_street = is_street_duplicate(a1_street, a2_street, languages=languages)
        same_house_number = is_house_number_duplicate(a1_house_number, a2_house_number, languages=languages)

        return same_street and same_house_number

    @classmethod
    def is_sub_building_dupe(cls, a1, a2, languages=None):
        a1_unit = a1.get(AddressComponents.UNIT)
        a2_unit = a2.get(AddressComponents.UNIT)

        if a1_unit and a2_unit and not is_unit_duplicate(a1_unit, a2_unit, languages=languages):
            return False
        elif a1_unit or a2_unit:
            return False

        a2_floor = a1.get(AddressComponents.FLOOR)
        a2_floor = a2.get(AddressComponents.FLOOR)

        if a1_floor and a2_floor and not is_floor_duplicate(a1_floor, a2_floor, languages=languages):
            return False
        elif a1_floor or a2_floor:
            return False

        return True

    @classmethod
    def combined_languages(cls, languages1, languages2):
        languages_set1 = set(languages1)

        return languages1 + [lang for lang in languages2 if lang not in languages_set1]

    @classmethod
    def combined_place_languages(cls, a1, a2):
        a1_keys, a1_values = cls.address_labels_and_values(a1)
        a1_languages = place_languages(a1_keys, a1_values) or []

        a2_keys, a2_values = cls.address_labels_and_values(a2)
        a2_languages = place_languages(a2_keys, a2_values) or []

        return cls.combined_languages(a1_languages, a2_languages)

    @classmethod
    def is_dupe(cls, a1, a2, with_unit=True):
        languages = cls.combined_place_languages(a1, a2)

        return cls.is_address_dupe(a1, a2, languages=languages) and (not with_unit or cls.is_sub_building_dupe(a1, a2, languages=languages))

    @classmethod
    def address_labels_and_values(cls, address):
        string_address = {k: v for k, v in six.iteritems(address) if isinstance(v, six.string_types) and v.strip()}

        return string_address.keys(), string_address.values()

    @classmethod
    def near_dupe_hashes(cls, address, languages=None,
                         with_address=True,
                         with_unit=False,
                         with_city_or_equivalent=False,
                         with_small_containing_boundaries=False,
                         with_postal_code=False,
                         with_latlon=True,
                         geohash_precision=DEFAULT_GEOHASH_PRECISION,
                         name_and_address_keys=None,
                         name_only_keys=None,
                         address_only_keys=None):
        lat = address.get(Coordinates.LATITUDE)
        lon = address.get(Coordinates.LONGITUDE)
        if lat is None or lon is None:
            lat = 0.0
            lon = 0.0
            with_latlon = False

        labels, values = cls.address_labels_and_values(address)

        if name_only_keys is None:
            name_only_keys = cls.name_only_keys

        if name_and_address_keys is None:
            name_and_address_keys = cls.name_and_address_keys

        if address_only_keys is None:
            address_only_keys = cls.address_only_keys

        return near_dupe_hashes(labels, values, languages=languages,
                                with_name=cls.with_name,
                                with_address=with_address,
                                with_unit=with_unit,
                                with_city_or_equivalent=with_city_or_equivalent,
                                with_small_containing_boundaries=with_small_containing_boundaries,
                                with_postal_code=with_postal_code,
                                with_latlon=with_latlon,
                                latitude=lat,
                                longitude=lon,
                                geohash_precision=geohash_precision,
                                name_and_address_keys=name_and_address_keys,
                                name_only_keys=name_only_keys,
                                address_only_keys=cls.address_only_keys)


class Name(object):
    @classmethod
    def content_tokens(cls, name):
        return [t for t, c in tokenize(name) if c in token_types.WORD_TOKEN_TYPES or c in token_types.NUMERIC_TOKEN_TYPES]


class VenueDeduper(AddressDeduper):
    DEFAULT_GEOHASH_PRECISION = 6

    address_only_keys = False
    name_only_keys = False
    name_and_address_keys = True
    with_name = True

    @classmethod
    def tfidf_vector(cls, tokens, tfidf_index):
        token_counts = ordered_word_count(tokens1)
        return tfidf_index.tfidf_vector(token_counts)

    @classmethod
    def tfidf_vector_normalized(cls, tokens, tfidf_index):
        tfidf = cls.tfidf_vector(tokens, tfidf_index)
        return tfidf.normalized_tfidf_vector(tfidf)

    dupe_class_map = {
        duplicate_status.LIKELY_DUPLICATE: DedupeResponse.classifications.LIKELY_DUPE,
        duplicate_status.EXACT_DUPLICATE: DedupeResponse.classifications.EXACT_DUPE,
        duplicate_status.NEEDS_REVIEW: DedupeResponse.classifications.NEEDS_REVIEW,
    }

    @classmethod
    def string_dupe_class(cls, dupe_class):
        return cls.dupe_class_map.get(dupe_class)

    @classmethod
    def name_dupe_similarity(cls, a1_name, a2_name, tfidf, languages=None, likely_dupe_threshold=DedupeResponse.default_name_dupe_threshold,
                             needs_review_threshold=DedupeResponse.default_name_review_threshold):
        a1_name_tokens = Name.content_tokens(a1_name)
        a2_name_tokens = Name.content_tokens(a2_name)
        if not a1_name_tokens or not a2_name_tokens:
            return None, 0.0

        a1_tfidf_norm = cls.tfidf_vector_normalized(a1_name_tokens, tfidf)
        a2_tfidf_norm = cls.tfidf_vector_normalized(a2_name_tokens, tfidf)

        return is_name_duplicate_fuzzy(a1_name_tokens, a1_tfidf_norm, a2_name_tokens, a2_tfidf_norm, languages=languages,
                                       likely_dupe_threshold=likely_dupe_threshold, needs_review_threshold=needs_review_threshold)

    @classmethod
    def dupe_class_and_sim(cls, a1, a2, tfidf=None, name_dupe_threshold=DedupeResponse.default_name_dupe_threshold,
                           name_review_threshold=DedupeResponse.default_name_review_threshold, with_unit=False):
        a1_name = a1.get(AddressComponents.NAME)
        a2_name = a2.get(AddressComponents.NAME)
        if not a1_name or not a2_name:
            return None, 0.0

        languages = cls.combined_place_languages(a1, a2)

        same_address = cls.is_address_dupe(a1, a2, languages=languages)
        if not same_address:
            return None, 0.0

        if with_unit:
            same_unit = cls.is_sub_building_dupe(a1, a2, languages=languages)
            if not same_unit:
                return None, 0.0

        exact_same_name = cls.is_exact_name_dupe(a1_name, a2_name, languages=languages)
        if exact_same_name:
            return DedupeResponse.classifications.EXACT_DUPE, 1.0
        elif tfidf:
            dupe_class, name_sim = cls.name_dupe_similarity(a1_name, a2_name, tfidf)
            return cls.string_dupe_class(dupe_class), name_sim

        return None, 0.0

    @classmethod
    def is_dupe(cls, a1, a2, tfidf=None, name_dupe_threshold=DedupeResponse.default_name_dupe_threshold, with_unit=False):
        dupe_class, sim = cls.dupe_class_and_sim(a1, a2, tfidf=tfidf, name_dupe_threshold=name_dupe_threshold, with_unit=with_unit)
        return dupe_class in (DedupeResponse.classifications.EXACT_DUPE, DedupeResponse.classifications.LIKELY_DUPE)

    @classmethod
    def is_exact_name_dupe(cls, name1, name2, languages=None):
        return is_name_duplicate(name1, name2, languages=languages)
