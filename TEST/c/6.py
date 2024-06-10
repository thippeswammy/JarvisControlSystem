from gensim.models import Word2Vec

model = Word2Vec.load("path/to/word2vec_model.model")

similar_words = model.most_similar("happy")

print(similar_words)  # Output: [('delighted', 0.75), ('joyful', 0.72), ('elated', 0.71), ...]
