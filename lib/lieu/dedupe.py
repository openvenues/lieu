import re
import six

import phonenumbers

from postal.near_dupe import near_dupe_hashes
from postal.dedupe import place_languages, duplicate_status, is_name_duplicate, is_street_duplicate, is_house_number_duplicate, is_po_box_duplicate, is_unit_duplicate, is_floor_duplicate, is_postal_code_duplicate, is_toponym_duplicate, is_name_duplicate_fuzzy, is_street_duplicate_fuzzy
from postal.normalize import normalized_tokens, DEFAULT_STRING_OPTIONS, NORMALIZE_STRING_REPLACE_NUMEX
from postal.tokenize import tokenize
from postal.token_types import token_types

from lieu.address import AddressComponents, EntityDetails, Coordinates
from lieu.api import Dupe, DedupeResponse, NULL_DUPE
from lieu.encoding import safe_decode
from lieu.word_index import WordIndex


whitespace_regex = re.compile('[\\s]+')


DEFAULT_LANGUAGES = ['en']


def combined_languages(languages1, languages2):
    languages_set1 = set(languages1)

    return languages1 + [lang for lang in languages2 if lang not in languages_set1]


class StreetDeduper(object):
    @classmethod
    def street_dupe_status(cls, street1, street2, languages=None, fuzzy=False):
        if languages is None:
            languages1 = place_languages(['road'], [street1])
            languages2 = place_languages(['road'], [street2])
            if languages1 is not None and languages2 is not None:
                languages = combined_languages(languages1, languages2)
            else:
                languages = languages1 or languages2 or DEFAULT_LANGUAGES

        street_status = is_street_duplicate(street1, street2, languages=languages)
        same_street = street_status in (duplicate_status.EXACT_DUPLICATE, duplicate_status.LIKELY_DUPLICATE)
        if street_status == duplicate_status.EXACT_DUPLICATE:
            street_sim = 1.0
        elif street_status == duplicate_status.NEEDS_REVIEW:
            street_sim = 0.5
        elif street_status == duplicate_status.LIKELY_DUPLICATE:
            street_sim = 0.9
        else:
            street_sim = 0.0

        if same_street:
            return Dupe(status=street_status, sim=street_sim)
        elif fuzzy:
            a1_street_tokens = Name.content_tokens(street1, languages=languages)
            a1_scores_norm = WordIndex.normalized_vector([1] * len(a1_street_tokens))
            a2_street_tokens = Name.content_tokens(street2, languages=languages)
            a2_scores_norm = WordIndex.normalized_vector([1] * len(a2_street_tokens))
            if a1_street_tokens and a2_street_tokens and a1_scores_norm and a2_scores_norm:
                street_status, street_sim = is_street_duplicate_fuzzy(a1_street_tokens, a1_scores_norm, a2_street_tokens, a2_scores_norm, languages=languages)
                return Dupe(status=street_status, sim=street_sim)
            else:
                return Dupe(status=duplicate_status.NON_DUPLICATE, sim=street_sim)
        else:
            return Dupe(status=duplicate_status.NON_DUPLICATE, sim=street_sim)


