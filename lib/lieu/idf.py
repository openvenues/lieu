import math
import ujson as json

from collections import defaultdict

from lieu.floats import isclose


class IDFIndex(object):
    finalized = False

    def __init__(self):
        self.idf_counts = defaultdict(int)
        self.N = 0

    def update(self, doc):
        if self.finalized or not doc:
            return

        for feature, count in doc.iteritems():
            self.idf_counts[feature] += 1

        self.N += 1

    def serialize(self):
        return json.dumps({
            'N': self.N,
            'idf_counts': dict(self.idf_counts)
        })

    def write(self, f):
        f.write(self.serialize())

    def save(self, filename):
        f = open(filename, 'w')
        self.write(f)

    @classmethod
    def read(cls, f):
        data = json.load(f)
        idf = cls()
        idf.N = data['N']
        idf.idf_counts.update(data['idf_counts'])
        return idf

    @classmethod
    def load(cls, filename):
        f = open(filename)
        return cls.read(f)

    def prune(self, min_count):
        self.idf_counts = {k: count for k, count in self.idf_counts.iteritems() if count >= min_count}

    def corpus_frequency(self, key):
        return self.idf_counts.get(key, 0)

    def tfidf_score(self, key, count=1):
        if count < 0:
            return 0.0

        idf_count = self.idf_counts.get(key, None)
        if idf_count is None:
            return 0.0
        return (math.log(count + 1.0) * (math.log(float(self.N) / idf_count)))

    def normalized_tfidf_vector(self, token_counts):
        tf_idf = [self.tfidf_score(t, count=c) for t, c in token_counts.iteritems()]
        norm = math.sqrt(sum((t ** 2 for t in tf_idf)))
        if isclose(norm, 0.0):
            return tf_idf
        return [t / norm for t in tf_idf]
