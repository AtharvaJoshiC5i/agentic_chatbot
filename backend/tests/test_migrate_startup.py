"""Startup migration helper avoids redundant Alembic runs."""

from unittest.mock import patch

from app.database.migrate import upgrade_database_to_head


def test_upgrade_skips_when_already_at_head() -> None:
    with (
        patch("app.database.migrate._head_revision", return_value="rev_head"),
        patch("app.database.migrate._current_revision", return_value="rev_head"),
        patch("app.database.migrate.command.upgrade") as mock_upgrade,
        patch("app.database.migrate.dispose_engine") as mock_dispose,
        patch("app.database.migrate._alembic_config") as mock_cfg,
    ):
        mock_cfg.return_value = object()
        upgrade_database_to_head()

    mock_dispose.assert_called()
    mock_upgrade.assert_not_called()
