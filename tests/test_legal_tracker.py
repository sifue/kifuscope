import cshogi

from kiou_eval.shogi import (
    INITIAL_SFEN,
    UNKNOWN,
    BoardObservation,
    BoardState,
    StableLegalTracker,
)


def _observation(state: BoardState) -> BoardObservation:
    return BoardObservation(state.squares, (1.0,) * 81, state.hands, state.turn, 1.0)


def _board_only_observation(state: BoardState) -> BoardObservation:
    return BoardObservation(state.squares, (1.0,) * 81, None, None, 1.0)


def _after_move(usi: str) -> BoardState:
    board = cshogi.Board(INITIAL_SFEN)
    board.push_usi(usi)
    return BoardState.from_sfen(board.sfen())


def test_legal_move_requires_stable_frames() -> None:
    tracker = StableLegalTracker(BoardState.from_sfen(INITIAL_SFEN), stable_frames=2)
    observed = _observation(_after_move("7g7f"))
    first = tracker.update(observed)
    second = tracker.update(observed)
    assert first.status == "position_unconfirmed"
    assert first.stable_count == 1
    assert second.status == "ok"
    assert second.move_usi == "7g7f"
    assert tracker.current.turn == "w"


def test_legal_move_can_be_tracked_from_board_only_observation() -> None:
    tracker = StableLegalTracker(BoardState.from_sfen(INITIAL_SFEN), stable_frames=1)
    result = tracker.update(_board_only_observation(_after_move("7g7f")))
    assert result.status == "ok"
    assert result.move_usi == "7g7f"
    assert result.state.turn == "w"
    assert result.state.hands == {}


def test_unchanged_position_is_kept() -> None:
    initial = BoardState.from_sfen(INITIAL_SFEN)
    result = StableLegalTracker(initial).update(_observation(initial))
    assert result.status == "ok"
    assert result.move_usi is None


def test_unknown_observation_is_rejected() -> None:
    initial = BoardState.from_sfen(INITIAL_SFEN)
    observation = BoardObservation((UNKNOWN,) * 81, (0.0,) * 81, None, None, 0.0)
    result = StableLegalTracker(initial).update(observation)
    assert result.status == "recognition_failed"
