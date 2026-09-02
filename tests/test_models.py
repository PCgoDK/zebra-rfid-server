from app.models import ApiUser, ApplicationSetting, AuditLog, Reader, TagRead


def test_required_phase_one_tables_are_registered() -> None:
    table_names = {
        Reader.__tablename__,
        TagRead.__tablename__,
        ApiUser.__tablename__,
        ApplicationSetting.__tablename__,
        AuditLog.__tablename__,
    }

    assert table_names == {
        "readers",
        "tag_reads",
        "api_users",
        "application_settings",
        "audit_log",
    }