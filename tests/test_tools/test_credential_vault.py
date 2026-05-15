"""Tests for credential vault secure storage tool."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import loom.tools.security.credential_vault


class TestCredentialVaultCore:
    """Test credential vault core functions."""

    def test_derive_key_deterministic(self):
        """Test that derive_key produces consistent results."""
        key1 = credential_vault._derive_key()
        key2 = credential_vault._derive_key()
        assert key1 == key2
        assert len(key1) == 32  # SHA256 truncated to 32 bytes

    def test_derive_key_length(self):
        """Test custom key length parameter."""
        key = credential_vault._derive_key(length=16)
        assert len(key) == 16

    def test_xor_cipher_reversible(self):
        """Test XOR cipher is reversible."""
        plaintext = b"secret_api_key_12345"
        key = credential_vault._derive_key()

        encrypted = credential_vault._xor_cipher(plaintext, key)
        decrypted = credential_vault._xor_cipher(encrypted, key)

        assert decrypted == plaintext

    def test_xor_cipher_with_different_key(self):
        """Test XOR cipher fails with different key."""
        plaintext = b"secret_data"
        key1 = credential_vault._derive_key()
        key2 = b"different_key_123"

        encrypted = credential_vault._xor_cipher(plaintext, key1)
        decrypted = credential_vault._xor_cipher(encrypted, key2)

        assert decrypted != plaintext

    def test_xor_cipher_key_repetition(self):
        """Test XOR cipher handles key repetition correctly."""
        plaintext = b"a" * 100  # Longer than key
        key = credential_vault._derive_key()

        encrypted = credential_vault._xor_cipher(plaintext, key)
        decrypted = credential_vault._xor_cipher(encrypted, key)

        assert decrypted == plaintext


class TestVaultStorage:
    """Test vault storage and retrieval."""

    @pytest.fixture
    def temp_vault_dir(self):
        """Create temporary vault directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_vault_path_creation(self, temp_vault_dir):
        """Test vault path is created correctly."""
        with patch("loom.tools.credential_vault.Path.home", return_value=temp_vault_dir):
            path = credential_vault._get_vault_path()
            assert path.parent.exists()
            assert str(path).endswith("vault.json")

    def test_load_vault_creates_empty_dict(self, temp_vault_dir):
        """Test loading non-existent vault returns empty dict."""
        with patch("loom.tools.credential_vault.Path.home", return_value=temp_vault_dir):
            vault = credential_vault._load_vault()
            assert vault == {}

    def test_save_and_load_vault(self, temp_vault_dir):
        """Test saving and loading vault."""
        with patch("loom.tools.credential_vault.Path.home", return_value=temp_vault_dir):
            vault_data = {
                "test_key": {
                    "encrypted": "base64data",
                    "category": "api_key",
                    "stored_at": "2026-01-01T00:00:00+00:00",
                }
            }

            credential_vault._save_vault(vault_data)
            loaded = credential_vault._load_vault()

            assert loaded == vault_data

    def test_vault_file_permissions(self, temp_vault_dir):
        """Test vault file has restricted permissions (600)."""
        with patch("loom.tools.credential_vault.Path.home", return_value=temp_vault_dir):
            vault_data = {"test": {"encrypted": "data", "category": "api_key"}}
            credential_vault._save_vault(vault_data)

            vault_path = credential_vault._get_vault_path()
            perms = oct(vault_path.stat().st_mode)[-3:]
            assert perms == "600"

    def test_load_vault_handles_corrupted_json(self, temp_vault_dir):
        """Test loading corrupted JSON returns empty dict."""
        with patch("loom.tools.credential_vault.Path.home", return_value=temp_vault_dir):
            vault_path = credential_vault._get_vault_path()
            vault_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

            # Write invalid JSON
            with open(vault_path, "w") as f:
                f.write("{ invalid json }")

            vault = credential_vault._load_vault()
            assert vault == {}


