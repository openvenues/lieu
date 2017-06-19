from six import itertools

from lieu.address import AddressComponents, Coordinates
from lieu.api import DedupeResponse
from lieu.dedupe import AddressDeduper, NameDeduper, VenueDeduper
from lieu.similarity import soft_tfidf_similarity, jaccard_similarity
from lieu.tfidf import TFIDF

from lieu.spark.tfidf import TFIDFSpark, GeoTFIDFSpark
from lieu.spark.utils import IDPairRDD


class AddressDeduperSpark(object):
    @classmethod
    def address_dupe_pairs(cls, address_hashes, sub_building=False):
        dupe_pairs = address_hashes.groupByKey() \
                                   .filter(lambda (key, vals): len(vals) > 1) \
                                   .values() \
                                   .flatMap(lambda vals: [(max(uid1, uid2), min(uid1, uid2))
                                                          for (uid1, a1), (uid2, a2) in itertools.combinations(vals, 2)
                                                          if AddressDeduper.is_address_dupe(a1, a2) and
                                                          (not sub_building or AddressDeduper.is_sub_building_dupe(a1, a2))]) \
                                   .distinct()

        return dupe_pairs

    @classmethod
    def dupes(cls, address_ids):
        address_hashes = address_ids.flatMap(lambda (address, uid): [(h, (uid, address)) for h in AddressDeduper.near_dupe_hashes(address)])

        return cls.address_dupe_pairs(address_hashes) \
                  .map(lambda (uid1, uid2): ((uid1, uid2), (DedupeResponse.classifications.EXACT_DUPE)))


class VenueDeduperSpark(object):
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
    def dupes(cls, address_ids, geo_model=True, doc_frequency=None, geo_doc_frequency=None, total_docs=0, total_docs_by_geo=None,
              min_name_word_count=1, min_geo_name_word_count=1, geo_model_proportion=0.6, dupe_threshold=NameDeduper.default_dupe_threshold):
        name_ids = cls.names(address_ids)
        name_word_counts = TFIDFSpark.doc_word_counts(name_ids, has_id=True)
        batch_doc_frequency = TFIDFSpark.doc_frequency(name_word_counts)

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

        address_hashes = address_ids.flatMap(lambda (address, uid): [(h, (uid, address)) for h in VenueDeduper.near_dupe_hashes(address)])

        address_dupe_pairs = AddressDeduperSpark.address_dupe_pairs(address_hashes)

        id_names = name_ids.map(lambda (name, uid): (uid, name))

        exact_dupe_pairs = IDPairRDD.join_pairs(address_dupe_pairs, id_names) \
                                    .filter(lambda ((uid1, uid2), (name1, name2)): VenueDeduper.is_exact_name_dupe(name1, name2)) \
                                    .keys()

        if not geo_model:
            likely_dupe_pairs = IDPairRDD.join_pairs(address_dupe_pairs, names_tfidf) \
                                         .mapValues(lambda (tfidf1, tfidf2): (TFIDF.normalized_tfidf_vector(tfidf1.items()), TFIDF.normalized_tfidf_vector(tfidf2.items()))) \
                                         .filter(lambda ((uid1, uid2), (tfidf1_norm, tfidf2_norm)): soft_tfidf_similarity(tfidf1_norm, tfidf2_norm) >= dupe_threshold)
        else:
            likely_dupe_pairs = IDPairRDD.join_pairs(address_dupe_pairs, names_tfidf.join(names_geo_tfidf)) \
                                         .mapValues(lambda ((tfidf1, geo_tfidf1), (tfidf2, geo_tfidf2)): (TFIDF.normalized_tfidf_vector(tfidf1.items()),
                                                                                                          TFIDF.normalized_tfidf_vector(geo_tfidf1.items()),
                                                                                                          TFIDF.normalized_tfidf_vector(tfidf2.items()),
                                                                                                          TFIDF.normalized_tfidf_vector(geo_tfidf2.items()))) \
                                         .filter(lambda ((uid1, uid2), (tfidf1_norm, tfidf1_geo_norm, tfidf2_norm, tfidf2_geo_norm)): ((soft_tfidf_similarity(tfidf1_geo_norm, tfidf2_geo_norm) * geo_model_proportion) +
                                                                                                                                       (soft_tfidf_similarity(tfidf1_norm, tfidf2_norm) * (1.0 - geo_model_proportion))) >= dupe_threshold)
        likely_dupe_pairs = likely_dupe_pairs.keys() \
                                             .subtract(exact_dupe_pairs)

        all_dupes = likely_dupe_pairs.map(lambda (uid1, uid2): ((uid1, uid2), DedupeResponse.classifications.LIKELY_DUPE)) \
                                     .union(exact_dupe_pairs.map(lambda (uid1, uid2): ((uid1, uid2), DedupeResponse.classifications.EXACT_DUPE)))

        return all_dupes
