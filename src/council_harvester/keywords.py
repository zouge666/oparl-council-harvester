"""finds out if a paper title is about one of our signal types.

the keyword lists live in config/harvester.toml under [signals].
we only look at the title, not at the pdf files.
"""


def clean_text(text):
    # lower case and no dashes, so "380-kV" and "380 kV" look the same
    return text.lower().replace("-", " ")


def is_excluded(title, exclude_words):
    """true if the title has one of the exclude words in it"""
    if not isinstance(title, str):
        return False
    text = clean_text(title)
    for word in exclude_words:
        if clean_text(word) in text:
            return True
    return False


def match_signal(title, signals):
    """checks a title against the keyword lists.

    gives back (signal_type, matched_keywords). signal_type is None if nothing matched.
    if keywords from two signal types match, the first type in the config wins,
    but we still keep all matched keywords.
    """
    if not isinstance(title, str) or not title.strip():
        return None, []

    text = clean_text(title)
    signal_type = None
    matched = []
    for name, keywords in signals.items():
        for keyword in keywords:
            if clean_text(keyword) in text:
                matched.append(keyword)
                if signal_type is None:
                    signal_type = name
    return signal_type, matched
