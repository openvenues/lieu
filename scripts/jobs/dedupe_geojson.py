import ujson as json

from lieu.api import DedupeResponse
from lieu.address import Address

from lieu.spark.dedupe import AddressDeduperSpark, NameAddressDeduperSpark
from lieu.word_index import WordIndex

from mrjob.job import MRJob


class DedupeGeoJSONJob(MRJob):
    def configure_options(self):
        super(DedupeGeoJSONJob, self).configure_options()
        self.add_passthrough_option(
            '--address-only',
            action="store_true",
            default=False,
            help="Address duplicates only")

        self.add_passthrough_option(
            '--name-only',
            action="store_true",
            default=False,
            help="Name duplicates only")

        self.add_passthrough_option(
            '--address-only-candidates',
            action='store_true',
            default=False,
            help='Use address-only hash keys for candidate generation, and compare all names at that address pairwise.')

        self.add_passthrough_option(
            '--no-geo-model',
            dest='geo_model',
            default=True,
            action="store_false",
            help="Disables the geo model (if using Spark on a small, local data set)")

        self.add_passthrough_option(
            '--geo-model-proportion',
            type=float,
            default=NameAddressDeduperSpark.DEFAULT_GEO_MODEL_PROPORTION,
            help="Weight to use when ")

        self.add_passthrough_option(
            '--dupes-only',
            action='store_true',
            default=False,
            help='Only output the dupes')

        self.add_passthrough_option(
            '--no-latlon',
            dest='use_latlon',
            default=True,
            action='store_false',
            help='Do not use lat/lon or geohashing (if one data set has no lat/lons for instance)')

        self.add_passthrough_option(
            '--use-city',
            action='store_true',
            default=False,
            help='Use the city for cases where lat/lon is not available (only for local data sets)')

        self.add_passthrough_option(
            '--use-small-containing',
            action='store_true',
            default=False,
            help='Use the small containing boundaries like county as a geo qualifier (only for local data sets)')

        self.add_passthrough_option(
            '--use-postal-code',
            action='store_true',
            default=False,
            help='Use the postcode as a geo qualifier (only for single-country data sets or cases where postcode is unambiguous)')

        self.add_passthrough_option(
            '--no-phone-numbers',
            dest='use_phone_number',
            action='store_false',
            default=True,
            help='Turn off comparison of normalized phone numbers as a postprocessing step (when available). Revises dupe classifications for phone number matches or definite mismatches.'
        )

        self.add_passthrough_option(
            '--no-fuzzy-street-names',
            dest='fuzzy_street_names',
            action='store_false',
            default=True,
            help='Do not use fuzzy street name comparison for minor misspellings, etc. Only use libpostal expansion equality.'
        )

        self.add_passthrough_option(
            '--name-dupe-threshold',
            type=float,
            default=DedupeResponse.default_name_dupe_threshold,
            help='Likely-dupe threshold between 0 and 1 for name deduping with Soft-TFIDF')

        self.add_passthrough_option(
            '--name-review-threshold',
            type=float,
            default=DedupeResponse.default_name_review_threshold,
            help='Human review threshold between 0 and 1 for name deduping with Soft-TFIDF')

        self.add_passthrough_option(
            '--with-unit',
            default=False,
            action="store_true",
            help="Include unit comparisons in deduplication (only if both addresses have unit)")

        self.add_passthrough_option(
            '--index-type',
            choices=[WordIndex.TFIDF, WordIndex.INFORMATION_GAIN],
            default=WordIndex.INFORMATION_GAIN,
            help='Model to use for word relevance')

    def spark(self, input_path, output_path):
        from pyspark import SparkContext

        sc = SparkContext(appName='dedupe geojson MRJob')

        lines = sc.textFile(input_path)

        geojson_lines = lines.map(lambda line: json.loads(line.rstrip()))
        geojson_ids = geojson_lines.cache().zipWithIndex()
        id_geojson = geojson_ids.map(lambda (geojson, uid): (uid, geojson))

        address_ids = geojson_ids.map(lambda (geojson, uid): (Address.from_geojson(geojson), uid))

        geo_model = self.options.geo_model
        index_type = self.options.index_type

        dupes_only = self.options.dupes_only
        address_only_candidates = self.options.address_only_candidates
        use_latlon = self.options.use_latlon
        use_city = self.options.use_city
        use_small_containing = self.options.use_small_containing
        use_postal_code = self.options.use_postal_code
        fuzzy_street_name = self.options.fuzzy_street_names
        geo_model_proportion = self.options.geo_model_proportion
        name_dupe_threshold = self.options.name_dupe_threshold
        name_review_threshold = self.options.name_review_threshold
        with_unit = self.options.with_unit
        with_phone_number = self.options.use_phone_number

        if not self.options.address_only:
            name_only = self.options.name_only
            with_address = not name_only
            name_and_address_keys = with_address
            address_only_keys = address_only_candidates
            name_only_keys = name_only
            dupes_with_classes_and_sims = NameAddressDeduperSpark.dupe_sims(address_ids, geo_model=geo_model, geo_model_proportion=geo_model_proportion, index_type=index_type, name_dupe_threshold=name_dupe_threshold, name_review_threshold=name_review_threshold, with_address=with_address, with_unit=with_unit, with_latlon=use_latlon, with_city_or_equivalent=use_city, with_small_containing_boundaries=use_small_containing, with_postal_code=use_postal_code, fuzzy_street_name=fuzzy_street_name, with_phone_number=with_phone_number, name_and_address_keys=name_and_address_keys, name_only_keys=name_only_keys, address_only_keys=address_only_keys)
        else:
            dupes_with_classes_and_sims = AddressDeduperSpark.dupe_sims(address_ids, with_unit=with_unit, with_latlon=use_latlon, with_city_or_equivalent=use_city, with_small_containing_boundaries=use_containing, with_postal_code=use_postal_code, fuzzy_street_name=fuzzy_street_name)

        dupes = dupes_with_classes_and_sims.filter(lambda ((uid1, uid2), (classification, sim)): classification in (DedupeResponse.classifications.EXACT_DUPE, DedupeResponse.classifications.LIKELY_DUPE)) \
                                           .map(lambda ((uid1, uid2), (classification, sim)): (uid1, True)) \
                                           .distinct()

        possible_dupe_pairs = dupes_with_classes_and_sims.map(lambda ((uid1, uid2), (classification, sim)): (uid1, True)) \
                                                         .distinct()

        canonicals = dupes_with_classes_and_sims.map(lambda ((uid1, uid2), (classification, sim)): (uid2, (uid1, classification, sim))) \
                                                .subtractByKey(dupes) \
                                                .map(lambda (uid2, (uid1, classification, sim)): (uid2, True)) \
                                                .distinct()

        dupes_with_canonical = dupes_with_classes_and_sims.map(lambda ((uid1, uid2), (classification, sim)): (uid2, (uid1, classification, sim))) \
                                                          .leftOuterJoin(canonicals) \
                                                          .map(lambda (uid2, ((uid1, classification, sim), is_canonical)): ((uid1, uid2), (classification, is_canonical or False, sim)))

        if not self.options.address_only:
            explain = DedupeResponse.explain_name_address_dupe(name_likely_dupe_threshold=self.options.name_dupe_threshold,
                                                               name_needs_review_threshold=self.options.name_review_threshold,
                                                               with_unit=self.options.with_unit)
        else:
            explain = DedupeResponse.explain_address_dupe(with_unit=self.options.with_unit)

        dupe_responses = dupes_with_canonical.map(lambda ((uid1, uid2), (classification, is_canonical, sim)): ((uid2, (uid1, classification, is_canonical, sim)))) \
                                             .join(id_geojson) \
                                             .map(lambda (uid2, ((uid1, classification, is_canonical, sim), val2)): (uid1, (val2, classification, is_canonical, sim))) \
                                             .groupByKey() \
                                             .leftOuterJoin(dupes) \
                                             .join(id_geojson) \
                                             .map(lambda (uid1, ((same_as, is_dupe), value)): (uid1, DedupeResponse.create(value, is_dupe=is_dupe or False, add_random_guid=True, same_as=same_as, explain=explain)))

        if dupes_only:
            all_responses = dupe_responses.values() \
                                          .map(lambda response: json.dumps(response))
        else:
            non_dupe_responses = id_geojson.subtractByKey(possible_dupe_pairs) \
                                           .map(lambda (uid, value): (uid, DedupeResponse.base_response(value, is_dupe=False)))

            all_responses = non_dupe_responses.union(dupe_responses) \
                                              .sortByKey() \
                                              .values() \
                                              .map(lambda response: json.dumps(response))

        all_responses.saveAsTextFile(output_path)

        sc.stop()

if __name__ == '__main__':
    DedupeGeoJSONJob.run()
