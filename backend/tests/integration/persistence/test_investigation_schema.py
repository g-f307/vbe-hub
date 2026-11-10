import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.integration
async def test_individual_signal_schema_expands_without_removing_legacy(
    db_session: AsyncSession,
) -> None:
    connection = await db_session.connection()

    def snapshot(sync_connection):
        inspector = inspect(sync_connection)
        return {
            "tables": set(inspector.get_table_names()),
            "investigation_file_columns": {
                item["name"] for item in inspector.get_columns("investigation_files")
            },
            "investigation_file_indexes": {
                item["name"] for item in inspector.get_indexes("investigation_files")
            },
            "individual_signal_indexes": {
                item["name"] for item in inspector.get_indexes("individual_signals")
            },
            "membership_indexes": {
                item["name"] for item in inspector.get_indexes("investigation_file_members")
            },
            "suggestion_indexes": {
                item["name"] for item in inspector.get_indexes("signal_relation_suggestions")
            },
        }

    schema = await connection.run_sync(snapshot)

    assert {
        "individual_signals",
        "signal_relation_suggestions",
        "investigation_files",
        "investigation_file_members",
        "investigation_membership_events",
    }.issubset(schema["tables"])
    assert "individual_signals_record_contract_uidx" in schema["individual_signal_indexes"]
    assert "head_signal_id" in schema["investigation_file_columns"]
    assert "investigation_files_head_signal_uidx" in schema["investigation_file_indexes"]
    assert "investigation_members_active_signal_uidx" in schema["membership_indexes"]
    assert "signal_relation_suggestions_left_status_idx" in schema["suggestion_indexes"]
    assert "signal_relation_suggestions_right_status_idx" in schema["suggestion_indexes"]
    assert "consolidated_signals" in schema["tables"]
    assert "signal_workflows" in schema["tables"]
