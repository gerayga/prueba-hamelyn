from authors.normalize import clean_name, match_key


def test_clean_name_collapses_whitespace_and_nfc():
    decomposed = "José  Saramago "
    assert clean_name(decomposed) == "José Saramago"


def test_match_key_strips_accents_and_punctuation():
    assert match_key("J. K. Rowling") == "j k rowling"
    assert match_key("Kenzaburō Ōe") == "kenzaburo oe"
    assert match_key("Ngũgĩ wa Thiong'o") == "ngugi wa thiong o"
    assert match_key("Arturo Pérez-Reverte") == "arturo perez reverte"
