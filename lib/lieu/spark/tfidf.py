import geohash
import math
import six

from six import operator

from collections import Counter

from lieu.tfidf import TFIDF
from lieu.dedupe import Name
from lieu.spark.geo_word_index import GeoWordIndexSpark


class TFIDFSpark(object):
    @classmethod
    def doc_words(cls, docs, has_id=False):
        if not has_id:
            docs = docs.zipWithUniqueId()

        doc_words = docs.flatMap(lambda (doc, doc_id): [(word, (doc_id, pos))
                                                        for pos, word in enumerate(doc)])
        return doc_words

    @classmethod
    def doc_word_counts(cls, docs, has_id=False):
        if not has_id:
            docs = docs.zipWithUniqueId()

        doc_word_counts = docs.flatMap(lambda (doc, doc_id): [(word, (doc_id, count))
                                                              for word, count in six.iteritems(Counter(doc))])
        return doc_word_counts

    @classmethod
    def doc_frequency(cls, doc_word_counts):
        doc_frequency = doc_word_counts.map(lambda (word, (doc_id, count)): (word, 1)).reduceByKey(lambda x, y: x + y)
        return doc_frequency

    @classmethod
    def filter_min_doc_frequency(cls, doc_frequency, min_count=2):
        return doc_frequency.filter(lambda (key, count): count >= min_count)

    @classmethod
    def update_doc_frequency(cls, doc_frequency, batch_frequency):
        updated = doc_frequency.union(batch_frequency).reduceByKey(lambda x, y: x + y)
        return updated

    @classmethod
    def doc_scores(cls, doc_words, doc_frequency, total_docs, min_count=1):
        if min_count > 1:
            doc_frequency = cls.filter_min_doc_frequency(doc_frequency, min_count=min_count)

        num_partitions = doc_words.getNumPartitions()

        doc_ids_word_stats = doc_words.join(doc_frequency).map(lambda (word, ((doc_id, pos), doc_frequency)): (doc_id, (word, pos, doc_frequency)))
        docs_tfidf = doc_ids_word_stats.groupByKey() \
                                       .mapValues(lambda vals: [(word, TFIDF.tfidf_score(1.0, doc_frequency, total_docs)) for word, pos, doc_frequency in sorted(vals, key=operator.itemgetter(1))])

        return docs_tfidf.coalesce(num_partitions)


class GeoTFIDFSpark(TFIDFSpark, GeoWordIndexSpark):
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
    def doc_word_counts(cls, docs, geo_aliases=None, has_id=False, geohash_precision=GeoWordIndexSpark.DEFAULT_GEOHASH_PRECISION):
        if not has_id:
            docs = docs.zipWithUniqueId()

        docs = docs.filter(lambda ((doc, lat, lon), doc_id): lat is not None and lon is not None)

        if geo_aliases:
            doc_geohashes = docs.flatMap(lambda ((doc, lat, lon), doc_id): [(gh, (doc, doc_id)) for gh in cls.geohashes(lat, lon)]) \
                                .leftOuterJoin(geo_aliases) \
                                .map(lambda (geo, ((doc, doc_id), geo_alias)): (geo_alias or geo, (doc, doc_id)))
        else:
            doc_geohashes = docs.flatMap(lambda ((doc, lat, lon), doc_id): [(gh, (doc, doc_id)) for gh in cls.geohashes(lat, lon)])

        doc_word_counts = doc_geohashes.flatMap(lambda (geo, (doc, doc_id)): [((geo, word), (doc_id, count))
                                                                              for word, count in six.iteritems(Counter(doc))])
        return doc_word_counts

    @classmethod
    def filter_min_doc_frequency(cls, doc_frequency, min_count=2):
        return doc_frequency.filter(lambda (key, count): count >= min_count)

    @classmethod
    def total_docs_by_geo(cls, docs, has_id=False, geohash_precision=GeoWordIndexSpark.DEFAULT_GEOHASH_PRECISION):
        if not has_id:
            docs = docs.zipWithUniqueId()

        docs = docs.filter(lambda ((doc, lat, lon), doc_id): lat is not None and lon is not None)

        total_docs_by_geo = docs.flatMap(lambda ((doc, lat, lon), doc_id): [(gh, 1) for gh in cls.geohashes(lat, lon)]) \
                                .reduceByKey(lambda x, y: x + y)
        return total_docs_by_geo

    @classmethod
    def update_total_docs_by_geo(cls, total_docs_by_geo, batch_docs_by_geo):
        updated = total_docs_by_geo.union(batch_docs_by_geo).reduceByKey(lambda x, y: x + y)
        return updated

    @classmethod
    def updated_total_docs_geo_aliases(cls, total_docs_by_geo, geo_aliases):
        batch_docs_by_geo = total_docs_by_geo.join(geo_aliases) \
                                             .map(lambda (geo, (count, geo_alias)): (geo_alias, count)) \
                                             .reduceByKey(lambda x, y: x + y)

        return cls.update_total_docs_by_geo(total_docs_by_geo, batch_docs_by_geo) \
                  .subtractByKey(geo_aliases)

    @classmethod
    def doc_scores(cls, doc_words, geo_doc_frequency, total_docs_by_geo, min_count=1):
        if min_count > 1:
            geo_doc_frequency = cls.filter_min_doc_frequency(geo_doc_frequency, min_count=min_count)

        num_partitions = doc_words.getNumPartitions()

        geo_doc_frequency_totals = geo_doc_frequency.map(lambda ((geo, word), count): (geo, (word, count))) \
                                                    .join(total_docs_by_geo) \
                                                    .map(lambda (geo, ((word, count), num_docs)): ((geo, word), (count, num_docs)))
        doc_ids_word_stats = doc_words.join(geo_doc_frequency_totals) \
                                      .map(lambda ((geo, word), ((doc_id, pos), (doc_frequency, num_docs))): (doc_id, (word, pos, doc_frequency, num_docs)))

        docs_tfidf = doc_ids_word_stats.groupByKey() \
                                       .mapValues(lambda vals: [(word, TFIDF.tfidf_score(1.0, doc_frequency, num_docs)) for word, pos, doc_frequency, num_docs in sorted(vals, key=operator.itemgetter(1))])

        return docs_tfidf.coalesce(num_partitions)

    @classmethod
    def save(cls, word_info_gain, index_path):
        word_info_gain.map(lambda ((geo, word), val): u'\t'.join([geo, word, val])) \
                      .saveAsTextFile(index_path)
