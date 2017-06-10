import geohash
import itertools
import re

from collections import Counter


from postal.expand import expand_address, ADDRESS_NAME, ADDRESS_STREET, ADDRESS_UNIT, ADDRESS_LEVEL, ADDRESS_HOUSE_NUMBER

from lieu.address import AddressComponents, VenueDetails, Coordinates
from lieu.dedupe import AddressDeduper, NameDeduper, VenueDeduper
from lieu.similarity import soft_tfidf_similarity, jaccard_similarity
from lieu.tfidf import TFIDF

from lieu.spark.tfidf import TFIDFSpark
from lieu.spark.utils import IDPairRDD


class AddressDeduperSpark(object):
    @classmethod
    def address_dupe_pairs(cls, address_hashes, sub_building=False):
        dupe_pairs = address_hashes.groupByKey() \
                                   .filter(lambda (key, vals): len(vals) > 1) \
                                   .values() \
                                   .flatMap(lambda vals: [(min(uid1, uid2), max(uid1, uid2))
                                                          for (uid1, a1), (uid2, a2) in itertools.combinations(vals, 2)
                                                          if AddressDeduper.is_address_dupe(a1, a2) and
                                                          (not sub_building or AddressDeduper.is_sub_building_dupe(a1, a2))]) \
                                   .distinct()

        return dupe_pairs

    @classmethod
    def dupe_pairs(cls, address_ids, sub_building=True):
        address_hashes = address_ids.flatMap(lambda (address, uid): [(h, (uid, address)) for h in AddressDeduper.near_dupe_hashes(address)])

        return cls.address_dupe_pairs(address_hashes, sub_building=sub_building)


class VenueDeduperSpark(object):
    @classmethod
    def names(cls, address_ids):
        return address_ids.map(lambda (address, uid): (address.get(AddressComponents.NAME, ''), uid))

    @classmethod
    def batch_doc_count(cls, docs):
        return docs.count()

    @classmethod
    def dupe_pairs(cls, address_ids, doc_frequency=None, total_docs=0, min_name_word_count=1, dupe_threshold=NameDeduper.default_dupe_threshold):
        name_ids = cls.names(address_ids)
        name_word_counts = TFIDFSpark.doc_word_counts(name_ids, has_id=True)
        batch_doc_frequency = TFIDFSpark.doc_frequency(name_word_counts)

        if doc_frequency is not None:
            doc_frequency = TFIDFSpark.update_doc_frequency(doc_frequency, batch_doc_frequency)
        else:
            doc_frequency = batch_doc_frequency

        total_docs += cls.batch_doc_count(address_ids)
        names_tfidf = TFIDFSpark.docs_tfidf(name_word_counts, doc_frequency, total_docs)

        address_hashes = address_ids.flatMap(lambda (address, uid): [(h, (uid, address)) for h in VenueDeduper.near_dupe_hashes(address)])

        address_dupe_pairs = AddressDeduperSpark.address_dupe_pairs(address_hashes)

        dupe_pairs = IDPairRDD.join_pairs(address_dupe_pairs, names_tfidf) \
                              .mapValues(lambda (tfidf1, tfidf2): (TFIDF.normalized_tfidf_vector(tfidf1.items()), TFIDF.normalized_tfidf_vector(tfidf2.items()))) \
                              .filter(lambda ((uid1, uid2), (tfidf1_norm, tfidf2_norm)): soft_tfidf_similarity(tfidf1_norm, tfidf2_norm) >= dupe_threshold) \
                              .keys()

        return dupe_pairs
