"""前局面からの合法手候補照合と連続フレーム安定化。"""

from __future__ import annotations

from dataclasses import dataclass

import cshogi

from .board_state import HAND_ORDER, UNKNOWN, BoardObservation, BoardState


@dataclass(frozen=True, slots=True)
class CandidateMatch:
    state: BoardState
    move_usi: str | None
    score: float
    margin: float


@dataclass(frozen=True, slots=True)
class TrackingResult:
    status: str
    message: str
    state: BoardState
    move_usi: str | None
    confidence: float
    stable_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "message": self.message,
            "sfen": self.state.to_sfen(),
            "move": self.move_usi,
            "confidence": self.confidence,
            "stable_count": self.stable_count,
        }


class LegalMoveMatcher:
    """現局面自身と全合法手後の局面から観測に最も一致する候補を探す。"""

    def __init__(self, *, threshold: float = 0.90, margin: float = 0.02) -> None:
        self.threshold = threshold
        self.required_margin = margin
        self.last_best: CandidateMatch | None = None

    def find(self, current: BoardState, observation: BoardObservation) -> CandidateMatch | None:
        candidates = [(current, None), *self._successors(current)]
        scored = sorted(
            (
                CandidateMatch(state, move, self._score(state, observation), 0.0)
                for state, move in candidates
            ),
            key=lambda candidate: candidate.score,
            reverse=True,
        )
        best = scored[0]
        second_score = scored[1].score if len(scored) > 1 else 0.0
        margin = best.score - second_score
        self.last_best = CandidateMatch(best.state, best.move_usi, best.score, margin)
        if best.score < self.threshold:
            return None
        if best.move_usi is None:
            return CandidateMatch(best.state, best.move_usi, best.score, margin)
        if margin < self.required_margin:
            return None
        return CandidateMatch(best.state, best.move_usi, best.score, margin)

    @staticmethod
    def _successors(current: BoardState) -> list[tuple[BoardState, str]]:
        board = cshogi.Board(current.to_sfen())
        successors: list[tuple[BoardState, str]] = []
        for move in list(board.legal_moves):
            next_board = board.copy()
            next_board.push(move)
            successors.append((BoardState.from_sfen(next_board.sfen()), cshogi.move_to_usi(move)))
        return successors

    @staticmethod
    def _score(candidate: BoardState, observation: BoardObservation) -> float:
        board_weight = 0.0
        board_score = 0.0
        for expected, observed, confidence in zip(
            candidate.squares,
            observation.squares,
            observation.square_confidences,
            strict=True,
        ):
            if observed is UNKNOWN:
                continue
            weight = max(0.05, confidence)
            board_weight += weight
            if observed == expected:
                board_score += weight

        components: list[tuple[float, float]] = []
        if board_weight:
            components.append((0.80, board_score / board_weight))
        if observation.hands is not None:
            matches = sum(
                candidate.hands.get(piece, 0) == observation.hands.get(piece, 0)
                for piece in HAND_ORDER
            )
            components.append((0.15, matches / len(HAND_ORDER)))
        if observation.turn is not None:
            components.append((0.05, float(candidate.turn == observation.turn)))
        if not components:
            return 0.0
        weight_sum = sum(weight for weight, _ in components)
        return sum(weight * score for weight, score in components) / weight_sum


class StableLegalTracker:
    """同じ合法手候補が連続して観測された場合だけ局面を更新する。"""

    def __init__(
        self,
        initial: BoardState,
        *,
        stable_frames: int = 3,
        threshold: float = 0.90,
        margin: float = 0.02,
    ) -> None:
        initial.validate()
        if stable_frames < 1:
            raise ValueError("stable_framesは1以上で指定してください")
        self.current = initial
        self.stable_frames = stable_frames
        self.matcher = LegalMoveMatcher(threshold=threshold, margin=margin)
        self._pending_sfen: str | None = None
        self._pending_move: str | None = None
        self._stable_count = 0

    def update(self, observation: BoardObservation) -> TrackingResult:
        match = self.matcher.find(self.current, observation)
        if match is None:
            self._clear_pending()
            detail = ""
            if self.matcher.last_best is not None:
                best = self.matcher.last_best
                detail = (
                    f"（最有力候補: move={best.move_usi or '現局面'}, "
                    f"score={best.score:.3f}, margin={best.margin:.3f}）"
                )
                if best.move_usi is None and best.score < self.matcher.threshold:
                    detail += (
                        "。KIOU画面が追跡開始局面から進んでいる、または"
                        "初期局面SFENと画面が一致していない可能性があります"
                    )
            return TrackingResult(
                "recognition_failed",
                f"前局面または合法手後の局面に一致しません{detail}",
                self.current,
                None,
                observation.confidence,
                0,
            )
        if match.move_usi is None:
            self._clear_pending()
            return TrackingResult(
                "ok", "局面に変化はありません", self.current, None, match.score, self.stable_frames
            )

        candidate_sfen = match.state.to_sfen()
        if candidate_sfen == self._pending_sfen:
            self._stable_count += 1
        else:
            self._pending_sfen = candidate_sfen
            self._pending_move = match.move_usi
            self._stable_count = 1
        if self._stable_count < self.stable_frames:
            return TrackingResult(
                "position_unconfirmed",
                "合法手候補の安定を待っています",
                self.current,
                match.move_usi,
                match.score,
                self._stable_count,
            )

        accepted_move = self._pending_move
        self.current = match.state
        self._clear_pending()
        return TrackingResult(
            "ok",
            "合法手として局面を確定しました",
            self.current,
            accepted_move,
            match.score,
            self.stable_frames,
        )

    def _clear_pending(self) -> None:
        self._pending_sfen = None
        self._pending_move = None
        self._stable_count = 0
