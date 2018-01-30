import fuzzy
import geohash
import re
import six

import phonenumbers

from postal.near_dupe import near_dupe_hashes
from postal.dedupe import place_languages, duplicate_status, is_name_duplicate, is_street_duplicate, is_house_number_duplicate, is_po_box_duplicate, is_unit_duplicate, is_floor_duplicate, is_postal_code_duplicate, is_toponym_duplicate, is_name_duplicate_fuzzy, is_street_duplicate_fuzzy
from postal.normalize import normalized_tokens
from postal.tokenize import tokenize
from postal.token_types import token_types

from lieu.address import AddressComponents, EntityDetails, Coordinates
from lieu.api import DedupeResponse
from lieu.similarity import ordered_word_count
from lieu.word_index import WordIndex

whitespace_regex = re.compile('[\s]+')


class AddressDeduper(object):
    DEFAULT_GEOHASH_PRECISION = 7

    address_only_keys = True
    name_only_keys = False
    name_and_address_keys = False
    with_name = False

    @classmethod
    def address_dupe_status(cls, a1, a2, languages=None, fuzzy_street_name=False):
        a1_street = a1.get(AddressComponents.STREET)
        a2_street = a2.get(AddressComponents.STREET)

        if a1_street:
            a1_street = a1_street.strip()
        if a2_street:
            a2_street = a2_street.strip()

        a1_house_number = a1.get(AddressComponents.HOUSE_NUMBER)
        a2_house_number = a2.get(AddressComponents.HOUSE_NUMBER)

        if a1_house_number:
            a1_house_number = a1_house_number.strip()
        if a2_house_number:
            a2_house_number = a2_house_number.strip()

        if (a1_street and not a2_street) or (a2_street and not a1_street):
            return duplicate_status.NON_DUPLICATE

        if (a1_house_number and not a2_house_number) or (a2_house_number and not a1_house_number):
            return duplicate_status.NON_DUPLICATE

        have_street = a1_street and a2_street
        same_street = False
        street_status = duplicate_status.NON_DUPLICATE

        if have_street:
            street_status = is_street_duplicate(a1_street, a2_street, languages=languages)
            same_street = street_status in (duplicate_status.EXACT_DUPLICATE, duplicate_status.LIKELY_DUPLICATE)
            if not same_street and fuzzy_street_name:
                a1_street_tokens = Name.content_tokens(a1_street)
                a1_scores_norm = WordIndex.normalized_vector([1] * len(a1_street_tokens))
                a2_street_tokens = Name.content_tokens(a2_street)
                a2_scores_norm = WordIndex.normalized_vector([1] * len(a2_street_tokens))
                street_status, street_sim = is_street_duplicate_fuzzy(a1_street_tokens, a1_scores_norm, a2_street_tokens, a2_scores_norm, languages=languages)
                same_street = street_status in (duplicate_status.EXACT_DUPLICATE, duplicate_status.LIKELY_DUPLICATE)
            if not same_street:
                return duplicate_status.NON_DUPLICATE

        have_house_number = a1_house_number and a2_house_number
        same_house_number = False
        house_number_status = duplicate_status.NON_DUPLICATE

        if have_house_number:
            house_number_status = is_house_number_duplicate(a1_house_number, a2_house_number, languages=languages)
            same_house_number = house_number_status == duplicate_status.EXACT_DUPLICATE
            if not same_house_number:
                return duplicate_status.NON_DUPLICATE

        if not have_house_number and not have_street:
            return duplicate_status.NON_DUPLICATE

        if have_street and same_street and (same_house_number or not have_house_number):
            return street_status
        elif have_house_number and same_house_number:
            return house_number_status
        elif have_street and same_street:
            return street_status

        return duplicate_status.NON_DUPLICATE

    @classmethod
    def is_address_dupe(cls, a1, a2, languages=None, fuzzy_street_name=False):
        return cls.address_dupe_status(a1, a2, languages=languages, fuzzy_street_name=fuzzy_street_name) in (duplicate_status.EXACT_DUPLICATE, duplicate_status.LIKELY_DUPLICATE)

    @classmethod
    def one_address_is_missing_field(cls, field, a1, a2):
        a1_field = a1.get(field, u'').strip()
        a2_field = a2.get(field, u'').strip()
        return bool(a1_field) != bool(a2_field)

    @classmethod
    def is_sub_building_dupe(cls, a1, a2, languages=None):
        a1_unit = a1.get(AddressComponents.UNIT)
        a2_unit = a2.get(AddressComponents.UNIT)

        have_unit = a1_unit is not None and a2_unit is not None
        same_unit = False

        if have_unit:
            unit_status = is_unit_duplicate(a1_unit, a2_unit, languages=languages)
            same_unit = unit_status in (duplicate_status.EXACT_DUPLICATE, duplicate_status.LIKELY_DUPLICATE)
            if not same_unit:
                return False

        a1_floor = a1.get(AddressComponents.FLOOR)
        a2_floor = a2.get(AddressComponents.FLOOR)

        have_floor = a1_floor is not None and a2_floor is not None
        same_floor = False

        if have_floor:
            floor_status = is_floor_duplicate(a1_floor, a2_floor, languages=languages)
            same_floor = floor_status in (duplicate_status.EXACT_DUPLICATE, duplicate_status.LIKELY_DUPLICATE)

        if have_floor and not same_floor:
            return False

        return True

    @classmethod
    def combined_languages(cls, languages1, languages2):
        languages_set1 = set(languages1)

        return languages1 + [lang for lang in languages2 if lang not in languages_set1]

    @classmethod
    def combined_place_languages(cls, *addresses):
        languages = []
        languages_set = set()
        for address in addresses:
            keys, values = cls.address_labels_and_values(address)
            if not (keys and values):
                continue
            langs = place_languages(keys, values) or []
            new_languages = [lang for lang in langs if lang not in languages_set]
            languages.extend(new_languages)
            languages_set.update(new_languages)

        return languages

    @classmethod
    def address_minus_name(cls, address):
        return {k: v for k, v in six.iteritems(address) if k != AddressComponents.NAME}

    @classmethod
    def address_languages(cls, address):
        addresses = [address]
        if AddressComponents.NAME in address:
            addresses.append(cls.address_minus_name(address))

        return cls.combined_place_languages(*addresses)

    @classmethod
    def is_dupe(cls, a1, a2, with_unit=True, fuzzy_street_name=False):
        languages = cls.combined_place_languages(cls.address_minus_name(a1), cls.address_minus_name(a2))

        return cls.is_address_dupe(a1, a2, languages=languages) and (not with_unit or cls.is_sub_building_dupe(a1, a2, languages=languages, fuzzy_street_name=fuzzy_street_name))

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
                         geohash_precision=None,
                         name_and_address_keys=None,
                         name_only_keys=None,
                         address_only_keys=None):
        lat = address.get(Coordinates.LATITUDE)
        lon = address.get(Coordinates.LONGITUDE)
        if lat is None or lon is None:
            lat = 0.0
            lon = 0.0
            with_latlon = False

        if geohash_precision is None:
            geohash_precision = cls.DEFAULT_GEOHASH_PRECISION

        if languages is None:
            languages = cls.address_languages(address)

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
        return [t for t, c in normalized_tokens(name) if c in token_types.WORD_TOKEN_TYPES or c in token_types.NUMERIC_TOKEN_TYPES or c in (token_types.AMPERSAND, token_types.POUND)]


