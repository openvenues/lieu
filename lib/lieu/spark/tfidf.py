import math

from collections import Counter

from lieu.tfidf import TFIDF


class TFIDFSpark(object):
    @classmethod
    def doc_word_counts(cls, docs, has_id=False):
        if not has_id:
            docs = docs.zipWithUniqueId()

        doc_word_counts = docs.flatMap(lambda (doc, doc_id): [(word, (doc_id, count)) for word, count in Counter(doc.lower().split()).items()])
        return doc_word_counts

    @classmethod
    def doc_frequency(cls, doc_word_counts):
        doc_frequency = doc_word_counts.map(lambda (word, (doc_id, count)): (word, 1)).reduceByKey(lambda x, y: x + y)
        return doc_frequency

    @classmethod
    def filter_min_doc_frequency(cls, doc_frequency, min_count=2):
        return doc_frequency.filter(lambda (word, count): count >= min_count)

    @classmethod
    def update_doc_frequency(cls, doc_frequency, batch_frequency):
        updated = doc_frequency.union(batch_frequency).reduceByKey(lambda x, y: x + y)
        return updated

    @classmethod
    def docs_tfidf(cls, doc_word_counts, doc_frequency, total_docs, min_count=1, has_id=False):
        if min_count > 1:
            doc_frequency = cls.filter_min_doc_frequency(doc_frequency, min_count=min_count)
        doc_ids_word_stats = doc_word_counts.join(doc_frequency).map(lambda (word, ((doc_id, term_frequency), doc_frequency)): (doc_id, (word, term_frequency, doc_frequency)))
        docs_tfidf = doc_ids_word_stats.groupByKey().map(lambda (key, vals): (key, {word: TFIDF.tfidf_score(term_frequency, doc_frequency, total_docs) for word, term_frequency, doc_frequency in vals}))
        return docs_tfidf
