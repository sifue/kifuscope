from kiou_eval.engine.usi_parser import normalize_score_for_sente, parse_info_line


def test_parse_cp_info_with_multipv() -> None:
    info = parse_info_line(
        "info depth 14 seldepth 21 multipv 2 score cp -235 nodes 123456 nps 700000 "
        "pv 7g7f 3c3d"
    )
    assert info is not None
    assert info.score_type == "cp"
    assert info.score == -235
    assert info.depth == 14
    assert info.seldepth == 21
    assert info.multipv == 2
    assert info.nodes == 123456
    assert info.pv == ["7g7f", "3c3d"]


def test_parse_mate_info() -> None:
    info = parse_info_line("info depth 20 score mate 7 upperbound pv 5a5b")
    assert info is not None
    assert info.score_type == "mate"
    assert info.score == 7
    assert info.upperbound is True


def test_non_info_line_is_ignored() -> None:
    assert parse_info_line("bestmove 7g7f") is None


def test_normalize_score_for_sente() -> None:
    assert normalize_score_for_sente(120, "b") == 120
    assert normalize_score_for_sente(120, "w") == -120

