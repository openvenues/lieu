import geohash
import itertools
import math

from six import operator

from collections import Counter

from lieu.dedupe import Name
from lieu.information_gain import InformationGain
from lieu.spark.geo_word_index import GeoWordIndexSpark


class InformationGainSpark(object):
    @classmethod
    def doc_cooccurrences(cls, docs, has_id=False):
        if not has_id:
            docs = docs.zipWithUniqueId()

        return docs.flatMap(lambda (doc, doc_id): [((word, other), 1) for word, other in itertools.permutations(doc, 2)]) \
                   .reduceByKey(lambda x, y: x + y)

    @classmethod
    def filter_min_doc_count(cls, word_marginals, min_count=2):
        return word_marginals.filter(lambda (key, count): count >= min_count)

    @classmethod
    def doc_words(cls, docs, has_id=False, geohash_precision=GeoWordIndexSpark.DEFAULT_GEOHASH_PRECISION):
        if not has_id:
            docs = docs.zipWithUniqueId()

        doc_words = docs.flatMap(lambda (doc, doc_id): [(word, (doc_id, i))
                                                        for i, word in enumerate(doc)])
        return doc_words

    @classmethod
    def word_marginal_probs(cls, docs, total_docs, has_id=False, min_count=1):
        if not has_id:
            docs = docs.zipWithUniqueId()

        marginals = docs.flatMap(lambda (doc, doc_id): [(word, 1) for word in set(doc)]) \
                        .reduceByKey(lambda x, y: x + y)

        if min_count > 1:
            marginals = cls.filter_min_doc_count(marginals, min_count=min_count)

        return marginals.mapValues(lambda count: float(count) / total_docs)

    @classmethod
    def word_info_gain(cls, doc_cooccurrences, word_marginal_probs, min_count=1):
        num_partitions = doc_cooccurrences.getNumPartitions()

        doc_sum_cooccurrences = doc_cooccurrences.map(lambda ((word, other), count): (word, count)).reduceByKey(lambda x, y: x + y)
        probs = doc_cooccurrences.map(lambda ((word, other), count): (word, (other, count))).join(doc_sum_cooccurrences).map(lambda (word, ((other, c_xy), c_y)): ((word, other), float(c_xy) / c_y))

        coo_info_gain = probs.map(lambda ((word, other), prob): (other, (word, prob))) \
                             .join(word_marginal_probs) \
                             .map(lambda (other, ((word, p_xy), p_x)): (word, math.log(p_xy / p_x, 2) * p_xy)) \
                             .reduceByKey(lambda x, y: x + y) \
                             .mapValues(lambda value: max(value, 0.0))
        no_coo_info_gain = word_marginal_probs.subtractByKey(coo_info_gain).mapValues(lambda p_x: math.log(1.0 / p_x, 2))
        word_info_gain = coo_info_gain.union(no_coo_info_gain)

        return word_info_gain.coalesce(num_partitions)

    @classmethod
    def doc_scores(cls, doc_words, word_info_gain):
        num_partitions = doc_words.getNumPartitions()

        doc_word_stats = doc_words.join(word_info_gain).map(lambda (word, ((doc_id, pos), info_gain)): (doc_id, (word, pos, info_gain)))

        docs_info_gain = doc_word_stats.groupByKey() \
                                       .mapValues(lambda vals: [(word, val) for word, pos, val in sorted(vals, key=operator.itemgetter(1))])

        return docs_info_gain.coalesce(num_partitions)

    @classmethod
    def save(cls, word_info_gain, index_path):
        word_info_gain.map(lambda (word, val): u'\t'.join(word, val)) \
                      .saveAsTextFile(index_path)


