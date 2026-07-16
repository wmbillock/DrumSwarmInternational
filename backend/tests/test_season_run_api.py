def test_create_and_get_season_run_summary(app_client):
    response = app_client.post(
        "/api/v1/seasons/runs",
        json={
            "name": "2026 Test Season",
            "regular_show_count": 3,
            "winter_camp_count": 7,
            "corps_ids": ["corps-a", "corps-b"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "planning"
    assert payload["regular_show_count"] == 3
    assert payload["winter_camp_count"] == 7
    assert len(payload["corps"]) == 2

    summary = app_client.get(f"/api/v1/seasons/runs/{payload['season_run_id']}/summary")

    assert summary.status_code == 200
    assert summary.json()["season_run_id"] == payload["season_run_id"]


def test_create_season_run_rejects_too_many_winter_camps(app_client):
    response = app_client.post(
        "/api/v1/seasons/runs",
        json={
            "name": "Broken Season",
            "regular_show_count": 3,
            "winter_camp_count": 8,
            "corps_ids": ["corps-a"],
        },
    )

    assert response.status_code == 422
    assert "winter_camp_count must be between 1 and 7" in response.text
