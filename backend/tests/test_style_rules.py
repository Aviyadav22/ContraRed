from __future__ import annotations
from app.services.drafting.style_rules import (
    normalize_shall_will,
    normalize_number_words,
    normalize_efforts_standard,
    remove_archaisms,
    format_defined_term_first_use,
)


def test_shall_will_normalization_to_shall():
    text = 'The Company will deliver the goods. The Vendor will pay on time.'
    result = normalize_shall_will(text, preference="shall")
    assert "shall deliver" in result
    assert "shall pay" in result
    assert "will deliver" not in result


def test_shall_will_normalization_to_will():
    text = 'The Company shall deliver. The Vendor shall pay.'
    result = normalize_shall_will(text, preference="will")
    assert "will deliver" in result
    assert "shall pay" not in result


def test_shall_will_skips_future_tense():
    text = 'This Agreement will expire on the date set forth above.'
    result = normalize_shall_will(text, preference="shall")
    assert "will expire" in result


def test_number_word_pairs():
    text = "within 30 days of notice"
    result = normalize_number_words(text)
    assert "thirty (30) days" in result


def test_number_word_pairs_already_correct():
    text = "within thirty (30) days"
    result = normalize_number_words(text)
    assert "thirty (30) days" in result


def test_number_word_large():
    text = "not to exceed 12 months"
    result = normalize_number_words(text)
    assert "twelve (12) months" in result


def test_efforts_standard_normalization():
    text = 'Party shall use best efforts to obtain consent. Party shall use commercially reasonable efforts to deliver.'
    result = normalize_efforts_standard(text)
    assert "reasonable efforts" in result
    assert "best efforts" not in result
    assert "commercially reasonable efforts" not in result


def test_remove_archaisms():
    text = "The party herein agrees to the terms hereof and hereby acknowledges thereof."
    result = remove_archaisms(text)
    assert "herein" not in result
    assert "hereof" not in result
    assert "hereby" not in result
    assert "thereof" not in result


def test_format_defined_term_first_use():
    text = 'The Confidential Information means all data. The Receiving Party shall protect Confidential Information.'
    defined = {"Confidential Information", "Receiving Party"}
    result = format_defined_term_first_use(text, defined)
    assert '\u201cConfidential Information\u201d' in result or '"Confidential Information"' in result
