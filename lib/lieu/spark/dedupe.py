from six import itertools

from lieu.address import AddressComponents, Coordinates
from lieu.api import DedupeResponse
from lieu.dedupe import AddressDeduper, Name, VenueDeduper
from lieu.tfidf import TFIDF

from lieu.spark.tfidf import TFIDFSpark, GeoTFIDFSpark
from lieu.spark.utils import IDPairRDD

from postal.dedupe import duplicate_status


class AddressDeduperSpark(object):
    @classmethod
    def address_dupe_pairs(cls, address_hashes, addresses_and_languages, sub_building=False, fuzzy_street_name=False):
        candidate_dupe_pairs = address_hashes.groupByKey() \
                                             .filter(lambda (key, vals): len(vals) > 1) \
                                             .values() \
                                             .flatMap(lambda vals: [(max(uid1, uid2), min(uid1, uid2)) for uid1, uid2 in itertools.combinations(vals, 2)]) \
                                             .distinct()

        dupe_pairs = IDPairRDD.join_pairs(candidate_dupe_pairs, addresses_and_languages) \
                              .mapValues(lambda ((a1, langs1), (a2, langs2)): (a1, a2, AddressDeduper.combined_languages(langs1, langs2))) \
                              .mapValues(lambda (a1, a2, all_langs): (AddressDeduper.address_dupe_status(a1, a2, languages=all_langs, fuzzy_street_name=fuzzy_street_name), (not sub_building or AddressDeduper.is_sub_building_dupe(a1, a2, languages=all_langs)))) \
                              .filter(lambda ((uid1, uid2), (address_dupe_status, is_sub_building_dupe)): address_dupe_status in (duplicate_status.EXACT_DUPLICATE, duplicate_status.LIKELY_DUPLICATE) and is_sub_building_dupe) \
                              .map(lambda ((uid1, uid2), (address_dupe_status, is_sub_building_dupe)): ((uid1, uid2), address_dupe_status))

        return dupe_pairs

    @classmethod
    def address_languages(cls, id_address):
        return id_address.mapValues(lambda address: AddressDeduper.address_languages(address))

    @classmethod
    def dupe_sims(cls, address_ids, with_unit=False, with_city_or_equivalent=False, with_small_containing_boundaries=False, with_postal_code=False, with_latlon=True, fuzzy_street=False):
        id_address = address_ids.map(lambda (address, uid): (uid, address))
        address_languages = cls.address_languages(id_address)
        addresses_and_languages = id_address.join(address_languages)

        address_hashes = addresses_and_languages.flatMap(lambda (uid, (address, langs)): [(h, uid) for h in AddressDeduper.near_dupe_hashes(address, languages=langs, with_address=with_address, with_unit=with_unit, with_city_or_equivalent=with_city_or_equivalent, \
                                                                                                                                            with_small_containing_boundaries=with_small_containing_boundaries, with_postal_code=with_postal_code, with_latlon=with_latlon)])

        return cls.address_dupe_pairs(address_hashes, addresses_and_languages) \
                  .map(lambda ((uid1, uid2), dupe_status): ((uid1, uid2), (dupe_status, 1.0)))


