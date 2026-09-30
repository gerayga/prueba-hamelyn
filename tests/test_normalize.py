from authors.normalize import clean_name, match_key, parse_wikidata_time


def test_clean_name_collapses_whitespace_and_nfc():
    decomposed = "José  Saramago "
    assert clean_name(decomposed) == "José Saramago"


def test_match_key_strips_accents_and_punctuation():
    assert match_key("J. K. Rowling") == "j k rowling"
    assert match_key("Kenzaburō Ōe") == "kenzaburo oe"
    assert match_key("Ngũgĩ wa Thiong'o") == "ngugi wa thiong o"
    assert match_key("Arturo Pérez-Reverte") == "arturo perez reverte"


def test_parse_time_day_precision():
    assert parse_wikidata_time("+1547-09-29T00:00:00Z", 11) == ("1547-09-29", 1547)


def test_parse_time_bce_year_is_not_shifted():
    assert parse_wikidata_time("-0630-00-00T00:00:00Z", 9) == ("-0630", -630)


def test_parse_time_truncates_to_precision():
    assert parse_wikidata_time("+1564-04-01T00:00:00Z", 10) == ("1564-04", 1564)
    assert parse_wikidata_time("-0650-00-00T00:00:00Z", 7) == ("-0650", -650)
