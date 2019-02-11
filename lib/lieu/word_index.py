import math
from lieu.floats import isclose


class WordIndex(object):
    TFIDF = 'tfidf'
    INFORMATION_GAIN = 'info_gain'

    count_tokens = False

    def vector(self, tokens):
        raise NotImplementedError('Children must implement')

    @classmethod
    def normalized_vector_l1(cls, vector):
        n = float(sum(vector))

        if isclose(n, 0.0):
            n = len(vector)
            if n == 0:
                return []
            return [1. / n] * n
        return [s / n for s in vector]

    @classmethod
    def normalized_vector_l2(cls, vector):
        n = math.sqrt(sum((s ** 2 for s in vector)))

        if isclose(n, 0.0):
            n = len(vector)
            if n == 0:
                return []
            return [1. / n] * n
        return [s / n for s in vector]

    normalized_vector = normalized_vector_l2