class VenueDeduperSpark(object):
    DEFAULT_GEO_MODEL_PROPORTION = 0.6

    @classmethod
    def names(cls, address_ids):
        return address_ids.map(lambda (address, uid): (address.get(AddressComponents.NAME, ''), uid))

    @classmethod
    def names_geo(cls, address_ids):
        return address_ids.map(lambda (address, uid): ((address.get(AddressComponents.NAME, ''), address.get(Coordinates.LATITUDE), address.get(Coordinates.LONGITUDE)), uid) )

    @classmethod
    def batch_doc_count(cls, docs):
        return docs.count()

    @classmethod
    def name_similarity(cls, tfidf1, tfidf2, languages=None, name_dupe_threshold=DedupeResponse.default_name_dupe_threshold,
                        name_review_threshold=DedupeResponse.default_name_review_threshold):
        a1_name_tokens = tfidf1.keys()
        a1_tfidf_norm = TFIDF.normalized_tfidf_vector(tfidf1.values())

        a2_name_tokens = tfidf2.keys()
        a2_tfidf_norm = TFIDF.normalized_tfidf_vector(tfidf2.values())

        return VenueDeduper.name_dupe_fuzzy(a1_name_tokens, a1_tfidf_norm, a2_name_tokens, a2_tfidf_norm, languages=languages,
                                            likely_dupe_threshold=name_dupe_threshold, needs_review_threshold=name_review_threshold)

    @classmethod
    def name_geo_dupe_similarity(cls, tfidf1, tfidf2, geo_tfidf1, geo_tfidf2, languages=None, geo_model_proportion=DEFAULT_GEO_MODEL_PROPORTION,
                                 name_dupe_threshold=DedupeResponse.default_name_dupe_threshold, name_review_threshold=DedupeResponse.default_name_review_threshold):
        dupe_class, tfidf_sim = cls.name_similarity(tfidf1, tfidf2, languages=languages,
                                                    name_dupe_threshold=name_dupe_threshold, name_review_threshold=name_review_threshold)

        geo_dupe_class, geo_tfidf_sim = cls.name_similarity(geo_tfidf1, geo_tfidf2, languages=languages,
                                                            name_dupe_threshold=name_dupe_threshold, name_review_threshold=name_review_threshold)

        combined_sim = (geo_model_proportion * geo_tfidf_sim) + ((1.0 - geo_model_proportion) * tfidf_sim)
        dupe_class = duplicate_status.LIKELY_DUPLICATE if combined_sim >= name_dupe_threshold else duplicate_status.NEEDS_REVIEW if combined_sim >= name_review_threshold else duplicate_status.NON_DUPLICATE
        return dupe_class, combined_sim

    @classmethod
    def dupe_sims(cls, address_ids, geo_model=True, doc_frequency=None, geo_doc_frequency=None, total_docs=0, total_docs_by_geo=None,
                  min_name_word_count=1, min_geo_name_word_count=1, name_dupe_threshold=DedupeResponse.default_name_dupe_threshold,
                  name_review_threshold=DedupeResponse.default_name_review_threshold, geo_model_proportion=DEFAULT_GEO_MODEL_PROPORTION,
                  with_address=True, with_unit=False, with_city_or_equivalent=False, with_small_containing_boundaries=False, with_postal_code=False,
                  with_latlon=True, fuzzy_street_name=True):
        name_ids = cls.names(address_ids)
        name_word_counts = TFIDFSpark.doc_word_counts(name_ids, has_id=True)
        batch_doc_frequency = TFIDFSpark.doc_frequency(name_word_counts)

        id_address = address_ids.map(lambda (address, uid): (uid, address))

        address_languages = AddressDeduperSpark.address_languages(id_address)

        if doc_frequency is not None:
            doc_frequency = TFIDFSpark.update_doc_frequency(doc_frequency, batch_doc_frequency)
        else:
            doc_frequency = batch_doc_frequency

        name_geo_word_counts = None

        if geo_model:
            name_geo_ids = cls.names_geo(address_ids)
            batch_docs_by_geo = GeoTFIDFSpark.total_docs_by_geo(name_geo_ids, has_id=True)
            if total_docs_by_geo is None:
                total_docs_by_geo = batch_docs_by_geo
            else:
                total_docs_by_geo = GeoTFIDFSpark.update_total_docs_by_geo(total_docs_by_geo, batch_docs_by_geo)

            geo_aliases = GeoTFIDFSpark.geo_aliases(total_docs_by_geo)
            updated_total_docs_geo_aliases = GeoTFIDFSpark.updated_total_docs_geo_aliases(total_docs_by_geo, geo_aliases)

            name_geo_word_counts = GeoTFIDFSpark.doc_word_counts(name_geo_ids, has_id=True, geo_aliases=geo_aliases)

            batch_geo_doc_frequency = GeoTFIDFSpark.doc_frequency(name_geo_word_counts)

            if geo_doc_frequency is not None:
                geo_doc_frequency = GeoTFIDFSpark.update_doc_frequency(geo_doc_frequency, batch_geo_doc_frequency)
            else:
                geo_doc_frequency = batch_geo_doc_frequency

        batch_docs = cls.batch_doc_count(address_ids)

        total_docs += batch_docs
        names_tfidf = TFIDFSpark.docs_tfidf(name_word_counts, doc_frequency, total_docs)
        names_geo_tfidf = None

        if geo_model:
            names_geo_tfidf = GeoTFIDFSpark.docs_tfidf(name_geo_word_counts, geo_doc_frequency, updated_total_docs_geo_aliases)

        addresses_and_languages = id_address.join(address_languages)

        address_hashes = addresses_and_languages.flatMap(lambda (uid, (address, langs)): [(h, uid) for h in VenueDeduper.near_dupe_hashes(address, languages=langs, with_address=with_address, with_unit=with_unit, with_city_or_equivalent=with_city_or_equivalent, \
                                                                                                                                          with_small_containing_boundaries=with_small_containing_boundaries, with_postal_code=with_postal_code, with_latlon=with_latlon)])

        address_dupe_pairs = AddressDeduperSpark.address_dupe_pairs(address_hashes, addresses_and_languages, sub_building=with_unit, fuzzy_street_name=fuzzy_street_name)

        id_names = name_ids.map(lambda (name, uid): (uid, name))
        names_and_languages = id_names.join(address_languages)

        exact_dupe_pairs = IDPairRDD.join_pairs(address_dupe_pairs.keys(), names_and_languages) \
                                    .filter(lambda ((uid1, uid2), ((name1, langs1), (name2, langs2))): VenueDeduper.name_dupe_status(name1, name2, languages=AddressDeduper.combined_languages(langs1, langs2)) == duplicate_status.EXACT_DUPLICATE ) \
                                    .keys()

        possible_dupe_pairs = address_dupe_pairs.keys().subtract(exact_dupe_pairs)

        if not geo_model:
            dupe_pair_sims = IDPairRDD.join_pairs(possible_dupe_pairs, names_tfidf.join(address_languages)) \
                                      .mapValues(lambda ((tfidf1, languages1), (tfidf2, languages2)): cls.name_similarity(tfidf1, tfidf2, languages=VenueDeduper.combined_languages(languages1, languages2)))
        else:
            dupe_pair_sims = IDPairRDD.join_pairs(possible_dupe_pairs, names_tfidf.join(names_geo_tfidf).join(address_languages)) \
                                      .mapValues(lambda (((tfidf1, geo_tfidf1), languages1) , ((tfidf2, geo_tfidf2), languages2)): cls.name_geo_dupe_similarity(tfidf1, tfidf2,
                                                                                                                                                                geo_tfidf1, geo_tfidf2,
                                                                                                                                                                languages=VenueDeduper.combined_languages(languages1, languages2),
                                                                                                                                                                geo_model_proportion=geo_model_proportion))

        exact_dupe_sims = exact_dupe_pairs.map(lambda (uid1, uid2): ((uid1, uid2), (DedupeResponse.classifications.EXACT_DUPE, 1.0)))

        possible_dupe_sims = dupe_pair_sims.filter(lambda ((uid1, uid2), (dupe_class, sim)): dupe_class in (duplicate_status.LIKELY_DUPLICATE, duplicate_status.NEEDS_REVIEW)) \
                                           .mapValues(lambda (dupe_class, sim): (DedupeResponse.classifications.LIKELY_DUPE if dupe_class == duplicate_status.LIKELY_DUPLICATE else DedupeResponse.classifications.NEEDS_REVIEW, sim)) \
                                           .subtractByKey(exact_dupe_sims)

        all_dupe_sims = possible_dupe_sims.union(exact_dupe_sims)

        return all_dupe_sims