class AddressDeduper(object):
    DEFAULT_GEOHASH_PRECISION = 7

    address_only_keys = True
    name_only_keys = False
    name_and_address_keys = False
    with_name = False

    us_zip5_pattern = re.compile('^\\s*([0-9]{5})\\-?([0-9]{4})\\s*$')

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
            a1_house_number = safe_decode(a1_house_number).strip()
        if a2_house_number:
            a2_house_number = safe_decode(a2_house_number).strip()

        a1_base_house_number = a1.get(AddressComponents.HOUSE_NUMBER_BASE)
        a2_base_house_number = a2.get(AddressComponents.HOUSE_NUMBER_BASE)

        if a1_base_house_number:
            a1_base_house_number = safe_decode(a1_base_house_number).strip()
        if a2_base_house_number:
            a2_base_house_number = safe_decode(a2_base_house_number).strip()

        if (a1_street and not a2_street) or (a2_street and not a1_street):
            return NULL_DUPE

        if (a1_house_number and not a2_house_number) or (a2_house_number and not a1_house_number):
            return NULL_DUPE

        have_street = a1_street and a2_street
        same_street = False
        street_status = duplicate_status.NON_DUPLICATE

        street_sim = 0.0
        if have_street:
            street_dupe_status = StreetDeduper.street_dupe_status(a1_street, a2_street, languages=languages, fuzzy=fuzzy_street_name)
            same_street = street_dupe_status.status in (duplicate_status.EXACT_DUPLICATE, duplicate_status.LIKELY_DUPLICATE)

            if not same_street:
                return Dupe(status=duplicate_status.NON_DUPLICATE, sim=street_sim)

        have_house_number = a1_house_number and a2_house_number
        have_base_house_number = a1_base_house_number or a2_base_house_number
        same_house_number = False
        house_number_status = duplicate_status.NON_DUPLICATE
        house_number_sim = 0.0

        if have_house_number:
            house_number_status = is_house_number_duplicate(a1_house_number, a2_house_number, languages=languages)
            same_house_number = house_number_status == duplicate_status.EXACT_DUPLICATE
            if same_house_number:
                house_number_sim = 1.0

            if have_base_house_number and not same_house_number:
                a1h = a1_base_house_number or a1_house_number
                a2h = a2_base_house_number or a2_house_number

                base_house_number_status = is_house_number_duplicate(a1h, a2h, languages=languages)
                same_house_number = base_house_number_status == duplicate_status.EXACT_DUPLICATE
                if same_house_number:
                    house_number_status = duplicate_status.LIKELY_DUPLICATE
                    house_number_sim = 0.9

            if not same_house_number:
                return Dupe(status=duplicate_status.NON_DUPLICATE, sim=house_number_sim)

        if not have_house_number and not have_street:
            return NULL_DUPE

        if have_street and same_street and have_house_number and same_house_number:
            min_status, min_sim = min((street_dupe_status.status, street_dupe_status.sim), (house_number_status, house_number_sim))
            return Dupe(status=min_status, sim=min_sim)
        elif have_house_number and same_house_number and not have_street:
            return Dupe(status=house_number_status, sim=house_number_sim)
        elif have_street and same_street and not have_house_number:
            return Dupe(status=street_status, sim=street_sim)

        return NULL_DUPE

    @classmethod
    def is_address_dupe(cls, a1, a2, languages=None, fuzzy_street_name=False):
        dupe = cls.address_dupe_status(a1, a2, languages=languages, fuzzy_street_name=fuzzy_street_name)
        return dupe.status in (duplicate_status.EXACT_DUPLICATE, duplicate_status.LIKELY_DUPLICATE)

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

        return cls.is_address_dupe(a1, a2, languages=languages, fuzzy_street_name=fuzzy_street_name) and (not with_unit or cls.is_sub_building_dupe(a1, a2, languages=languages))

    @classmethod
    def address_labels_and_values(cls, address, use_zip5=False):
        string_address = {k: v for k, v in six.iteritems(address) if isinstance(v, six.string_types) and v.strip()}
        if use_zip5 and AddressComponents.POSTAL_CODE in string_address:
            postal_code = string_address[AddressComponents.POSTAL_CODE]
            match = cls.us_zip5_pattern.match(postal_code)
            if match:
                string_address[AddressComponents.POSTAL_CODE] = match.group(1)

        return list(string_address.keys()), list(string_address.values())

    @classmethod
    def near_dupe_hashes(cls, address, languages=None,
                         with_address=True,
                         with_unit=False,
                         with_city_or_equivalent=False,
                         with_small_containing_boundaries=False,
                         with_postal_code=False,
                         with_zip5=False,
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

        base_house_number = None
        address_with_base_house_number = None
        if AddressComponents.HOUSE_NUMBER_BASE in address:
            base_house_number = address[AddressComponents.HOUSE_NUMBER_BASE]
            address = {k: v for k, v in six.iteritems(address) if k != AddressComponents.HOUSE_NUMBER_BASE}
            address_with_base_house_number = address.copy()
            address_with_base_house_number[AddressComponents.HOUSE_NUMBER] = base_house_number

        if name_only_keys is None:
            name_only_keys = cls.name_only_keys

        if name_and_address_keys is None:
            name_and_address_keys = cls.name_and_address_keys

        if address_only_keys is None:
            address_only_keys = cls.address_only_keys

        input_address = address

        all_hashes = []
        all_hashes_set = set()

        for address in (input_address, address_with_base_house_number):
            if address is None:
                continue

            labels, values = cls.address_labels_and_values(address, use_zip5=with_zip5)
            if not (labels and values and len(labels) == len(values)):
                return []

            hashes = near_dupe_hashes(labels, values, languages=languages,
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
            hashes = hashes or []

            all_hashes.extend([h for h in hashes if h not in all_hashes_set])
            all_hashes_set |= set(hashes)

        return all_hashes


class Name(object):
    @classmethod
    def content_tokens(cls, name, languages=None):
        return [t for t, c in normalized_tokens(name, string_options=DEFAULT_STRING_OPTIONS | NORMALIZE_STRING_REPLACE_NUMEX, languages=languages) if c in token_types.WORD_TOKEN_TYPES or c in token_types.NUMERIC_TOKEN_TYPES or c in (token_types.AMPERSAND, token_types.POUND)]


class PhoneNumberDeduper(object):
    @classmethod
    def normalized_phone_numbers(cls, a1, a2):
        num1 = a1.get(EntityDetails.PHONE, u'').strip()
        num2 = a2.get(EntityDetails.PHONE, u'').strip()

        country_code1 = a1.get(AddressComponents.COUNTRY)
        country_code2 = a2.get(AddressComponents.COUNTRY)

        if country_code1 and country_code2 and country_code1 != country_code2:
            return None, None

        country_code = country_code1 or country_code2

        try:
            p1 = phonenumbers.parse(num1, region=country_code)
            p2 = phonenumbers.parse(num2, region=country_code)
        except phonenumbers.NumberParseException:
            return None, None

        return p1, p2

    @classmethod
    def is_phone_number_dupe(cls, p1, p2):
        return p1 and p2 and p1.country_code == p2.country_code and p1.national_number == p2.national_number

    @classmethod
    def revised_dupe_class(cls, dupe_class, a1, a2):
        p1, p2 = cls.normalized_phone_numbers(a1, a2)
        have_phone_number = p1 is not None and p2 is not None
        same_phone_number = cls.is_phone_number_dupe(p1, p2)
        different_phone_number = have_phone_number and not same_phone_number

        if dupe_class == duplicate_status.NEEDS_REVIEW and same_phone_number:
            dupe_class = duplicate_status.LIKELY_DUPLICATE
        elif dupe_class == duplicate_status.LIKELY_DUPLICATE and different_phone_number:
            dupe_class = duplicate_status.NEEDS_REVIEW

        return dupe_class, same_phone_number


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
        a1_name_tokens = Name.content_tokens(a1_name, languages=languages)
        a2_name_tokens = Name.content_tokens(a2_name, languages=languages)
        if not a1_name_tokens or not a2_name_tokens:
            return None, 0.0

        a1_scores = cls.word_scores_normalized(a1_name_tokens, word_index)
        a2_scores = cls.word_scores_normalized(a2_name_tokens, word_index)

        return is_name_duplicate_fuzzy(a1_name_tokens, a1_scores, a2_name_tokens, a2_scores, languages=languages,
                                       likely_dupe_threshold=likely_dupe_threshold, needs_review_threshold=needs_review_threshold)

    @classmethod
    def dupe_class_and_sim(cls, a1, a2, word_index=None, likely_dupe_threshold=DedupeResponse.default_name_dupe_threshold,
                           needs_review_threshold=DedupeResponse.default_name_review_threshold, with_address=True, with_unit=False, with_phone_number=True, fuzzy_street_name=False):
        a1_name = a1.get(AddressComponents.NAME)
        a2_name = a2.get(AddressComponents.NAME)
        if not a1_name or not a2_name:
            return NULL_DUPE

        a1_languages = cls.address_languages(a1)
        a2_languages = cls.address_languages(a2)

        languages = cls.combined_languages(a1_languages, a2_languages)

        if with_address:
            same_address = cls.is_address_dupe(a1, a2, languages=languages, fuzzy_street_name=fuzzy_street_name)
            if not same_address:
                return NULL_DUPE

        if with_unit:
            same_unit = cls.is_sub_building_dupe(a1, a2, languages=languages)
            if not same_unit:
                return NULL_DUPE

        name_dupe_class = cls.name_dupe_status(a1_name, a2_name, languages=languages)
        name_sim = 0.0

        if name_dupe_class == duplicate_status.EXACT_DUPLICATE:
            name_sim = 1.0
        elif name_dupe_class == duplicate_status.LIKELY_DUPLICATE:
            name_sim = likely_dupe_threshold
        elif name_dupe_class == duplicate_status.NEEDS_REVIEW:
            name_sim = needs_review_threshold
        else:
            return NULL_DUPE

        if word_index and name_dupe_class != duplicate_status.EXACT_DUPLICATE:
            name_fuzzy_dupe_class, name_fuzzy_sim = cls.name_dupe_similarity(a1_name, a2_name, word_index=word_index, languages=languages)

            if name_fuzzy_dupe_class is None:
                return NULL_DUPE

            if name_fuzzy_dupe_class >= name_dupe_class:
                name_dupe_class = name_fuzzy_dupe_class
                name_sim = name_fuzzy_sim

        phone_number_dupe = None

        if with_phone_number:
            name_dupe_class, phone_number_dupe = PhoneNumberDeduper.revised_dupe_class(name_dupe_class, a1, a2)

        return Dupe(name_dupe_class, name_sim)

    @classmethod
    def is_dupe(cls, a1, a2, index=None, name_dupe_threshold=DedupeResponse.default_name_dupe_threshold, with_unit=False, fuzzy_street_name=False):
        dupe = cls.dupe_class_and_sim(a1, a2, index=index, name_dupe_threshold=name_dupe_threshold, with_unit=with_unit, fuzzy_street_name=fuzzy_street_name)
        return dupe.status in (duplicate_status.EXACT_DUPLICATE, duplicate_status.LIKELY_DUPLICATE)

    @classmethod
    def name_dupe_status(cls, name1, name2, languages=None):
        return is_name_duplicate(name1, name2, languages=languages)
