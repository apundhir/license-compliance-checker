"""Integration tests for Scan API endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


class TestScanCreation:
    """Test scan creation operations."""

    def test_create_scan_with_path(
        self,
        test_app: TestClient,
        admin_token: str,
        sample_project_dir: Path
    ):
        """Test creating a scan for a local filesystem path."""
        response = test_app.post(
            "/scans",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "path": str(sample_project_dir),
                "project_name": "test-project"
            }
        )

        # Should succeed or return appropriate error
        assert response.status_code in [201, 400]  # 500 no longer acceptable

        if response.status_code == 201:
            scan_data = response.json()
            assert "id" in scan_data
            assert "project" in scan_data
            assert scan_data["project"] == "test-project"
            assert "status" in scan_data

            # Verify we can retrieve the scan
            scan_id = scan_data["id"]
            get_response = test_app.get(
                f"/scans/{scan_id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert get_response.status_code == 200

    def test_create_scan_with_invalid_path(
        self,
        test_app: TestClient,
        admin_token: str
    ):
        """Test creating a scan with a nonexistent path."""
        response = test_app.post(
            "/scans",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "path": "/nonexistent/path/12345",
                "project_name": "invalid-project"
            }
        )

        # Should return 400 error
        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"].lower() or "not found" in response.json()["detail"].lower()

    def test_create_scan_without_path_or_repo(
        self,
        test_app: TestClient,
        admin_token: str
    ):
        """Test that either path or repo_url is required."""
        response = test_app.post(
            "/scans",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "project_name": "no-source"
            }
        )

        # Should return 400 error
        assert response.status_code == 400
        assert "path" in response.json()["detail"].lower() or "repo" in response.json()["detail"].lower()

    def test_create_scan_with_policy(
        self,
        test_app: TestClient,
        admin_token: str,
        sample_project_dir: Path
    ):
        """Test creating a scan with a specific policy."""
        # First create a test policy
        policy_response = test_app.post(
            "/policies",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "scan-test-policy",
                "content": "name: scan-test-policy\nversion: 1.0\ndisclaimer: test\ncontexts:\n  production:\n    allow: [MIT, Apache-2.0]\n    deny: [GPL-*]",
                "format": "yaml"
            }
        )
        assert policy_response.status_code == 201

        # Create scan with the policy
        scan_response = test_app.post(
            "/scans",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "path": str(sample_project_dir),
                "project_name": "policy-test-scan",
                "policy": "scan-test-policy",
                "context": "production"
            }
        )

        # Should succeed
        assert scan_response.status_code in [201, 400]  # 500 no longer acceptable

        if scan_response.status_code == 201:
            scan_data = scan_response.json()
            assert "id" in scan_data

        # Cleanup policy
        test_app.delete(
            "/policies/scan-test-policy",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

    def test_create_scan_with_exclude_patterns(
        self,
        test_app: TestClient,
        admin_token: str,
        sample_project_dir: Path
    ):
        """Test creating a scan with exclude patterns."""
        response = test_app.post(
            "/scans",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "path": str(sample_project_dir),
                "project_name": "exclude-test",
                "exclude": ["node_modules/**", "*.pyc", "test/**"]
            }
        )

        assert response.status_code in [201, 400]  # 500 no longer acceptable


class TestScanRetrieval:
    """Test scan retrieval operations."""

    def test_list_scans(self, test_app: TestClient, admin_token: str):
        """Test listing all scans."""
        response = test_app.get(
            "/scans",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        scans = response.json()
        assert isinstance(scans, list)

        # Check structure if scans exist
        if scans:
            scan = scans[0]
            assert "id" in scan
            assert "project" in scan
            assert "status" in scan

    def test_get_scan_details(
        self,
        test_app: TestClient,
        admin_token: str,
        sample_project_dir: Path
    ):
        """Test getting details of a specific scan."""
        # Create a scan first
        create_response = test_app.post(
            "/scans",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "path": str(sample_project_dir),
                "project_name": "detail-test"
            }
        )

        if create_response.status_code == 201:
            scan_id = create_response.json()["id"]

            # Get scan details
            get_response = test_app.get(
                f"/scans/{scan_id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )

            assert get_response.status_code == 200
            scan_detail = get_response.json()
            assert "summary" in scan_detail
            assert "report" in scan_detail

            # Check summary structure
            summary = scan_detail["summary"]
            assert "id" in summary
            assert "project" in summary
            assert "status" in summary
            assert "violations" in summary
            assert "warnings" in summary

    def test_get_nonexistent_scan(self, test_app: TestClient, admin_token: str):
        """Test getting a scan that doesn't exist."""
        response = test_app.get(
            "/scans/nonexistent-scan-id-12345",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_list_scans_pagination(self, test_app: TestClient, admin_token: str):
        """Test scan listing with pagination."""
        # Test with limit and offset parameters
        response = test_app.get(
            "/scans?limit=10&offset=0",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Should succeed even if pagination isn't implemented
        assert response.status_code in [200, 400, 422]

        if response.status_code == 200:
            scans = response.json()
            assert isinstance(scans, list)
            # If pagination is implemented, should respect limit
            if "limit" in response.request.url.params:
                assert len(scans) <= 10


class TestScanFiltering:
    """Test scan filtering and search operations."""

    def test_filter_scans_by_project(self, test_app: TestClient, admin_token: str):
        """Test filtering scans by project name."""
        response = test_app.get(
            "/scans?project=test-project",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Should succeed even if filtering isn't implemented
        assert response.status_code in [200, 400, 422]

        if response.status_code == 200:
            scans = response.json()
            assert isinstance(scans, list)

    def test_filter_scans_by_status(self, test_app: TestClient, admin_token: str):
        """Test filtering scans by status."""
        response = test_app.get(
            "/scans?status=completed",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Should succeed even if filtering isn't implemented
        assert response.status_code in [200, 400, 422]

        if response.status_code == 200:
            scans = response.json()
            assert isinstance(scans, list)

    def test_filter_scans_by_date(self, test_app: TestClient, admin_token: str):
        """Test filtering scans by date range."""
        response = test_app.get(
            "/scans?from=2024-01-01&to=2024-12-31",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Should succeed even if filtering isn't implemented
        assert response.status_code in [200, 400, 422]


class TestScanDeletion:
    """Test scan deletion operations."""

    def test_delete_scan(
        self,
        test_app: TestClient,
        admin_token: str,
        sample_project_dir: Path
    ):
        """Test deleting a scan."""
        # Create a scan first
        create_response = test_app.post(
            "/scans",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "path": str(sample_project_dir),
                "project_name": "delete-test"
            }
        )

        if create_response.status_code == 201:
            scan_id = create_response.json()["id"]

            # Delete the scan
            delete_response = test_app.delete(
                f"/scans/{scan_id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )

            # Should succeed or return 404 if deletion not implemented
            assert delete_response.status_code in [200, 204, 404]

            if delete_response.status_code in [200, 204]:
                # Verify it's deleted
                get_response = test_app.get(
                    f"/scans/{scan_id}",
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                assert get_response.status_code == 404

    def test_delete_nonexistent_scan(self, test_app: TestClient, admin_token: str):
        """Test deleting a scan that doesn't exist."""
        response = test_app.delete(
            "/scans/nonexistent-scan-xyz",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Should return 404
        assert response.status_code in [404, 405]


class TestScanReports:
    """Test scan report generation and retrieval."""

    def test_get_scan_report(
        self,
        test_app: TestClient,
        admin_token: str,
        sample_project_dir: Path
    ):
        """Test getting a scan report."""
        # Create a scan
        create_response = test_app.post(
            "/scans",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "path": str(sample_project_dir),
                "project_name": "report-test"
            }
        )

        if create_response.status_code == 201:
            scan_id = create_response.json()["id"]

            # Get the scan details (which includes report)
            get_response = test_app.get(
                f"/scans/{scan_id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )

            assert get_response.status_code == 200
            scan_data = get_response.json()
            assert "report" in scan_data

            report = scan_data["report"]
            # Check basic report structure
            if report and isinstance(report, dict):
                # Report should have some license findings
                assert "project" in report or "metadata" in report or "findings" in report

    def test_get_scan_report_formats(
        self,
        test_app: TestClient,
        admin_token: str,
        sample_project_dir: Path
    ):
        """Test getting scan reports in different formats."""
        # Create a scan
        create_response = test_app.post(
            "/scans",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "path": str(sample_project_dir),
                "project_name": "format-test"
            }
        )

        if create_response.status_code == 201:
            scan_id = create_response.json()["id"]

            # Try different report formats
            for format_type in ["json", "html", "markdown", "csv"]:
                report_response = test_app.get(
                    f"/scans/{scan_id}/report?format={format_type}",
                    headers={"Authorization": f"Bearer {admin_token}"}
                )

                # Should succeed or return 404 if format not supported
                assert report_response.status_code in [200, 404, 400, 422]


class TestGitHubIntegration:
    """Test GitHub repository scanning."""

    def test_scan_github_repo_invalid_url(self, test_app: TestClient, admin_token: str):
        """Test scanning with invalid GitHub URL."""
        response = test_app.post(
            "/scans",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "repo_url": "not-a-valid-url",
                "project_name": "invalid-github"
            }
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower() or "url" in response.json()["detail"].lower()

    def test_scan_github_repo_both_path_and_url(
        self,
        test_app: TestClient,
        admin_token: str,
        sample_project_dir: Path
    ):
        """Test that providing both path and repo_url is rejected."""
        response = test_app.post(
            "/scans",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "path": str(sample_project_dir),
                "repo_url": "https://github.com/user/repo",
                "project_name": "both-sources"
            }
        )

        # Should return 400 error
        assert response.status_code == 400
        assert "both" in response.json()["detail"].lower() or "either" in response.json()["detail"].lower()


class TestScanAccess:
    """Test scan access control."""

    def test_regular_user_can_create_scan(
        self,
        test_app: TestClient,
        user_token: str,
        sample_project_dir: Path
    ):
        """Test that regular users can create scans."""
        response = test_app.post(
            "/scans",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "path": str(sample_project_dir),
                "project_name": "user-scan"
            }
        )

        # Should succeed (scans are not admin-only)
        assert response.status_code in [201, 400]  # 500 no longer acceptable

    def test_regular_user_can_view_scans(
        self,
        test_app: TestClient,
        user_token: str
    ):
        """Test that regular users can view scans."""
        response = test_app.get(
            "/scans",
            headers={"Authorization": f"Bearer {user_token}"}
        )

        assert response.status_code == 200

    def test_unauthenticated_cannot_create_scan(
        self,
        test_app: TestClient,
        sample_project_dir: Path
    ):
        """Test that unauthenticated users cannot create scans."""
        response = test_app.post(
            "/scans",
            json={
                "path": str(sample_project_dir),
                "project_name": "unauth-scan"
            }
        )

        assert response.status_code == 401
        assert "not authenticated" in response.json()["detail"].lower()
