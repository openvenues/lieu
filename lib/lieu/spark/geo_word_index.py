import geohash
import operator


class GeoWordIndexSpark(object):
    DEFAULT_GEOHASH_PRECISION = 4

    @classmethod
    def geohash(cls, lat, lon, geohash_precision=DEFAULT_GEOHASH_PRECISION):
        return geohash.encode(lat, lon)[:geohash_precision]

    @classmethod
    def geohashes(cls, lat, lon, geohash_precision=DEFAULT_GEOHASH_PRECISION):
        gh = cls.geohash(lat, lon, geohash_precision=geohash_precision)
        return [gh] + geohash.neighbors(gh)

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
