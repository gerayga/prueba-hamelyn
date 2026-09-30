from authors.resolve import Candidate, classify_name_match, decide, score_candidate


def cand(qid, name_match="exact_label", human=True, writer=True, works=False, sitelinks=50):
    c = Candidate(qid, 0, qid, None, name_match, is_human=human, is_writer=writer,
                  has_works=works, sitelinks=sitelinks)
    c.score = score_candidate(c)
    return c


def test_classify_prefers_label_over_reported_alias():
    # La API a veces informa del alias largo aunque la etiqueta sea exacta.
    assert classify_name_match("almudena grandes", "Almudena Grandes",
                               "alias", "Almudena Grandes Hernández") == "exact_label"


def test_classify_alias_and_partial():
    assert classify_name_match("robert galbraith", "J. K. Rowling",
                               "alias", "Robert Galbraith") == "alias"
    assert classify_name_match("homer", "Homer Simpson", "label", "Homer Simpson") == "partial"


def test_non_human_scores_zero():
    assert cand("Q1", human=False).score == 0.0


def test_writer_beats_popular_non_writer_with_same_name():
    writer = cand("Q_writer", sitelinks=20)
    footballer = cand("Q_other", writer=False, sitelinks=150)
    assert writer.score > footballer.score


def test_decide_matched_with_clear_margin():
    status, best, conf, _ = decide([cand("Q1", sitelinks=200), cand("Q2", "partial", writer=False, sitelinks=5)])
    assert status == "matched" and best.qid == "Q1" and conf >= 0.6


def test_decide_ambiguous_when_two_similar_writers():
    status, best, _, note = decide([cand("Q1", sitelinks=40), cand("Q2", sitelinks=35)])
    assert status == "ambiguous" and best.qid == "Q1" and "margen" in note


def test_decide_ambiguous_when_not_literary():
    status, _, _, note = decide([cand("Q1", writer=False, sitelinks=200)])
    assert status == "ambiguous" and "literaria" in note


def test_decide_no_match_without_humans():
    status, best, _, _ = decide([cand("Q1", human=False)])
    assert status == "no_match" and best is None


def test_decide_dominance_overrides_small_margin():
    # Caso John Milton: el homónimo (su padre) también es escritor pero muy menor.
    status, best, _, _ = decide([cand("Q79759", sitelinks=155), cand("Q3809493", sitelinks=5)])
    assert status == "matched" and best.qid == "Q79759"


def test_decide_similar_notability_stays_ambiguous():
    # Caso Mary Beard: 38 vs 28 sitelinks, ambas historiadoras.
    status, _, _, _ = decide([cand("Q458403", sitelinks=38), cand("Q6780609", sitelinks=28)])
    assert status == "ambiguous"
