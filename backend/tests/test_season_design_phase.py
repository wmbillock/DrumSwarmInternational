from backend.models.corps import Corps
from backend.models.season_run import CorpsSeasonPhase
from backend.models.show import Show
from backend.services.season_calendar import create_season_calendar
from backend.services.season_phases.design import complete_show_design_for_season


def test_complete_show_design_advances_corps_to_recruiting(db):
    corps = Corps(name="Test Corps")
    show = Show(title="Designed Show")
    db.add_all([corps, show])
    db.flush()
    run = create_season_calendar(
        db,
        name="2026 Test Season",
        regular_show_count=1,
        winter_camp_count=2,
        corps_ids=[corps.id],
    )

    state = complete_show_design_for_season(
        db,
        season_run_id=run.id,
        corps_id=corps.id,
        show_id=show.id,
    )

    assert state.phase == CorpsSeasonPhase.RECRUITING
    db.refresh(corps)
    assert corps.show_id == show.id
