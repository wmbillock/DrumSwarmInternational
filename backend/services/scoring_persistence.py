"""Scoring persistence — save/load standings and per-corps scores to YAML on disk."""

from pathlib import Path

from backend.models.score import JudgeType
from backend.services.scoring_engine import CorpsResult, Standings
from backend.services.yaml_util import atomic_write, safe_dump_yaml, safe_load_yaml_dict


def _corps_result_to_dict(result: CorpsResult) -> dict:
    return {
        "corps_id": result.corps_id,
        "caption_scores": {k.value: v for k, v in result.caption_scores.items()},
        "penalties_total": result.penalties_total,
        "difficulty_coefficient": result.difficulty_coefficient,
        "raw_score": result.raw_score,
        "final_score": result.final_score,
        "rank": result.rank,
    }


def _dict_to_corps_result(d: dict) -> CorpsResult:
    return CorpsResult(
        corps_id=d["corps_id"],
        caption_scores={JudgeType(k): v for k, v in d["caption_scores"].items()},
        penalties_total=d["penalties_total"],
        difficulty_coefficient=d["difficulty_coefficient"],
        raw_score=d["raw_score"],
        final_score=d["final_score"],
        rank=d["rank"],
    )


def save_standings(base_dir: Path, season_id: str, standings: Standings) -> Path:
    """Write seasons/<season_id>/standings.yaml"""
    base_dir = Path(base_dir)
    season_dir = base_dir / "seasons" / season_id
    season_dir.mkdir(parents=True, exist_ok=True)
    path = season_dir / "standings.yaml"
    data = {
        "season_id": standings.season_id,
        "generated_at": standings.generated_at,
        "results": [_corps_result_to_dict(r) for r in standings.results],
    }
    atomic_write(path, safe_dump_yaml(data))
    return path


def load_standings(base_dir: Path, season_id: str) -> Standings:
    """Read standings.yaml back."""
    base_dir = Path(base_dir)
    path = base_dir / "seasons" / season_id / "standings.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Standings not found: {path}")
    data = safe_load_yaml_dict(path.read_text(encoding="utf-8"))
    return Standings(
        season_id=data["season_id"],
        results=[_dict_to_corps_result(r) for r in data["results"]],
        generated_at=data["generated_at"],
    )


def save_corps_scores(base_dir: Path, season_id: str, corps_id: str, result: CorpsResult) -> Path:
    """Write seasons/<season_id>/performances/<corps_id>/scores.yaml"""
    base_dir = Path(base_dir)
    perf_dir = base_dir / "seasons" / season_id / "performances" / corps_id
    perf_dir.mkdir(parents=True, exist_ok=True)
    path = perf_dir / "scores.yaml"
    atomic_write(path, safe_dump_yaml(_corps_result_to_dict(result)))
    return path


def load_corps_scores(base_dir: Path, season_id: str, corps_id: str) -> CorpsResult:
    """Read scores.yaml back."""
    base_dir = Path(base_dir)
    path = base_dir / "seasons" / season_id / "performances" / corps_id / "scores.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Corps scores not found: {path}")
    data = safe_load_yaml_dict(path.read_text(encoding="utf-8"))
    return _dict_to_corps_result(data)
