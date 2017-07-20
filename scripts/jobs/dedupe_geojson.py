import ujson as json
from collections import Counter, defaultdict

from lieu.api import DedupeResponse
from lieu.address import Address
from lieu.dedupe import NameDeduper

from lieu.spark.dedupe import AddressDeduperSpark, VenueDeduperSpark
from lieu.spark.utils import IDPairRDD

from mrjob.job import MRJob


class DedupeVenuesJob(MRJob):
    def configure_options(self):
        super(DedupeVenuesJob, self).configure_options()
        self.add_passthrough_option(
            '--address-only',
            default=False,
            action="store_true",
            help="Address duplicates only")

        self.add_passthrough_option(
            '--name-dupe-threshold',
            type=float,
            default=NameDeduper.default_dupe_threshold,
            help='Threshold between 0 and 1 for name deduping with Soft-TFIDF')

        self.add_passthrough_option(
            '--geo-name-dupe-threshold',
            type=float,
            default=NameDeduper.default_dupe_threshold,
            help='Threshold between 0 and 1 for geo name deduping with Soft-TFIDF')

        self.add_passthrough_option(
            '--with-unit',
            default=False,
            action="store_true",
            help="Whether to include units in deduplication")

    def spark(self, input_path, output_path):
        from pyspark import SparkContext

        sc = SparkContext(appName='dedupe venues MRJob')

        lines = sc.textFile(input_path)

        geojson_lines = lines.map(lambda line: json.loads(line.rstrip()))
        geojson_ids = geojson_lines.cache().zipWithIndex()
        id_geojson = geojson_ids.map(lambda (geojson, uid): (uid, geojson))

        address_ids = geojson_ids.map(lambda (geojson, uid): (Address.from_geojson(geojson), uid))

        if not self.options.address_only:
            dupes_with_classes = VenueDeduperSpark.dupes(address_ids)
        else:
            dupes_with_classes = AddressDeduperSpark.dupes(address_ids)

        dupes_of = dupes_with_classes.map(lambda ((uid1, uid2), classification): (uid1, (uid2, classification))) \
                                     .distinct()

        canonicals = dupes_with_classes.map(lambda ((uid1, uid2), classification): (uid2, (uid1, classification))) \
                                       .subtractByKey(dupes_of) \
                                       .map(lambda (uid2, (uid1, classification)): (uid2, True)) \
                                       .distinct()

        dupes_with_canonical = dupes_with_classes.map(lambda ((uid1, uid2), classification): (uid2, (uid1, classification))) \
                                                 .leftOuterJoin(canonicals) \
                                                 .map(lambda (uid2, ((uid1, classification), is_canonical)): ((uid1, uid2), (classification, is_canonical)))

        if not self.options.address_only:
            explain = DedupeResponse.explain_venue_dupe(name_dupe_threshold=self.options.name_dupe_threshold, with_unit=self.options.with_unit)
        else:
            explain = DedupeResponse.explain_address_dupe(with_unit=self.options.with_unit)

        dupe_responses = dupes_with_canonical.map(lambda ((uid1, uid2), (classification, is_canonical)): ((uid2, (uid1, classification, is_canonical)))) \
                                             .join(id_geojson) \
                                             .map(lambda (uid2, ((uid1, classification, canonical), val2)): (uid1, (val2, classification, canonical))) \
                                             .groupByKey() \
                                             .join(id_geojson) \
                                             .map(lambda (uid1, (same_as, value)): (uid1, DedupeResponse.create(value, is_dupe=True, add_random_guid=True, same_as=same_as, explain=explain)))

        non_dupe_responses = id_geojson.subtractByKey(dupes_of) \
                                       .map(lambda (uid, value): (uid, DedupeResponse.base_response(value, is_dupe=False)))

        all_responses = non_dupe_responses.union(dupe_responses) \
                                          .sortByKey() \
                                          .values() \
                                          .map(lambda response: json.dumps(response))

        all_responses.saveAsTextFile(output_path)

        sc.stop()

if __name__ == '__main__':
    DedupeVenuesJob.run()
