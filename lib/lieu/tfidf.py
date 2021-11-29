import csv
import math
import six
import json

from collections import defaultdict, Counter

from lieu.encoding import safe_decode
from lieu.floats import isclose
from lieu.word_index import WordIndex


class TFIDF(WordIndex):
    finalized = False

    count_tokens = True

    term_key_prefix = 't:'
    doc_count_key = 'N'

    def __init__(self, min_count=1):
        self.idf_counts = defaultdict(int)
        self.N = 0
        self.min_count = min_count

    def update(self, doc):
        if self.finalized or not doc:
            return

        for feature, count in six.iteritems(Counter(doc)):
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
            writer.writerow([safe_decode('{}{}'.format(self.term_key_prefix, safe_decode(k))), safe_decode(v)])
        writer.writerow([self.doc_count_key, safe_decode(self.N)])

    def save(self, filename):
        f = open(filename, 'w')
        self.write(f)
        f.close()

    def read(self, f):
        reader = csv.reader(f, delimiter='\t')
        term_prefix_len = len(self.term_key_prefix)
        for key, val in reader:
            val = int(val)
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
        self.idf_counts = {k: count for k, count in six.iteritems(self.idf_counts) if count >= min_count}

    def finalize(self):
        if self.min_count > 1:
            self.prune(self.min_count)
        self.finalized = True
        return self

    def corpus_frequency(self, key):
        return self.idf_counts.get(key, 0)

    @classmethod
    def tfidf_score(cls, term_frequency, doc_frequency, total_docs):
        return math.log(term_frequency + 1.0) * (math.log(float(total_docs) / doc_frequency))

    def vector(self, tokens):
        return [self.tfidf_score(term_frequency=1.0, doc_frequency=self.idf_counts.get(w, 1.0), total_docs=self.N) for w in tokens]

    @classmethod
    def normalized_vector(cls, vector):
        n = math.sqrt(sum((s ** 2 for s in vector)))

        if isclose(n, 0.0):
            n = len(vector)
            return [1. / n] * n
        return [s / n for s in vector]
