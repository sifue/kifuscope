import pytest

from kiou_eval.shogi import (
    INITIAL_SFEN,
    BoardState,
    PositionValidationError,
    validate_sfen_position,
)


def test_board_state_round_trip() -> None:
    state = BoardState.from_sfen(INITIAL_SFEN)
    assert state.to_sfen() == INITIAL_SFEN
    state.validate()


def test_board_state_hands_round_trip() -> None:
    sfen = "4k4/9/9/9/9/9/9/9/4K4 w 2R3p 42"
    state = BoardState.from_sfen(sfen)
    assert state.hands == {"R": 2, "p": 3}
    assert state.to_sfen() == sfen


def test_missing_king_is_rejected() -> None:
    state = BoardState.from_sfen("9/9/9/9/9/9/9/9/4K4 b - 1")
    with pytest.raises(PositionValidationError, match="王"):
        state.validate()


def test_nifu_is_rejected() -> None:
    state = BoardState.from_sfen("4k4/9/9/9/4P4/4P4/9/9/4K4 b - 1")
    with pytest.raises(PositionValidationError, match="二歩"):
        state.validate()


def test_validate_sfen_position() -> None:
    assert validate_sfen_position(INITIAL_SFEN).turn == "b"
