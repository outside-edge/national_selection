import json
import zipfile
from datetime import date

import pytest

from national_selection.refresh import (
    extract_archive,
    observation_end,
    verify_retained_matches,
)


def test_refresh_uses_completed_sibling_cutoff_and_rejects_staleness():
    assert observation_end({"as_of": "2026-10-25"}, date(2026, 10, 30)) == date(
        2026, 10, 25
    )
    for value in ["2026-10-01", "2026-10-30", "2026-11-01"]:
        with pytest.raises(ValueError, match="completed day"):
            observation_end({"as_of": value}, date(2026, 10, 30))


def test_archive_rejects_paths_and_empty_archives(tmp_path):
    for name in ["../123.json", "folder/123.json", "metadata.json"]:
        archive = tmp_path / "archive.zip"
        with zipfile.ZipFile(archive, "w") as target:
            target.writestr(name, "{}")
        with pytest.raises(ValueError, match="Unexpected"):
            extract_archive(archive, tmp_path / "output")
    with zipfile.ZipFile(archive, "w") as target:
        target.writestr("README.txt", "Read me")
    with pytest.raises(ValueError, match="no match records"):
        extract_archive(archive, tmp_path / "output")


def test_archive_preserves_json_and_record_count(tmp_path):
    archive = tmp_path / "archive.zip"
    record = {"info": {"dates": ["2026-05-01"]}}
    with zipfile.ZipFile(archive, "w") as target:
        target.writestr("123.json", json.dumps(record))
        target.writestr("README.txt", "Read me")
    assert extract_archive(archive, tmp_path / "output") == 1
    assert json.loads((tmp_path / "output/123.json").read_text()) == record


def test_source_regression_blocks_publication(tmp_path):
    before, after = tmp_path / "before", tmp_path / "after"
    before.mkdir()
    after.mkdir()
    for name in ["performances.csv", "international_appearances.csv", "calendar.csv"]:
        (before / name).write_text("match_id\n123\n456\n")
        (after / name).write_text("match_id\n123\n456\n789\n")
    verify_retained_matches(before, after)
    (after / "performances.csv").write_text("match_id\n123\n")
    with pytest.raises(ValueError, match="disappeared"):
        verify_retained_matches(before, after)
