

class IDPairRDD(object):
    @classmethod
    def join_pairs(cls, pairs, kvs):
        result = pairs.join(kvs) \
                      .map(lambda (k1, (k2, v1)): (k2, (k1, v1)))

        num_partitions = result.getNumPartitions()

        return result.join(kvs) \
                     .map(lambda (k2, ((k1, v1), v2)): ((k1, k2), (v1, v2))) \
                     .coalesce(num_partitions)

    @classmethod
    def join_pairs_multi_kv(cls, pairs, kvs1, kvs2):
        result = pairs.join(kvs1) \
                      .map(lambda (k1, (k2, v1)): (k2, (k1, v1)))

        num_partitions = result.getNumPartitions()

        return result.join(kvs2) \
                     .map(lambda (k2, ((k1, v1), v2)): ((k1, k2), (v1, v2))) \
                     .coalesce(num_partitions)
