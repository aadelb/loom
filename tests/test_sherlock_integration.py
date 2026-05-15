"""Integration tests for Sherlock backend with Loom system."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from loom.params import SherlockBatchParams, SherlockLookupParams
import loom.tools.backends.sherlock_backend


class TestSherlockIntegration:
    """Integration tests for Sherlock backend with the Loom system."""

    def test_params_to_function_lookup(self) -> None:
        """Params can be created and passed to research_sherlock_lookup."""
        params = SherlockLookupParams(
            username="testuser",
            platforms=["twitter", "github"],
            timeout=60,
        )

        with patch(
            "loom.tools.backends.sherlock_backend._check_sherlock_available"
        ) as mock_check:
            mock_check.return_value = (False, "Not available")

            result = sherlock_backend.research_sherlock_lookup(
                params.username,
                params.platforms,
                params.timeout,
            )

            assert result["sherlock_available"] is False

    def test_params_to_function_batch(self) -> None:
        """Params can be created and passed to research_sherlock_batch."""
        params = SherlockBatchParams(
            usernames=["user1", "user2"],
            platforms=["twitter"],
            timeout=45,
        )

        with patch(
            "loom.tools.backends.sherlock_backend._check_sherlock_available"
        ) as mock_check:
            mock_check.return_value = (False, "Not available")

            result = sherlock_backend.research_sherlock_batch(
                params.usernames,
                params.platforms,
                params.timeout,
            )

            assert result["sherlock_available"] is False

    def test_workflow_single_lookup(self) -> None:
        """Complete workflow: params creation -> validation -> lookup."""
        username = "john_doe"
        params = SherlockLookupParams(username=username)

        # Params should be valid
        assert params.username == username
        assert params.timeout == 30

        # Can call the function
        with patch(
            "loom.tools.backends.sherlock_backend._check_sherlock_available"
        ) as mock_check:
            mock_check.return_value = (True, "Available")

            with patch(
                "loom.tools.sherlock_backend.subprocess.run"
            ) as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                with patch("builtins.open", create=True) as mock_open:
                    mock_file = MagicMock()
                    mock_file.__enter__.return_value = mock_file
                    mock_file.read.return_value = '{"john_doe": {}}'
                    mock_open.return_value = mock_file

                    result = sherlock_backend.research_sherlock_lookup(
                        params.username,
                        params.platforms,
                        params.timeout,
                    )

                    assert "sherlock_available" in result
                    assert "username" in result

    def test_workflow_batch_lookup(self) -> None:
        """Complete workflow: batch params -> validation -> batch lookup."""
        usernames = ["user1", "user2", "user3"]
        params = SherlockBatchParams(usernames=usernames)

        # Params should be valid
        assert params.usernames == usernames
        assert len(params.usernames) == 3

        # Can call the function
        with patch(
            "loom.tools.backends.sherlock_backend._check_sherlock_available"
        ) as mock_check:
            mock_check.return_value = (True, "Available")

            with patch(
                "loom.tools.backends.sherlock_backend.research_sherlock_lookup"
            ) as mock_lookup:
                mock_lookup.return_value = {
                    "username": "user1",
                    "found_on": [],
                    "total_found": 0,
                }

                result = sherlock_backend.research_sherlock_batch(
                    params.usernames,
                    params.platforms,
                    params.timeout,
                )

                assert result["usernames_checked"] == 3
                assert "results" in result

    def test_error_handling_invalid_username(self) -> None:
        """Invalid username is rejected early."""
        with pytest.raises(Exception):  # ValidationError from Pydantic
            SherlockLookupParams(username="invalid@user")

    def test_error_handling_invalid_batch(self) -> None:
        """Invalid batch params are rejected early."""
        with pytest.raises(Exception):  # ValidationError from Pydantic
            SherlockBatchParams(usernames=[])  # Empty list

    def test_params_serialization(self) -> None:
        """Params can be serialized and used as kwargs."""
        params = SherlockLookupParams(
            username="testuser",
            platforms=["twitter", "github"],
        )

        # Convert to dict for potential serialization
        params_dict = params.model_dump(exclude_none=True)
        assert "username" in params_dict
        assert "platforms" in params_dict
        assert "timeout" in params_dict

    def test_concurrent_lookups_safe(self) -> None:
        """Multiple param instances can be created safely."""
        params1 = SherlockLookupParams(username="user1")
        params2 = SherlockLookupParams(username="user2")
        params3 = SherlockLookupParams(username="user3")

        assert params1.username == "user1"
        assert params2.username == "user2"
        assert params3.username == "user3"

    def test_params_are_basemodel(self) -> None:
        """Params are Pydantic BaseModel instances."""
        from pydantic import BaseModel
        
        params = SherlockLookupParams(username="testuser")
        
        # Should be a Pydantic BaseModel
        assert isinstance(params, BaseModel)
        
        # Should have model validation
        assert hasattr(params, 'model_dump')
        assert hasattr(params, 'model_validate')

    def test_full_response_structure(self) -> None:
        """Full response structure from research_sherlock_lookup is valid."""
        with patch(
            "loom.tools.backends.sherlock_backend._check_sherlock_available"
        ) as mock_check:
            mock_check.return_value = (True, "Available")

            with patch(
                "loom.tools.sherlock_backend.subprocess.run"
            ) as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                with patch("builtins.open", create=True) as mock_open:
                    sherlock_output = {
                        "testuser": {
                            "twitter": {
                                "url": "https://twitter.com/testuser",
                                "status_code": 200,
                            },
                            "instagram": {
                                "status_code": 404,
                            },
                        }
                    }

                    import json

                    mock_file = MagicMock()
                    mock_file.__enter__.return_value = mock_file
                    mock_file.read.return_value = json.dumps(sherlock_output)
                    mock_open.return_value = mock_file

                    result = sherlock_backend.research_sherlock_lookup(
                        "testuser"
                    )

                    # Verify response structure
                    assert isinstance(result, dict)
                    assert "username" in result
                    assert "found_on" in result
                    assert "total_found" in result
                    assert "total_checked" in result
                    assert "sherlock_available" in result
                    assert isinstance(result["found_on"], list)
                    assert isinstance(result["total_found"], int)
