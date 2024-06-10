from nltk.corpus import wordnet

syns = wordnet.synsets("beautiful")[0].lemmas()
synonyms = [lemma.name() for lemma in syns]

print(synonyms)  # Output: ['beautiful', 'pretty', 'lovely', ...]
