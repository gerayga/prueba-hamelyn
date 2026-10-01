from authors.enrich import classify_name_type, count_references, pick_date


def claim(time, precision, rank="normal", refs=()):
    return {
        "rank": rank,
        "mainsnak": {"snaktype": "value", "datavalue": {"value": {
            "time": time, "precision": precision,
            "calendarmodel": "http://www.wikidata.org/entity/Q1985727"}}},
        "references": [{"snaks": {p: [] for p in r}} for r in refs],
    }


def test_preferred_rank_wins_over_more_precise_normal():
    date, conflict = pick_date([
        claim("+0973-00-00T00:00:00Z", 9),
        claim("+0970-00-00T00:00:00Z", 8, rank="preferred"),
    ])
    assert date["date"] == "0970" and date["precision"] == "decade" and not conflict


def test_deprecated_is_ignored():
    date, _ = pick_date([claim("+1900-01-01T00:00:00Z", 11, rank="deprecated"),
                         claim("+1901-00-00T00:00:00Z", 9)])
    assert date["year"] == 1901


def test_tie_broken_by_references_ignoring_p143():
    # Caso Ismat Chughtai: varias fechas de día con rango normal.
    date, conflict = pick_date([
        claim("+1911-08-21T00:00:00Z", 11, refs=[("P854", "P813")]),
        claim("+1915-08-21T00:00:00Z", 11, refs=[("P143",), ("P143",), ("P143",)]),
        claim("+1915-08-15T00:00:00Z", 11, refs=[("P854", "P813"), ("P248",)]),
    ])
    assert date["date"] == "1915-08-15" and conflict


def test_count_references_excludes_imported_from():
    assert count_references(claim("+1900-00-00T00:00:00Z", 9, refs=[("P143",), ("P248",)])) == 1


def test_unknown_value_is_skipped():
    unknown = {"rank": "normal", "mainsnak": {"snaktype": "somevalue"}}
    assert pick_date([unknown]) == (None, False)


def test_name_type_pseudonym_wins_over_main_label():
    names = {"pseudonym": {"mark twain"}, "main": {"mark twain"},
             "birth_name": {"samuel langhorne clemens"}}
    assert classify_name_type("mark twain", names) == "pseudonym"


def test_name_type_birth_name_by_token_subset():
    names = {"main": {"mark twain"}, "birth_name": {"samuel langhorne clemens"},
             "alias": {"samuel clemens"}}
    assert classify_name_type("samuel clemens", names) == "birth_name"


def test_name_type_single_token_is_not_birth_name_subset():
    # 'samuel' a secas no debe contar como nombre de nacimiento.
    assert classify_name_type("samuel", {"birth_name": {"samuel langhorne clemens"}}) == "other"


def test_name_type_alias_and_other():
    names = {"main": {"fyodor dostoyevsky"}, "alias": {"fyodor dostoevsky"}}
    assert classify_name_type("fyodor dostoevsky", names) == "alias"
    assert classify_name_type("andrey platonov", {"main": {"andrei platonov"}}) == "other"


def test_name_type_short_form_is_not_birth_name():
    names = {"main": {"pedro calderon de la barca"},
             "birth_name": {"pedro calderon de la barca y barreda"},
             "alias": {"calderon de la barca"}}
    assert classify_name_type("calderon de la barca", names) == "alias"
