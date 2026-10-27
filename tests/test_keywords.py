from pathlib import Path

import pytest

from council_harvester.config import load_settings
from council_harvester.keywords import is_excluded, match_signal

SIGNALS = {
    "mega_substation": ["umspannwerk", "380 kv"],
    "semiconductor_dc_park": ["halbleiter", "rechenzentrum"],
}


def test_substation_title_matches():
    signal, words = match_signal("Bebauungsplan Nr. 1 - Neubau Umspannwerk Nord", SIGNALS)
    assert signal == "mega_substation"
    assert words == ["umspannwerk"]


def test_dash_and_space_are_the_same():
    signal, words = match_signal("Neue 380-kV-Leitung bis Dresden", SIGNALS)
    assert signal == "mega_substation"
    assert words == ["380 kv"]


def test_german_compound_words_match():
    # "halbleiter" is inside "Halbleiterstandortes"
    signal, words = match_signal("Entwicklung des Halbleiterstandortes Dresden", SIGNALS)
    assert signal == "semiconductor_dc_park"


def test_first_signal_wins_but_all_words_are_kept():
    signal, words = match_signal("Umspannwerk für das neue Rechenzentrum", SIGNALS)
    assert signal == "mega_substation"
    assert words == ["umspannwerk", "rechenzentrum"]


def test_normal_paper_does_not_match():
    assert match_signal("Sanierung der 36. Grundschule", SIGNALS) == (None, [])


@pytest.mark.parametrize("title", [None, "", "   ", 42])
def test_empty_or_weird_titles(title):
    assert match_signal(title, SIGNALS) == (None, [])


def test_exclude_words():
    title = "Kleinprojektförderung für das Projekt TSMC in Dresden"
    assert is_excluded(title, ["kleinprojektförderung"]) is True
    assert is_excluded("Umspannwerk Nord", ["kleinprojektförderung"]) is False
    assert is_excluded(None, ["kleinprojektförderung"]) is False


# real titles from the dresden api, so we notice when the shipped keywords get worse
REAL_TITLES = [
    (
        "Intensivierung der interkommunalen Kooperation zur Entwicklung des europäischen "
        "Halbleiterstandortes in der Region Dresden",
        "semiconductor_dc_park",
    ),
    (
        "Vergabenummer: 2025-GB313-00001 Neu- und Umbau Rechenzentrum RZ E1-Ost SKDF "
        "am Standort Dresden-Friedrichstadt",
        "semiconductor_dc_park",
    ),
    (
        "Kleinprojektförderung des Freien Musikverein Paukenschlag e. V. im Rahmen der "
        "FFRL Stadtbezirke",
        None,
    ),
    ("Weihnachtspyramide und Schwibbogen am Standort Wasaplatz", None),
]


@pytest.mark.parametrize("title, expected", REAL_TITLES)
def test_shipped_keywords_on_real_titles(title, expected):
    settings = load_settings(str(Path(__file__).parent.parent / "config" / "harvester.toml"))
    if is_excluded(title, settings["filter"]["exclude_keywords"]):
        signal = None
    else:
        signal, words = match_signal(title, settings["signals"])
    assert signal == expected
