import math
from lieu.floats import isclose


class WordIndex(object):
    TFIDF = 'tfidf'
    INFORMATION_GAIN = 'info_gain'

    def vector(self, tokens):
        raise NotImplementedError('Children must implement')

    @classmethod
    def normalized_vector(cls, vector):
        norm = math.sqrt(sum((s ** 2 for s in vector)))

        if isclose(norm, 0.0):
            n = len(vector)
            return [1. / n] * n
        return [s / norm for s in vector]
