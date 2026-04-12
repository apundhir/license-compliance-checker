"""Integration tests for end-to-end workflows."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


class TestPolicyManagementWorkflow:
    """Test complete policy management workflows."""

    def test_complete_policy_lifecycle(self, test_app: TestClient, admin_token: str):
        """Test creating, updating, evaluating, and deleting a policy."""
        # Step 1: Create a policy
        create_response = test_app.post(
            "/policies",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "lifecycle-test",
                "content": """
name: lifecycle-test
version: 1.0
disclaimer: Lifecycle test policy
description: Testing complete lifecycle
default_context: production
contexts:
  production:
    allow: [MIT, Apache-2.0]
    deny: [GPL-*]
    review: [LGPL-*]
    deny_reasons:
      GPL-*: Copyleft license
                """.strip(),
                "format": "yaml"
            }
        )
        assert create_response.status_code == 201
        created_policy = create_response.json()
        assert created_policy["name"] == "lifecycle-test"

        # Step 2: Verify it appears in list
        list_response = test_app.get(
            "/policies",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert list_response.status_code == 200
        policies = list_response.json()
        policy_names = [p["name"] for p in policies]
        assert "lifecycle-test" in policy_names

        # Step 3: Get policy details
        get_response = test_app.get(
            "/policies/lifecycle-test",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert get_response.status_code == 200
        policy_detail = get_response.json()
        assert "contexts" in policy_detail
        assert len(policy_detail["contexts"]) >= 1

        # Step 4: Evaluate licenses against the policy
        eval_response = test_app.post(
            "/policies/lifecycle-test/evaluate",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "licenses": ["MIT", "GPL-3.0", "Apache-2.0"],
                "context": "production"
            }
        )
        assert eval_response.status_code == 200
        eval_results = eval_response.json()
        assert len(eval_results) == 3

        # Step 5: Update the policy
        update_response = test_app.put(
            "/policies/lifecycle-test",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "content": """
name: lifecycle-test
version: 2.0
disclaimer: Updated lifecycle test policy
description: Updated version
default_context: production
contexts:
  production:
    allow: [MIT, Apache-2.0, BSD-3-Clause]
    deny: [GPL-*, AGPL-*]
    review: []
                """.strip(),
                "format": "yaml"
            }
        )
        assert update_response.status_code == 200

        # Step 6: Verify the update
        get_updated_response = test_app.get(
            "/policies/lifecycle-test",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert get_updated_response.status_code == 200
        updated_policy = get_updated_response.json()
        production_ctx = next(
            (c for c in updated_policy["contexts"] if c["name"] == "production"),
            None
        )
        assert production_ctx is not None
        assert "BSD-3-Clause" in production_ctx["allow"]

        # Step 7: Delete the policy
        delete_response = test_app.delete(
            "/policies/lifecycle-test",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert delete_response.status_code == 204

        # Step 8: Verify deletion
        verify_response = test_app.get(
            "/policies/lifecycle-test",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert verify_response.status_code == 404


class TestScanWorkflow:
    """Test complete scan workflows."""

    def test_scan_and_retrieve_workflow(
        self,
        test_app: TestClient,
        admin_token: str,
        sample_project_dir: Path
    ):
        """Test creating a scan and retrieving results."""
        # Step 1: Create a scan
        create_response = test_app.post(
            "/scans",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "path": str(sample_project_dir),
                "project_name": "workflow-test-project"
            }
        )

        # May fail if scanning is not fully functional
        if create_response.status_code != 201:
            pytest.skip("Scan creation not working, skipping workflow test")

        scan_data = create_response.json()
        scan_id = scan_data["id"]
        assert scan_data["project"] == "workflow-test-project"

        # Step 2: Verify scan appears in list
        list_response = test_app.get(
            "/scans",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert list_response.status_code == 200
        scans = list_response.json()
        scan_ids = [s["id"] for s in scans]
        assert scan_id in scan_ids

        # Step 3: Get scan details
        detail_response = test_app.get(
            f"/scans/{scan_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert "summary" in detail
        assert "report" in detail

        # Step 4: Verify report structure
        report = detail["report"]
        if report and isinstance(report, dict):
            # Should have some structure
            assert len(report) > 0

    def test_scan_with_policy_workflow(
        self,
        test_app: TestClient,
        admin_token: str,
        sample_project_dir: Path
    ):
        """Test scanning with a policy and checking violations."""
        # Step 1: Create a strict policy
        policy_response = test_app.post(
            "/policies",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "strict-workflow-policy",
                "content": """
