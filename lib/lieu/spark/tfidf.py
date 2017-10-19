import geohash
import math

from six import operator

from collections import Counter

from lieu.tfidf import TFIDF
from lieu.dedupe import NameDeduper


class TFIDFSpark(object):
    @classmethod
    def doc_word_counts(cls, docs, has_id=False):
        if not has_id:
            docs = docs.zipWithUniqueId()

        doc_word_counts = docs.flatMap(lambda (doc, doc_id): [(word, (doc_id, count))
                                                              for word, count in Counter(NameDeduper.content_tokens(doc)).items()])
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
    def docs_tfidf(cls, doc_word_counts, doc_frequency, total_docs, min_count=1):
        if min_count > 1:
            doc_frequency = cls.filter_min_doc_frequency(doc_frequency, min_count=min_count)

        num_partitions = doc_word_counts.getNumPartitions()

        doc_ids_word_stats = doc_word_counts.join(doc_frequency).map(lambda (word, ((doc_id, term_frequency), doc_frequency)): (doc_id, (word, term_frequency, doc_frequency)))
        docs_tfidf = doc_ids_word_stats.groupByKey() \
                                       .mapValues(lambda vals: {word: TFIDF.tfidf_score(term_frequency, doc_frequency, total_docs)
                                                                for word, term_frequency, doc_frequency in vals})
        return docs_tfidf.coalesce(num_partitions)


class GeoTFIDFSpark(TFIDFSpark):
    DEFAULT_GEOHASH_PRECISION = 4

    @classmethod
    def doc_geohash(cls, lat, lon, geohash_precision=DEFAULT_GEOHASH_PRECISION):
        return geohash.encode(lat, lon)[:geohash_precision]

    @classmethod
    def doc_word_counts(cls, docs, geo_aliases=None,  has_id=False, geohash_precision=DEFAULT_GEOHASH_PRECISION):
        if not has_id:
            docs = docs.zipWithUniqueId()

        if geo_aliases:
            doc_geohashes = docs.map(lambda ((doc, lat, lon), doc_id): (cls.doc_geohash(lat, lon), (doc, doc_id))) \
                                .leftOuterJoin(geo_aliases) \
                                .map(lambda (geo, ((doc, doc_id), geo_alias)): (geo_alias or geo, doc, doc_id))
        else:
            doc_geohashes = docs.map(lambda ((doc, lat, lon), doc_id): (cls.doc_geohash(lat, lon), doc, doc_id))

        doc_word_counts = doc_geohashes.flatMap(lambda (geo, doc, doc_id): [((geo, word), (doc_id, count))
                                                                            for word, count in Counter(NameDeduper.content_tokens(doc)).items()])
        return doc_word_counts

    @classmethod
    def geo_aliases(cls, total_docs_by_geo, min_doc_count=1000):
        keep_geos = total_docs_by_geo.filter(lambda (geo, count): count >= min_doc_count)
        alias_geos = total_docs_by_geo.subtract(keep_geos)
        return alias_geos.keys() \
                         .flatMap(lambda key: [(neighbor, key) for neighbor in geohash.neighbors(key)]) \
                         .join(keep_geos) \
                         .map(lambda (neighbor, (key, count)): (key, (neighbor, count))) \
                         .groupByKey() \
                         .map(lambda (key, values): (key, sorted(values, key=operator.itemgetter(1), reverse=True)[0][0]))

    @classmethod
    def total_docs_by_geo(cls, docs, has_id=False, geohash_precision=DEFAULT_GEOHASH_PRECISION):
        if not has_id:
            docs = docs.zipWithUniqueId()

        total_docs_by_geo = docs.map(lambda ((doc, lat, lon), doc_id): (cls.doc_geohash(lat, lon), 1)) \
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
    def docs_tfidf(cls, doc_word_counts, geo_doc_frequency, total_docs_by_geo, min_count=1):
        if min_count > 1:
            geo_doc_frequency = cls.filter_min_doc_frequency(geo_doc_frequency, min_count=min_count)

        num_partitions = doc_word_counts.getNumPartitions()

        geo_doc_frequency_totals = geo_doc_frequency.map(lambda ((geo, word), count): (geo, (word, count))) \
                                                    .join(total_docs_by_geo) \
                                                    .map(lambda (geo, ((word, count), num_docs)): ((geo, word), (count, num_docs)))
        doc_ids_word_stats = doc_word_counts.join(geo_doc_frequency_totals) \
                                            .map(lambda ((geo, word), ((doc_id, term_frequency), (doc_frequency, num_docs))): (doc_id, (geo, word, term_frequency, doc_frequency, num_docs)))

        docs_tfidf = doc_ids_word_stats.groupByKey() \
                                       .mapValues(lambda vals: {word: TFIDF.tfidf_score(term_frequency, doc_frequency, num_docs)
                                                                for geo, word, term_frequency, doc_frequency, num_docs in vals})
        return docs_tfidf.coalesce(num_partitions)
