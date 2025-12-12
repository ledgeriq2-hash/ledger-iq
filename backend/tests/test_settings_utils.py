from __future__ import annotations

from app.core import settings_utils


def test_get_tenant_settings_none():
    settings = settings_utils.get_tenant_settings(None)
    assert "chart_of_accounts_mapping" in settings
    assert settings["chart_of_accounts_mapping"]["cash_account_id"] is None
    assert settings["limits"] == {}


def test_get_tenant_settings_empty_dict():
    settings = settings_utils.get_tenant_settings({})
    assert settings["chart_of_accounts_mapping"]["revenue_account_id"] is None
    assert settings["limits"] == {}


def test_get_tenant_settings_partial_data():
    partial = {"chart_of_accounts_mapping": {"cash_account_id": "abc"}}
    settings = settings_utils.get_tenant_settings(partial)
    assert settings["chart_of_accounts_mapping"]["cash_account_id"] == "abc"
    # Missing keys backfilled
    assert settings["chart_of_accounts_mapping"]["revenue_account_id"] is None
    assert settings["limits"] == {}
