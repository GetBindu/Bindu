"""Unit tests for x402 metadata utilities."""

import pytest

from bindu.extensions.x402.utils import (
    build_payment_completed_metadata,
    build_payment_failed_metadata,
    build_payment_required_metadata,
    build_payment_verified_metadata,
    merge_task_metadata,
)
from bindu.settings import app_settings

pytestmark = pytest.mark.x402


class TestX402Utils:
    def test_build_payment_required_metadata(self):
        req = {"accepts": [{"scheme": "exact"}]}
        md = build_payment_required_metadata(req)
        assert (
            md[app_settings.x402.meta_status_key] == app_settings.x402.status_required
        )
        assert md[app_settings.x402.meta_required_key] is req

    def test_build_payment_verified_metadata(self):
        md = build_payment_verified_metadata()
        assert (
            md[app_settings.x402.meta_status_key] == app_settings.x402.status_verified
        )

    def test_build_payment_completed_metadata(self):
        receipt = {"tx": "0xabc"}
        md = build_payment_completed_metadata(receipt)
        assert (
            md[app_settings.x402.meta_status_key] == app_settings.x402.status_completed
        )
        assert md[app_settings.x402.meta_receipts_key] == [receipt]

    def test_build_payment_failed_metadata(self):
        md = build_payment_failed_metadata("verification_failed")
        assert md[app_settings.x402.meta_status_key] == app_settings.x402.status_failed
        assert md[app_settings.x402.meta_error_key] == "verification_failed"

    def test_build_payment_failed_metadata_with_receipt(self):
        receipt = {"tx": "0xfailed"}
        md = build_payment_failed_metadata("verification_failed", receipt)
        assert md[app_settings.x402.meta_status_key] == app_settings.x402.status_failed
        assert md[app_settings.x402.meta_error_key] == "verification_failed"
        assert md[app_settings.x402.meta_receipts_key] == [receipt]

    def test_merge_task_metadata_new_metadata(self):
        task = {"id": "task-1"}
        updates = {"key": "value"}
        result = merge_task_metadata(task, updates)
        assert result["metadata"] == {"key": "value"}
        assert result is task

    def test_merge_task_metadata_existing_metadata(self):
        task = {"id": "task-1", "metadata": {"existing": "data"}}
        updates = {"new": "value"}
        result = merge_task_metadata(task, updates)
        assert result["metadata"] == {"existing": "data", "new": "value"}

    def test_merge_task_metadata_none_metadata(self):
        task = {"id": "task-1", "metadata": None}
        updates = {"key": "value"}
        result = merge_task_metadata(task, updates)
        assert result["metadata"] == {"key": "value"}
