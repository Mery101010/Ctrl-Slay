"""
Fits ONE TF-IDF vectorizer + TruncatedSVD (LSA) across reviews + roadmap
issue text, so every downstream comparison (theme-to-theme, theme-to-
roadmap) happens in the same vector space.

Uses a stemming tokenizer (Porter stemmer) - this matters more than it
sounds: confirmed on the real Western Union corpus that without stemming,
a 211-review cluster about the app "crashing"/"freezing" scored only 0.094
similarity to the GitHub issue titled "crash and freeze triage" - LOWER
than its similarity to an unrelated issue - purely because "crashing" and
"crash" are different literal tokens to unstemmed TF-IDF. Stemming fixes
this specific, confirmed failure mode.

The SVD step matters beyond just dimensionality reduction: it smooths raw
TF-IDF's literal-keyword-only similarity by picking up co-occurring term
structure, which noticeably improves cluster quality at real corpus sizes
(see feedback_agent.py comments for what was tried and why).

Swap for a real embedding model (Voyage AI, sentence-transformers) later —
nothing downstream needs to change, they only consume vectors + cosine
similarity.
"""

import re
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.decomposition import TruncatedSVD
from nltk.stem import PorterStemmer

_stemmer = PorterStemmer()
_token_re = re.compile(r"[a-zA-Z]{2,}")
# Stop words must be stemmed too, or stemmed tokens like "wa" (was),
# "onli" (only) silently stop matching the unstemmed stopword list and
# leak into the vocabulary as noise - confirmed via sklearn's own warning
# when this wasn't done.
_STEMMED_STOP_WORDS = list({_stemmer.stem(w) for w in ENGLISH_STOP_WORDS})


def _stem_tokenizer(text):
    return [_stemmer.stem(tok) for tok in _token_re.findall(text.lower())]


def fit_shared_space(all_texts: list, n_components: int = 100):
    vectorizer = TfidfVectorizer(tokenizer=_stem_tokenizer, stop_words=_STEMMED_STOP_WORDS,
                                  max_features=5000, min_df=5, ngram_range=(1, 2),
                                  token_pattern=None)
    tfidf = vectorizer.fit_transform(all_texts)

    n_components = min(n_components, tfidf.shape[0] - 1, tfidf.shape[1] - 1)
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    svd.fit(tfidf)

    return vectorizer, svd
