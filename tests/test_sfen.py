import pytest

from kiou_eval.shogi import INITIAL_SFEN, SfenError, parse_sfen


def test_parse_initial_sfen() -> None:
    position = parse_sfen(INITIAL_SFEN)
    assert position.turn == "b"
    assert position.move_number == 1
    assert position.hands == "-"


@pytest.mark.parametrize(
    "sfen",
    [
        "9/9/9 b - 1",
        "9/9/9/9/9/9/9/9/8 b - 1",
        "9/9/9/9/9/9/9/9/9 x - 1",
        "9/9/9/9/9/9/9/9/9 b - 0",
        "9/9/9/9/9/9/9/9/9 b 1P 1",
    ],
)
def test_invalid_sfen(sfen: str) -> None:
    with pytest.raises(SfenError):
        parse_sfen(sfen)

