from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Standing:
    player_id: int
    name: str
    course: str
    center: str
    points: float
    buchholz: float
    wins: int
    played: int
    color_balance: int
    had_bye: bool


def calculate_standings(players: Iterable, history: Iterable) -> list[Standing]:
    players = list(players)
    history = list(history)
    stats = {
        int(p["id"]): {"points": 0.0, "wins": 0, "played": 0, "balance": 0, "bye": False, "opponents": []}
        for p in players
    }
    for game in history:
        white, black, result = int(game["white_id"]), game["black_id"], game["result"]
        if white not in stats or not result:
            continue
        if black is None:
            stats[white]["points"] += 1.0
            stats[white]["played"] += 1
            stats[white]["bye"] = True
            continue
        black = int(black)
        if black not in stats:
            continue
        stats[white]["opponents"].append(black)
        stats[black]["opponents"].append(white)
        stats[white]["played"] += 1
        stats[black]["played"] += 1
        stats[white]["balance"] += 1
        stats[black]["balance"] -= 1
        if result == "1-0":
            stats[white]["points"] += 1
            stats[white]["wins"] += 1
        elif result == "0-1":
            stats[black]["points"] += 1
            stats[black]["wins"] += 1
        elif result == "1/2-1/2":
            stats[white]["points"] += 0.5
            stats[black]["points"] += 0.5

    result = []
    for player in players:
        player_id = int(player["id"])
        own = stats[player_id]
        buchholz = sum(stats[opponent]["points"] for opponent in own["opponents"])
        result.append(Standing(
            player_id=player_id,
            name=f"{player['first_name']} {player['last_name']}",
            course=player["course"], center=player["center"],
            points=own["points"], buchholz=buchholz, wins=own["wins"],
            played=own["played"], color_balance=own["balance"], had_bye=own["bye"],
        ))
    return sorted(result, key=lambda s: (-s.points, -s.buchholz, -s.wins, s.name.casefold()))


def generate_pairings(players: Iterable, history: Iterable) -> list[tuple[int, int | None]]:
    standings = calculate_standings(players, history)
    if len(standings) < 2:
        raise ValueError("Se necesitan al menos 2 alumnos activos para emparejar.")

    previous = set()
    for game in history:
        if game["black_id"] is not None:
            previous.add(frozenset((int(game["white_id"]), int(game["black_id"]))))

    bye = None
    pool = standings[:]
    if len(pool) % 2:
        candidates = [s for s in reversed(pool) if not s.had_bye] or list(reversed(pool))
        bye = candidates[0]
        pool.remove(bye)

    rank = {s.player_id: index for index, s in enumerate(standings)}

    def pair_cost(a: Standing, b: Standing) -> float:
        repeat = 10_000 if frozenset((a.player_id, b.player_id)) in previous else 0
        score_gap = abs(a.points - b.points) * 100
        rank_gap = abs(rank[a.player_id] - rank[b.player_id])
        same_center = 3 if a.center and a.center == b.center else 0
        return repeat + score_gap + rank_gap + same_center

    def search(remaining: list[Standing]) -> tuple[float, list[tuple[Standing, Standing]]]:
        if not remaining:
            return 0.0, []
        first = remaining[0]
        best_cost, best_pairs = float("inf"), []
        for i, opponent in enumerate(remaining[1:], 1):
            rest = remaining[1:i] + remaining[i + 1:]
            tail_cost, tail_pairs = search(rest)
            cost = pair_cost(first, opponent) + tail_cost
            if cost < best_cost:
                best_cost, best_pairs = cost, [(first, opponent)] + tail_pairs
        return best_cost, best_pairs

    # Full backtracking is ideal for school groups; cap candidate branching for very large fields.
    if len(pool) <= 14:
        _, raw_pairs = search(pool)
    else:
        raw_pairs = []
        remaining = pool[:]
        while remaining:
            first = remaining.pop(0)
            opponent = min(remaining, key=lambda other: pair_cost(first, other))
            remaining.remove(opponent)
            raw_pairs.append((first, opponent))

    pairs: list[tuple[int, int | None]] = []
    for a, b in raw_pairs:
        # Give White to the player who has had fewer Whites; alternate by rank on ties.
        if a.color_balance > b.color_balance:
            white, black = b, a
        elif b.color_balance > a.color_balance:
            white, black = a, b
        elif rank[a.player_id] % 2 == 0:
            white, black = a, b
        else:
            white, black = b, a
        pairs.append((white.player_id, black.player_id))
    if bye:
        pairs.append((bye.player_id, None))
    return pairs
