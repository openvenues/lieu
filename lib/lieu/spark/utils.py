

class IDPairRDD(object):
    @classmethod
    def join_pairs(cls, pairs, kvs):
        return pairs.join(kvs) \
                    .map(lambda (k1, (k2, v1)): (k2, (k1, v1))) \
                    .join(kvs) \
                    .map(lambda (k2, ((k1, v1), v2)): ((k1, k2), (v1, v2)))