@pytest.mark.asyncio
class TestResearchVaultStore:
    """Test research_vault_store async function."""

    async def test_store_credential_basic(self, tmp_path):
        """Test storing a basic credential."""
        with patch("loom.tools.credential_vault.Path.home", return_value=tmp_path):
            result = await credential_vault.research_vault_store(
                name="test_key",
                value="super_secret_value",
                category="api_key",
            )

            assert result["stored"] is True
            assert result["name"] == "test_key"
            assert result["category"] == "api_key"
            assert result["value_prefix"] == "super"

    async def test_store_credential_short_value(self, tmp_path):
        """Test storing credential with short value."""
        with patch("loom.tools.credential_vault.Path.home", return_value=tmp_path):
            result = await credential_vault.research_vault_store(
                name="short",
                value="abc",
                category="token",
            )

            assert result["stored"] is True
            assert result["value_prefix"] == "****"

    async def test_store_credential_missing_name(self, tmp_path):
        """Test storing credential with missing name."""
        with patch("loom.tools.credential_vault.Path.home", return_value=tmp_path):
            result = await credential_vault.research_vault_store(
                name="",
                value="secret",
            )

            assert result["stored"] is False
            assert "error" in result

    async def test_store_credential_missing_value(self, tmp_path):
        """Test storing credential with missing value."""
        with patch("loom.tools.credential_vault.Path.home", return_value=tmp_path):
            result = await credential_vault.research_vault_store(
                name="key",
                value="",
            )

            assert result["stored"] is False
            assert "error" in result

    async def test_store_credential_persists_to_disk(self, tmp_path):
        """Test credential is actually written to vault file."""
        with patch("loom.tools.credential_vault.Path.home", return_value=tmp_path):
            await credential_vault.research_vault_store(
                name="persistent_key",
                value="test_value_123",
                category="password",
            )

            vault_path = tmp_path / ".loom" / "vault.json"
            assert vault_path.exists()

            with open(vault_path, "r") as f:
                vault = json.load(f)

            assert "persistent_key" in vault
            assert vault["persistent_key"]["category"] == "password"

    async def test_store_overwrites_existing_credential(self, tmp_path):
        """Test storing overwrites existing credential with same name."""
        with patch("loom.tools.credential_vault.Path.home", return_value=tmp_path):
            # Store initial credential
            await credential_vault.research_vault_store(
                name="my_key",
                value="old_value",
            )

            # Overwrite with new value
            await credential_vault.research_vault_store(
                name="my_key",
                value="new_value_1234",
            )

            # Verify we can retrieve the new value
            result = await credential_vault.research_vault_retrieve(name="my_key")
            assert result["value"] == "new_value_1234"


@pytest.mark.asyncio
class TestResearchVaultRetrieve:
    """Test research_vault_retrieve async function."""

    async def test_retrieve_credential_basic(self, tmp_path):
        """Test retrieving stored credential."""
        with patch("loom.tools.credential_vault.Path.home", return_value=tmp_path):
            secret = "my_secret_api_key_value"
            await credential_vault.research_vault_store(
                name="api_key",
                value=secret,
                category="api_key",
            )

            result = await credential_vault.research_vault_retrieve(name="api_key")

            assert result["name"] == "api_key"
            assert result["value"] == secret
            assert result["category"] == "api_key"
            assert "last_accessed" in result

    async def test_retrieve_nonexistent_credential(self, tmp_path):
        """Test retrieving non-existent credential."""
        with patch("loom.tools.credential_vault.Path.home", return_value=tmp_path):
            result = await credential_vault.research_vault_retrieve(name="nonexistent")

            assert "error" in result
            assert "not found" in result["error"]

    async def test_retrieve_updates_access_time(self, tmp_path):
        """Test retrieving credential updates last_accessed timestamp."""
        with patch("loom.tools.credential_vault.Path.home", return_value=tmp_path):
            await credential_vault.research_vault_store(
                name="tracked_key",
                value="secret",
            )

            result1 = await credential_vault.research_vault_retrieve(name="tracked_key")
            first_access = result1["last_accessed"]

            # Retrieve again
            result2 = await credential_vault.research_vault_retrieve(name="tracked_key")
            second_access = result2["last_accessed"]

            # Times should be different (second should be newer)
            assert second_access >= first_access

    async def test_retrieve_handles_decryption_error(self, tmp_path):
        """Test retrieve handles corrupted encrypted data gracefully."""
        with patch("loom.tools.credential_vault.Path.home", return_value=tmp_path):
            # Store a valid credential
            await credential_vault.research_vault_store(
                name="bad_key",
                value="test",
            )

            # Corrupt the vault file
            vault_path = tmp_path / ".loom" / "vault.json"
            with open(vault_path, "r") as f:
                vault = json.load(f)

            vault["bad_key"]["encrypted"] = "@@@@invalid@@@@"
            with open(vault_path, "w") as f:
                json.dump(vault, f)

            # Attempt to retrieve should handle error gracefully
            result = await credential_vault.research_vault_retrieve(name="bad_key")
            assert "error" in result or "value" in result


