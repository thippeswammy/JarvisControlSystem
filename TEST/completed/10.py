from spellchecker import SpellChecker


def correct_spelling(text):
    spell = SpellChecker()
    words = text.split()

    corrected_text = []
    for word in words:
        corrected_word = spell.correction(word)
        corrected_text.append(corrected_word)

    return ' '.join(corrected_text)


text_with_mistakes = "open notepa"
corrected_text = correct_spelling(text_with_mistakes)
print("Original Text:", text_with_mistakes)
print("Corrected Text:", corrected_text)