class GeoInformationGainSpark(InformationGainSpark, GeoWordIndexSpark):
    @classmethod
    def doc_cooccurrences(cls, docs, geo_aliases=None, has_id=False, geohash_precision=GeoWordIndexSpark.DEFAULT_GEOHASH_PRECISION):
        if not has_id:
            docs = docs.zipWithUniqueId()

        docs = docs.filter(lambda ((doc, lat, lon), doc_id): lat is not None and lon is not None)

        if geo_aliases:
            doc_geohashes = docs.flatMap(lambda ((doc, lat, lon), doc_id): [(geo, (doc, doc_id)) for geo in cls.geohashes(lat, lon)]) \
                                .leftOuterJoin(geo_aliases) \
                                .map(lambda (geo, ((doc, doc_id), geo_alias)): (geo_alias or geo, (doc, doc_id)))
        else:
            doc_geohashes = docs.flatMap(lambda ((doc, lat, lon), doc_id): [(geo, (doc, doc_id)) for geo in cls.geohashes(lat, lon)])

        return doc_geohashes.flatMap(lambda (geo, (doc, doc_id)): [((geo, word, other), 1) for word, other in itertools.permutations(doc, 2)]) \
                            .reduceByKey(lambda x, y: x + y)

    @classmethod
    def doc_words(cls, docs, geo_aliases=None, has_id=False, geohash_precision=GeoWordIndexSpark.DEFAULT_GEOHASH_PRECISION):
        if not has_id:
            docs = docs.zipWithUniqueId()

        docs = docs.filter(lambda ((doc, lat, lon), doc_id): lat is not None and lon is not None)

        if geo_aliases:
            doc_geohashes = docs.map(lambda ((doc, lat, lon), doc_id): (cls.geohash(lat, lon, geohash_precision=geohash_precision), (doc, doc_id))) \
                                .leftOuterJoin(geo_aliases) \
                                .map(lambda (geo, ((doc, doc_id), geo_alias)): (geo_alias or geo, (doc, doc_id)))
        else:
            doc_geohashes = docs.map(lambda ((doc, lat, lon), doc_id): (cls.geohash(lat, lon, geohash_precision=geohash_precision), (doc, doc_id)))

        doc_words = doc_geohashes.flatMap(lambda (geo, (doc, doc_id)): [((geo, word), (doc_id, pos))
                                                                        for pos, word in enumerate(doc)])
        return doc_words

    @classmethod
    def word_marginal_probs(cls, docs, total_docs_by_geo, geo_aliases=None, has_id=False, min_count=1, geohash_precision=GeoWordIndexSpark.DEFAULT_GEOHASH_PRECISION):
        if not has_id:
            docs = docs.zipWithUniqueId()

        docs = docs.filter(lambda ((doc, lat, lon), doc_id): lat is not None and lon is not None)
        num_partitions = docs.getNumPartitions()

        if geo_aliases:
            doc_geohashes = docs.flatMap(lambda ((doc, lat, lon), doc_id): [(gh, (doc, doc_id)) for gh in cls.geohashes(lat, lon)]) \
                                .leftOuterJoin(geo_aliases) \
                                .map(lambda (geo, ((doc, doc_id), geo_alias)): (geo_alias or geo, (doc, doc_id)))
        else:
            doc_geohashes = docs.flatMap(lambda ((doc, lat, lon), doc_id): [(gh, (doc, doc_id)) for gh in cls.geohashes(lat, lon)])

        marginals = doc_geohashes.flatMap(lambda (geo, (doc, doc_id)): [((geo, word), 1) for word in set(doc)]) \
                                 .reduceByKey(lambda x, y: x + y)

        if min_count > 1:
            marginals = cls.filter_min_doc_count(marginals, min_count=min_count)

        return marginals.map(lambda ((geo, word), count): (geo, (word, count))) \
                        .join(total_docs_by_geo) \
                        .map(lambda (geo, ((word, count), num_docs)): ((geo, word), float(count) / num_docs)) \
                        .coalesce(num_partitions)

    @classmethod
    def word_info_gain(cls, doc_cooccurrences, word_marginal_probs):
        num_partitions = word_marginal_probs.getNumPartitions()

        doc_sum_cooccurrences = doc_cooccurrences.map(lambda ((geo, word, other), count): ((geo, word), count)).reduceByKey(lambda x, y: x + y)
        probs = doc_cooccurrences.map(lambda ((geo, word, other), count): ((geo, word), (other, count))).join(doc_sum_cooccurrences).map(lambda ((geo, word), ((other, c_xy), c_y)): ((geo, word, other), float(c_xy) / c_y))

        coo_info_gain = probs.map(lambda ((geo, word, other), prob): ((geo, other), (word, prob))) \
                             .join(word_marginal_probs) \
                             .map(lambda ((geo, other), ((word, p_xy), p_x)): ((geo, word), math.log(p_xy / p_x, 2) * p_xy)) \
                             .reduceByKey(lambda x, y: x + y) \
                             .mapValues(lambda value: max(value, 0.0))
        no_coo_info_gain = word_marginal_probs.subtractByKey(coo_info_gain).mapValues(lambda p_x: math.log(1.0 / p_x, 2))
        word_info_gain = coo_info_gain.union(no_coo_info_gain)

        return word_info_gain.coalesce(num_partitions)

    @classmethod
    def doc_scores(cls, doc_words, word_info_gain):
        num_partitions = doc_words.getNumPartitions()

        doc_word_stats = doc_words.join(word_info_gain).map(lambda ((geo, word), ((doc_id, pos), info_gain)): (doc_id, (word, pos, info_gain)))

        docs_info_gain = doc_word_stats.groupByKey() \
                                       .mapValues(lambda vals: [(word, info_gain) for word, pos, info_gain in sorted(vals, key=operator.itemgetter(1))])

        return docs_info_gain.coalesce(num_partitions)

    @classmethod
    def save(cls, word_info_gain, index_path):
        word_info_gain.map(lambda ((geo, word), val): u'\t'.join([geo, word, val])) \
                      .saveAsTextFile(index_path)
