import csv
import math
import six
import ujson as json

from collections import defaultdict

from lieu.encoding import safe_encode, safe_decode
from lieu.floats import isclose


class TFIDF(object):
    finalized = False

    term_key_prefix = 't:'
    doc_count_key = 'N'

    def __init__(self):
        self.idf_counts = defaultdict(int)
        self.N = 0

    def update(self, doc):
        if self.finalized or not doc:
            return

        for feature, count in six.iteritems(doc):
            self.idf_counts[feature] += 1

        self.N += 1

    def serialize(self):
        return json.dumps({
            'N': self.N,
            'idf_counts': dict(self.idf_counts)
        })

    def write(self, f):
        writer = csv.writer(f, delimiter='\t')
        for k, v in six.iteritems(self.idf_counts):
            writer.writerow([safe_encode(u'{}{}'.format(self.term_key_prefix, safe_decode(k))), six.text_type(v)])
        writer.writerow([self.doc_count_key, six.text_type(self.N)])

    def save(self, filename):
        f = open(filename, 'w')
        self.write(f)
        f.close()

    def read(self, f):
        reader = csv.reader(f, delimiter='\t')
        term_prefix_len = len(self.term_key_prefix)
        for key, val in reader:
            val = long(val)
            key = safe_decode(key)
            if key.startswith(self.term_key_prefix):
                key = key[term_prefix_len:]

                self.idf_counts[key] += val
            elif key == self.doc_count_key:
                self.N += val

    @classmethod
    def load(cls, filename):
        f = open(filename)
        idf = cls()
        idf.read(f)
        return idf

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