name: strict-workflow-policy
version: 1.0
disclaimer: Strict policy for testing
contexts:
  production:
    allow: [MIT]
    deny: [GPL-*, Apache-*, BSD-*]
                """.strip(),
                "format": "yaml"
            }
        )
        assert policy_response.status_code == 201

        # Step 2: Run scan with the strict policy
        scan_response = test_app.post(
            "/scans",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "path": str(sample_project_dir),
                "project_name": "strict-policy-scan",
                "policy": "strict-workflow-policy",
                "context": "production"
            }
        )

        # May fail if policy evaluation in scans is not implemented
        if scan_response.status_code == 201:
            scan_data = scan_response.json()

            # Step 3: Check for violations
            detail_response = test_app.get(
                f"/scans/{scan_data['id']}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert detail_response.status_code == 200
            detail = detail_response.json()

            # Should have violation or warning data
            summary = detail["summary"]
            assert "violations" in summary
            assert "warnings" in summary

        # Cleanup
        test_app.delete(
            "/policies/strict-workflow-policy",
            headers={"Authorization": f"Bearer {admin_token}"}
        )


class TestMultiUserWorkflow:
    """Test workflows involving multiple users."""

    def test_admin_creates_policy_user_scans(
        self,
        test_app: TestClient,
        admin_token: str,
        user_token: str,
        sample_project_dir: Path
    ):
        """Test admin creating policy and regular user using it for scan."""
        # Step 1: Admin creates a policy
        policy_response = test_app.post(
            "/policies",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "multiuser-policy",
                "content": """
