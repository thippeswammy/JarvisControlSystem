from textblob import TextBlob

# Sentence with errors
sentence = "I has seen a nice movie yesterday."

# Correct the sentence with TextBlob
corrected_sentence = TextBlob(sentence).correct()

# Print the corrected sentence
print(corrected_sentence)
