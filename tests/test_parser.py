from src.parser import parse_git_diff, parse_name_status


def test_parse_name_status_handles_common_git_status_entries():
    sample = "M\tapi/openapi.yaml\nA\tconfig/app.yaml\nR100\told.md\tnew.md\n"

    changes = parse_name_status(sample)

    assert len(changes) == 3
    assert changes[0].path == "api/openapi.yaml"
    assert changes[0].change_type == "api"
    assert changes[0].impact == "high"
    assert changes[1].path == "config/app.yaml"
    assert changes[2].status == "R100"
    assert changes[2].path == "new.md"


def test_parse_git_diff_collects_change_records_from_diff_stream():
    diff = """diff --git a/api/openapi.yaml b/api/openapi.yaml
index 1111111..2222222 100644
--- a/api/openapi.yaml
+++ b/api/openapi.yaml
@@ -1,2 +1,3 @@
- old
+ new
+ credentials: token=abc123
"""

    changes = parse_git_diff(diff, source_commit="abc123")

    assert changes
    assert any(change.path == "api/openapi.yaml" for change in changes)
    assert all(change.source_commit == "abc123" for change in changes)