class PhoneNumberDeduper(object):
    @classmethod
    def have_phone_numbers(cls, a1, a2):
        num1 = a1.get(EntityDetails.PHONE, u'').strip()
        num2 = a2.get(EntityDetails.PHONE, u'').strip()
        return bool(num1) and bool(num2)

    @classmethod
    def is_phone_number_dupe(cls, a1, a2):
        num1 = a1.get(EntityDetails.PHONE)
        num2 = a2.get(EntityDetails.PHONE)

        country_code1 = a1.get(AddressComponents.COUNTRY)
        country_code2 = a2.get(AddressComponents.COUNTRY)

        if country_code1 and country_code2 and country_code1 != country_code2:
            return False

        country_code = country_code1 or country_code2

        try:
            p1 = phonenumbers.parse(num1, region=country_code)
            p2 = phonenumbers.parse(num2, region=country_code)
        except phonenumbers.NumberParseException:
            return False

        return p1.country_code == p2.country_code and p1.national_number == p2.national_number

    @classmethod
    def revised_dupe_class(cls, dupe_class, a1, a2):
        have_phone_number = cls.have_phone_numbers(a1, a2)
        same_phone_number = cls.is_phone_number_dupe(a1, a2)
        different_phone_number = have_phone_number and not same_phone_number

        if dupe_class == duplicate_status.NEEDS_REVIEW and same_phone_number:
            dupe_class = duplicate_status.LIKELY_DUPLICATE
        elif dupe_class == duplicate_status.LIKELY_DUPLICATE and different_phone_number:
            dupe_class = duplicate_status.NEEDS_REVIEW

        return dupe_class


