import csv
import itertools
import math
import six

from collections import defaultdict

from lieu.encoding import safe_decode
from lieu.word_index import WordIndex


class InformationGain(WordIndex):
    def __init__(self, info_gain):
        self.info_gain = info_gain

    def write(self, f):
        writer = csv.writer(f, delimiter='\t')
        for k, v in six.iteritems(self.info_gain):
            writer.writerow([safe_decode(k), safe_decode(v)])

    def save(self, filename):
        f = open(filename, 'w')
        self.write(f)
        f.close()

    @classmethod
    def read(cls, f):
        reader = csv.reader(f, delimiter='\t')

        info_gain = {}
        for key, val in reader:
            val = float(val)
            key = safe_decode(key)
            info_gain[key] = val
        return info_gain

    @classmethod
    def load(cls, filename):
        f = open(filename)
        info_gain = cls.read(f)
        ig = cls(info_gain)
        return ig

    def vector(self, tokens):
        return [self.info_gain.get(w, 0.0) for w in tokens]


class InformationGainBuilder(object):
    def __init__(self):
        self.word_ids = {}
        self.words = []
        self.marginals = defaultdict(int)
        self.num_docs = 0
        self.cooccurrences = defaultdict(lambda: defaultdict(int))

    def word_id(self, word):
        i = self.word_ids.get(word)
        if i is None:
            i = len(self.word_ids)
            self.word_ids[word] = i
            self.words.append(word)
        return i

    def update(self, tokens):
        words = set(tokens)
        word_ids = set([self.word_id(w) for w in words])
        for i in word_ids:
            self.marginals[i] += 1
        self.num_docs += 1

        for i, j in itertools.permutations(word_ids, 2):
            self.cooccurrences[i][j] += 1

    def finalize(self):
        info_gain = {}

        n = self.num_docs
        p_marginals = {k: float(v) / n for k, v in six.iteritems(self.marginals)}

        for y, vals in six.iteritems(self.cooccurrences):
            n_y = sum(six.itervalues(vals))
            sum_info = 0.0
            for x, c in six.iteritems(vals):
                p_xy = float(c) / n_y
                p_x = p_marginals[x]
                info = math.log(p_xy / p_x, 2) * p_xy
                sum_info += info
            word = self.words[y]
            info_gain[word] = max(sum_info, 0.0)

        info_gain.update({word: math.log(1.0 / p_marginals[word_id], 2) for word, word_id in six.iteritems(self.word_ids) if word not in info_gain})

        del self.cooccurrences
        del self.marginals
        del self.word_ids
        del self.words
        self.cooccurrences = None
        self.marginals = None
        self.word_ids = None
        self.words = None

        return InformationGain(info_gain)
