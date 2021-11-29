import json
import bz2

class GeoJSONParser(object):
    def __init__(self, filename):
        self.i = 0
        self.data = json.load(open(filename))
        self.features = self.data.get('features', [])
        self.num_features = len(self.features)

    def __iter__(self):
        self.i = 0
        return self

    def next_feature(self):
        if self.i < self.num_features:
            feature = self.data['features'][self.i]
            self.i += 1
            return feature
        else:
            raise StopIteration

    def __next__(self):
        return self.next_feature()


class GeoJSONLineParser(GeoJSONParser):
    def __init__(self, filename):
        if filename.endswith(".bz2"):
            self.f = bz2.BZ2File(filename)
        else:
            self.f = open(filename)

    def next_feature(self):
        return json.loads(next(self.f).rstrip())
