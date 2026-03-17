import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from lcc.worker.tasks import run_scan_task
from lcc.database.models import Scan

@pytest.mark.asyncio
async def test_run_scan_task_success():
    scan_id = "test-scan-id"

    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:

        # Mock Redis connection (redis_from_url is awaited, so use AsyncMock)
        mock_redis = AsyncMock()
        mock_redis.aclose = AsyncMock()

        with patch("lcc.worker.tasks.redis_from_url", AsyncMock(return_value=mock_redis)):
            # Mock Scanner
            with patch("lcc.worker.tasks.Scanner") as MockScanner:
                mock_scanner_instance = MockScanner.return_value
                mock_report = MagicMock()
                mock_report.findings = []
                mock_report.summary.component_count = 0
                mock_report.summary.violations = 0
                mock_report.summary.duration_seconds = 1.0
                mock_scanner_instance.scan.return_value = mock_report

                # Mock DB Session and Repository
                mock_session = AsyncMock()

                with patch("lcc.worker.tasks.AsyncSessionLocal") as MockSessionLocal:
                    MockSessionLocal.return_value.__aenter__.return_value = mock_session

                    with patch("lcc.worker.tasks.ScanRepository") as MockRepo:
                        mock_repo_instance = MockRepo.return_value
                        # Configure async methods
                        mock_repo_instance.get_scan = AsyncMock(return_value=Scan(id=scan_id, status="queued"))
                        mock_repo_instance.update_scan = AsyncMock()

                        # Run task with valid path
                        await run_scan_task({}, scan_id, path=temp_dir)

                        # Verify
                        mock_repo_instance.get_scan.assert_called_with(scan_id)
                        assert mock_repo_instance.update_scan.call_count >= 1
                        mock_session.commit.assert_called()

@pytest.mark.asyncio
async def test_run_scan_task_not_found():
    scan_id = "missing-scan-id"

    # Mock Redis connection (redis_from_url is awaited, so use AsyncMock)
    mock_redis = AsyncMock()
    mock_redis.aclose = AsyncMock()

    with patch("lcc.worker.tasks.redis_from_url", AsyncMock(return_value=mock_redis)):
        with patch("lcc.worker.tasks.AsyncSessionLocal") as MockSessionLocal:
            mock_session = AsyncMock()
            MockSessionLocal.return_value.__aenter__.return_value = mock_session

            with patch("lcc.worker.tasks.ScanRepository") as MockRepo:
                mock_repo_instance = MockRepo.return_value
                # Configure async methods
                mock_repo_instance.get_scan = AsyncMock(return_value=None)
                mock_repo_instance.update_scan = AsyncMock()

                await run_scan_task({}, scan_id, path="/tmp/test")

                # Should just return without error
                mock_repo_instance.get_scan.assert_called_with(scan_id)
                mock_repo_instance.update_scan.assert_not_called()
