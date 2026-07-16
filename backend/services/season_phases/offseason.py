from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.models.performer import Performer


@dataclass(frozen=True)
class LearningDelta:
    target_type: str
    target_id: str
    source: str
    summary: str


def run_offseason_training(db: Session, *, season_run_id: str, corps_id: str) -> list[LearningDelta]:
    performers = db.query(Performer).filter(Performer.corps_id == corps_id).all()
    deltas: list[LearningDelta] = []

    for performer in performers:
        old_trust = float(performer.trust_score or 0.0)
        performer.trust_score = min(100.0, old_trust + 1.0)
        deltas.append(
            LearningDelta(
                target_type="performer",
                target_id=performer.id,
                source="offseason_training",
                summary=(
                    f"Offseason training improved trust from {old_trust:.1f} "
                    f"to {performer.trust_score:.1f}."
                ),
            )
        )

    db.commit()
    return deltas