class NameAddressDeduper(AddressDeduper):
    DEFAULT_GEOHASH_PRECISION = 6

    address_only_keys = False
    name_only_keys = False
    name_and_address_keys = True
    with_name = True

    @classmethod
    def word_scores_normalized(cls, tokens, word_index):
        vector = word_index.vector(tokens)
        return word_index.normalized_vector(vector)

    dupe_class_map = {
        duplicate_status.LIKELY_DUPLICATE: DedupeResponse.classifications.LIKELY_DUPE,
        duplicate_status.EXACT_DUPLICATE: DedupeResponse.classifications.EXACT_DUPE,
        duplicate_status.NEEDS_REVIEW: DedupeResponse.classifications.NEEDS_REVIEW,
    }

    @classmethod
    def string_dupe_class(cls, dupe_class):
        return cls.dupe_class_map.get(dupe_class)

    @classmethod
    def name_dupe_fuzzy(cls, a1_name_tokens, a1_scores_norm, a2_name_tokens, a2_scores_norm, languages=None, likely_dupe_threshold=DedupeResponse.default_name_dupe_threshold,
                        needs_review_threshold=DedupeResponse.default_name_review_threshold):
        if not a1_name_tokens or not a2_name_tokens:
            return None, 0.0

        return is_name_duplicate_fuzzy(a1_name_tokens, a1_scores_norm, a2_name_tokens, a2_scores_norm, languages=languages,
                                       likely_dupe_threshold=likely_dupe_threshold, needs_review_threshold=needs_review_threshold)

    @classmethod
    def name_dupe_similarity(cls, a1_name, a2_name, word_index, languages=None, likely_dupe_threshold=DedupeResponse.default_name_dupe_threshold,
                             needs_review_threshold=DedupeResponse.default_name_review_threshold):
        a1_name_tokens = Name.content_tokens(a1_name)
        a2_name_tokens = Name.content_tokens(a2_name)
        if not a1_name_tokens or not a2_name_tokens:
            return None, 0.0

        a1_scores = cls.word_scores_normalized(a1_name_tokens, word_index)
        a2_scores = cls.word_scores_normalized(a2_name_tokens, word_index)

        return is_name_duplicate_fuzzy(a1_name_tokens, a1_scores, a2_name_tokens, a2_scores, languages=languages,
                                       likely_dupe_threshold=likely_dupe_threshold, needs_review_threshold=needs_review_threshold)

    @classmethod
    def dupe_class_and_sim(cls, a1, a2, word_index=None, likely_dupe_threshold=DedupeResponse.default_name_dupe_threshold,
                           needs_review_threshold=DedupeResponse.default_name_review_threshold, with_unit=False, with_phone_number=True, fuzzy_street_name=False):
        a1_name = a1.get(AddressComponents.NAME)
        a2_name = a2.get(AddressComponents.NAME)
        if not a1_name or not a2_name:
            return None, 0.0

        a1_languages = cls.address_languages(a1)
        a2_languages = cls.address_languages(a2)

        languages = cls.combined_languages(a1_languages, a2_languages)

        same_address = cls.is_address_dupe(a1, a2, languages=languages, fuzzy_street_name=fuzzy_street_name)
        if not same_address:
            return None, 0.0

        if with_unit:
            same_unit = cls.is_sub_building_dupe(a1, a2, languages=languages)
            if not same_unit:
                return None, 0.0

        name_dupe_class = cls.name_dupe_status(a1_name, a2_name, languages=languages)
        if name_dupe_class == duplicate_status.EXACT_DUPLICATE:
            return DedupeResponse.classifications.EXACT_DUPE, 1.0
        elif word_index:
            name_fuzzy_dupe_class, name_sim = cls.name_dupe_similarity(a1_name, a2_name, word_index=word_index, languages=languages)

            if with_phone_number:
                name_fuzzy_dupe_class = PhoneNumberDeduper.revised_dupe_class(name_fuzzy_dupe_class, a1, a2)
            if name_fuzzy_dupe_class >= name_dupe_class:
                return cls.string_dupe_class(name_fuzzy_dupe_class), name_sim

        if name_dupe_class == duplicate_status.LIKELY_DUPLICATE:
            name_sim = likely_dupe_threshold
        elif name_dupe_class == duplicate_status.NEEDS_REVIEW:
            name_sim = needs_review_threshold
        else:
            return None, 0.0

        return cls.string_dupe_class(name_dupe_class), name_sim

    @classmethod
    def is_dupe(cls, a1, a2, index=None, name_dupe_threshold=DedupeResponse.default_name_dupe_threshold, with_unit=False, fuzzy_street_name=False):
        dupe_class, sim = cls.dupe_class_and_sim(a1, a2, index=index, name_dupe_threshold=name_dupe_threshold, with_unit=with_unit, fuzzy_street_name=fuzzy_street_name)
        return dupe_class in (DedupeResponse.classifications.EXACT_DUPE, DedupeResponse.classifications.LIKELY_DUPE)

    @classmethod
    def name_dupe_status(cls, name1, name2, languages=None):
        return is_name_duplicate(name1, name2, languages=languages)