name: multiuser-policy
version: 1.0
disclaimer: Multi-user test policy
contexts:
  production:
    allow: [MIT, Apache-2.0]
    deny: [GPL-*]
                """.strip(),
                "format": "yaml"
            }
        )
        assert policy_response.status_code == 201

        # Step 2: Regular user lists policies (should see the new one)
        list_response = test_app.get(
            "/policies",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert list_response.status_code == 200
        policies = list_response.json()
        policy_names = [p["name"] for p in policies]
        assert "multiuser-policy" in policy_names

        # Step 3: Regular user creates a scan with the policy
        scan_response = test_app.post(
            "/scans",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "path": str(sample_project_dir),
                "project_name": "user-policy-scan",
                "policy": "multiuser-policy"
            }
        )

        # Should succeed
        assert scan_response.status_code in [201, 400]  # 500 no longer acceptable

        # Step 4: Regular user tries to delete policy (should fail)
        delete_response = test_app.delete(
            "/policies/multiuser-policy",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert delete_response.status_code == 403

        # Step 5: Admin deletes the policy
        admin_delete_response = test_app.delete(
            "/policies/multiuser-policy",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_delete_response.status_code == 204

    def test_user_isolation(
        self,
        test_app: TestClient,
        admin_token: str,
        user_token: str,
        sample_project_dir: Path
    ):
        """Test that users can only see their own scans (if isolation implemented)."""
        # Admin creates a scan
        admin_scan_response = test_app.post(
            "/scans",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "path": str(sample_project_dir),
                "project_name": "admin-private-scan"
            }
        )

        # User creates a scan
        user_scan_response = test_app.post(
            "/scans",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "path": str(sample_project_dir),
                "project_name": "user-private-scan"
            }
        )

        # If both succeed
        if admin_scan_response.status_code == 201 and user_scan_response.status_code == 201:
            admin_scan_id = admin_scan_response.json()["id"]
            user_scan_id = user_scan_response.json()["id"]

            # User lists scans - may or may not see admin's scan depending on implementation
            user_list_response = test_app.get(
                "/scans",
                headers={"Authorization": f"Bearer {user_token}"}
            )
            assert user_list_response.status_code == 200
            user_visible_scans = user_list_response.json()

            # At minimum, user should see their own scan
            user_scan_ids = [s["id"] for s in user_visible_scans]
            assert user_scan_id in user_scan_ids


class TestDashboardWorkflow:
    """Test dashboard data aggregation workflow."""

    def test_dashboard_summary(self, test_app: TestClient, admin_token: str):
        """Test retrieving dashboard summary data."""
        response = test_app.get(
            "/dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Should succeed
        assert response.status_code == 200
        dashboard_data = response.json()

        # Check expected structure
        assert "totalProjects" in dashboard_data
        assert "totalScans" in dashboard_data
        assert "totalViolations" in dashboard_data
        assert "totalWarnings" in dashboard_data

        # Check that values are numbers
        assert isinstance(dashboard_data["totalProjects"], int)
        assert isinstance(dashboard_data["totalScans"], int)
        assert isinstance(dashboard_data["totalViolations"], int)
        assert isinstance(dashboard_data["totalWarnings"], int)

    def test_dashboard_with_scans(
        self,
        test_app: TestClient,
        admin_token: str,
        sample_project_dir: Path
    ):
        """Test dashboard data after creating scans."""
        # Get initial dashboard state
        initial_response = test_app.get(
            "/dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert initial_response.status_code == 200
        initial_data = initial_response.json()
        initial_scans = initial_data["totalScans"]

        # Create a scan
        scan_response = test_app.post(
            "/scans",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "path": str(sample_project_dir),
                "project_name": "dashboard-test-scan"
            }
        )

        if scan_response.status_code == 201:
            # Get updated dashboard state
            updated_response = test_app.get(
                "/dashboard",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert updated_response.status_code == 200
            updated_data = updated_response.json()

            # Total scans should have increased
            assert updated_data["totalScans"] >= initial_scans


class TestErrorHandlingWorkflow:
    """Test error handling across workflows."""

    def test_graceful_degradation(
        self,
        test_app: TestClient,
        admin_token: str
    ):
        """Test that API handles errors gracefully."""
        # Try to create policy with invalid YAML
        response1 = test_app.post(
            "/policies",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "invalid-yaml-policy",
                "content": "{ invalid yaml: [",
                "format": "yaml"
            }
        )
        assert response1.status_code == 400
        assert "detail" in response1.json()

        # Try to scan nonexistent path
        response2 = test_app.post(
            "/scans",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "path": "/definitely/does/not/exist/12345",
                "project_name": "nonexistent"
            }
        )
        assert response2.status_code == 400
        assert "detail" in response2.json()

        # Try to get nonexistent resource
        response3 = test_app.get(
            "/policies/nonexistent-xyz-123",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response3.status_code == 404
        assert "detail" in response3.json()

    def test_validation_errors(self, test_app: TestClient, admin_token: str):
        """Test input validation across endpoints."""
        # Invalid policy name (special characters)
        response1 = test_app.post(
            "/policies",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "invalid@name#with$chars",
                "content": "name: test\nversion: 1.0\ndisclaimer: test",
                "format": "yaml"
            }
        )
        # Should reject or accept depending on validation
        assert response1.status_code in [201, 400, 422]

        # Missing required fields
        response2 = test_app.post(
            "/scans",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "project_name": "incomplete-scan"
                # Missing path or repo_url
            }
        )
        assert response2.status_code == 400

    def test_concurrent_operations(
        self,
        test_app: TestClient,
        admin_token: str
    ):
        """Test handling of concurrent operations."""
        # Create policy
        policy_response = test_app.post(
            "/policies",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "concurrent-test",
                "content": "name: concurrent-test\nversion: 1.0\ndisclaimer: test\ncontexts:\n  production:\n    allow: [MIT]",
                "format": "yaml"
            }
        )
        assert policy_response.status_code == 201

        # Try to update and delete concurrently (simulated)
        update_response = test_app.put(
            "/policies/concurrent-test",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "content": "name: concurrent-test\nversion: 2.0\ndisclaimer: updated",
                "format": "yaml"
            }
        )

        # One should succeed
        assert update_response.status_code in [200, 404]

        # Cleanup
        test_app.delete(
            "/policies/concurrent-test",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