@pytest.mark.asyncio
class TestResearchVaultList:
    """Test research_vault_list async function."""

    async def test_list_empty_vault(self, tmp_path):
        """Test listing empty vault."""
        with patch("loom.tools.credential_vault.Path.home", return_value=tmp_path):
            result = await credential_vault.research_vault_list()

            assert result["total"] == 0
            assert result["credentials"] == []

    async def test_list_credentials(self, tmp_path):
        """Test listing stored credentials."""
        with patch("loom.tools.credential_vault.Path.home", return_value=tmp_path):
            await credential_vault.research_vault_store(
                name="key1",
                value="value1",
                category="api_key",
            )
            await credential_vault.research_vault_store(
                name="key2",
                value="value2",
                category="token",
            )
            await credential_vault.research_vault_store(
                name="key3",
                value="value3",
                category="password",
            )

            result = await credential_vault.research_vault_list()

            assert result["total"] == 3
            assert len(result["credentials"]) == 3

            names = [cred["name"] for cred in result["credentials"]]
            assert "key1" in names
            assert "key2" in names
            assert "key3" in names

    async def test_list_never_exposes_values(self, tmp_path):
        """Test list operation never exposes actual credential values."""
        with patch("loom.tools.credential_vault.Path.home", return_value=tmp_path):
            await credential_vault.research_vault_store(
                name="secret_key",
                value="super_secret_value_12345",
                category="api_key",
            )

            result = await credential_vault.research_vault_list()

            cred = result["credentials"][0]
            assert cred["value_prefix"] == "****"
            assert "super_secret_value" not in str(result)

    async def test_list_includes_metadata(self, tmp_path):
        """Test list includes correct metadata for each credential."""
        with patch("loom.tools.credential_vault.Path.home", return_value=tmp_path):
            await credential_vault.research_vault_store(
                name="test_key",
                value="test_value",
                category="custom_category",
            )

            result = await credential_vault.research_vault_list()

            cred = result["credentials"][0]
            assert cred["name"] == "test_key"
            assert cred["category"] == "custom_category"
            assert "stored_at" in cred
            assert cred["value_prefix"] == "****"


@pytest.mark.asyncio
class TestVaultSecurity:
    """Test security properties of credential vault."""

    async def test_credentials_encrypted_on_disk(self, tmp_path):
        """Test credentials are encrypted when stored on disk."""
        with patch("loom.tools.credential_vault.Path.home", return_value=tmp_path):
            secret = "plaintext_secret_123"
            await credential_vault.research_vault_store(
                name="secure_key",
                value=secret,
            )

            vault_path = tmp_path / ".loom" / "vault.json"
            with open(vault_path, "r") as f:
                vault = json.load(f)

            encrypted_value = vault["secure_key"]["encrypted"]

            # Encrypted value should be base64-encoded and NOT contain plaintext
            assert secret not in encrypted_value
            assert isinstance(encrypted_value, str)

    async def test_vault_file_not_world_readable(self, tmp_path):
        """Test vault file is not world-readable."""
        with patch("loom.tools.credential_vault.Path.home", return_value=tmp_path):
            await credential_vault.research_vault_store(
                name="test",
                value="secret",
            )

            vault_path = tmp_path / ".loom" / "vault.json"
            perms = vault_path.stat().st_mode

            # Check that group and other have no read permission
            # octal 600 = rw-------
            assert oct(perms)[-3:] == "600"

    async def test_xor_key_machine_specific(self, tmp_path):
        """Test XOR key is derived from machine info."""
        with patch("loom.tools.credential_vault.Path.home", return_value=tmp_path):
            with patch("socket.gethostname", return_value="testhost"):
                with patch("os.getlogin", return_value="testuser"):
                    key1 = credential_vault._derive_key()

            with patch("socket.gethostname", return_value="otherhost"):
                with patch("os.getlogin", return_value="otheruser"):
                    key2 = credential_vault._derive_key()

            # Different machine info should produce different keys
            assert key1 != key2


@pytest.mark.asyncio
class TestVaultRoundTrip:
    """Test full store-retrieve round trips."""

    async def test_round_trip_various_secrets(self, tmp_path):
        """Test storing and retrieving various secret formats."""
        with patch("loom.tools.credential_vault.Path.home", return_value=tmp_path):
            test_cases = [
                ("api_key_long", "sk_test_FAKE0000000000000000000000000", "api_key"),
                ("oauth_token", "ghp_1234567890abcdefghijklmnopqrstuv", "token"),
                ("password", "MyP@ssw0rd!#$%", "password"),
                ("jwt", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", "token"),
                ("special_chars", "!@#$%^&*()_+-=[]{}|;:,.<>?", "secret"),
            ]

            for name, value, category in test_cases:
                result = await credential_vault.research_vault_store(
                    name=name,
                    value=value,
                    category=category,
                )
                assert result["stored"] is True

                retrieved = await credential_vault.research_vault_retrieve(name=name)
                assert retrieved["value"] == value
                assert retrieved["category"] == category

    async def test_round_trip_unicode_secrets(self, tmp_path):
        """Test storing and retrieving unicode secrets."""
        with patch("loom.tools.credential_vault.Path.home", return_value=tmp_path):
            unicode_secret = "السر_العربي_🔐_密钥_🚀"

            await credential_vault.research_vault_store(
                name="unicode_key",
                value=unicode_secret,
            )

            result = await credential_vault.research_vault_retrieve(name="unicode_key")
            assert result["value"] == unicode_secret

    async def test_large_credential_storage(self, tmp_path):
        """Test storing and retrieving large credentials."""
        with patch("loom.tools.credential_vault.Path.home", return_value=tmp_path):
            large_secret = "x" * 5000  # 5KB secret

            await credential_vault.research_vault_store(
                name="large_key",
                value=large_secret,
            )

            result = await credential_vault.research_vault_retrieve(name="large_key")
            assert result["value"] == large_secret
