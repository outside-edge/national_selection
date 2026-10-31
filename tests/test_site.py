import json

import pandas as pd
import pytest

from national_selection.site import check_site, checksum, validate_forecast


@pytest.fixture
def forecast():
    frame = pd.DataFrame(
        [
            dict(
                player_id="player",
                cutoff_date="2026-01-01",
                label_end="2026-12-31",
                horizon_months=12,
                fit_date="2026-01-01",
                selected_classifier="base_rate",
                base_rate=0.09,
                logistic=0.2,
            )
        ]
    )
    policy = dict(
        horizon_months=12,
        observed_through="2025-12-31",
        policy_available_from="2020-12-01",
        classification_model_selected_on_validation_log_loss="base_rate",
    )
    return frame, policy


def test_publication_preserves_selected_model(forecast):
    frame, policy = forecast
    assert validate_forecast(frame, policy, "2025-12-31") == "base_rate"
    frame["selected_classifier"] = "logistic"
    with pytest.raises(ValueError, match="differs from validation"):
        validate_forecast(frame, policy, "2025-12-31")


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("cutoff_date", "2026-02-01", "exceeds input coverage"),
        ("label_end", "2027-12-31", "target window"),
        ("fit_date", "2025-01-01", "annual parameter fit"),
        ("horizon_months", 6, "horizon differs"),
        ("logistic", float("nan"), "Invalid probabilities"),
        ("base_rate", 1.5, "Invalid probabilities"),
    ],
)
def test_rejects_misleading_forecast_metadata(forecast, column, value, message):
    frame, policy = forecast
    frame[column] = value
    with pytest.raises(ValueError, match=message):
        validate_forecast(frame, policy, "2025-12-31")


def test_duplicate_players_fail(forecast):
    frame, policy = forecast
    with pytest.raises(ValueError, match="unique"):
        validate_forecast(pd.concat([frame, frame]), policy, "2025-12-31")


def test_download_corruption_and_broken_links_fail(tmp_path):
    (tmp_path / "out").mkdir()
    data = tmp_path / "out/forecast.csv"
    data.write_text("player_id,probability\na,0.2\n")
    (tmp_path / "out/publication.json").write_text(
        json.dumps(
            {
                "downloads": {"out/forecast.csv": checksum(data)},
            }
        )
    )
    page = tmp_path / "index.html"
    page.write_text('<a href="out/forecast.csv">Download</a>')
    assert check_site(tmp_path) == 1
    data.write_text("player_id,probability\na,0.9\n")
    with pytest.raises(ValueError, match="checksum mismatch"):
        check_site(tmp_path)
    page.write_text('<a href="missing.html">Missing</a>')
    with pytest.raises(ValueError, match="Broken local link"):
        check_site(tmp_path)
