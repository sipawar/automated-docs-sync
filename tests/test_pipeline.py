from src.generator import run_sync_pipeline
from src.parser import ChangeRecord


def test_sync_pipeline_latency_remains_within_budget():
    changes = [
        ChangeRecord(
            path=f"api/schema_{index}.yaml",
            status="M",
            change_type="api",
            impact="high",
            summary=f"updated schema_{index}",
        )
        for index in range(25)
    ]

    result = run_sync_pipeline(changes, max_latency_seconds=1.0)

    assert result["generated_count"] == 25
    assert result["latency_ms"] < 1000
    assert result["patches"]
