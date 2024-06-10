from nltk.corpus import wordnet

words = ["beautiful", "happy", "intelligent"]
synonyms = {}

for word in words:
    syns = wordnet.synsets(word)
    synonyms[word] = [lemma.name() for lemma in syns[0].lemmas()]

print(
    synonyms)  # Output: {'beautiful': ['beautiful', 'pretty', 'lovely', ...], 'happy': ['happy', 'joyful', 'elated', ...], 'intelligent': ['intelligent', 'smart', 'bright', ...]}
