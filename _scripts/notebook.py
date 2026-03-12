import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    # Read in source data
    from itertools import combinations
    from pprint import pprint

    from amphetype.lesson_builder import common_words

    source_words = []
    source_words.extend(common_words.get_medium_words())
    source_words.extend(common_words.get_short_words())

    # Create lessons for the bottom row of qwerty keyboard layout
    bottom_row_chars = "zxcvbnm"
    pairs = list(combinations(bottom_row_chars, 2))

    lessons = {}
    for pair in pairs:
      pair_words = [word for word in source_words if (pair[0] in word and pair[1] in word)]
      lessons[pair] = pair_words

    for pair, lesson in lessons.items():
      pprint(f"{pair}: {len(lesson)}")
    return lessons, pprint


@app.cell
def _(lessons, pprint):
    # Extract all trigram from common words
    import more_itertools

    z_words =[]

    for k, v in lessons.items():
      if "z" in k:
        z_words.extend(v)

    z_ngrams = []

    for word in z_words:
      sub_str = more_itertools.substrings(word)
      ngram = ["".join(s) for s in list(sub_str) if 1 < len(s) <= 3]
      z_only = [item for item in ngram if "z" in item]
      z_ngrams.extend(set(z_only))

    pprint(z_ngrams)
    return


if __name__ == "__main__":
    app.run()
