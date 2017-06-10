import math
import six
import ujson as json

from collections import defaultdict

from lieu.floats import isclose


class TFIDF(object):
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

    @classmethod
    def tfidf_score(cls, term_frequency, doc_frequency, total_docs):
        return math.log(term_frequency + 1.0) * (math.log(float(total_docs) / doc_frequency))

    def tfidf_vector(self, token_counts):
        return [(w, self.tfidf_score(term_frequency=c, doc_frequency=self.idf_counts.get(w, 1.0), total_docs=self.N)) for w, c in token_counts.iteritems()]

    @classmethod
    def normalized_tfidf_vector(cls, tfidf_vector):
        norm = math.sqrt(sum((s ** 2 for w, s in tfidf_vector)))

        if isclose(norm, 0.0):
            return tfidf_vector
        return [(w, s / norm) for w, s in tfidf_vector]
