"""Unit tests for crypto_risk tool — cryptocurrency wallet risk scoring."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from loom.tools.intelligence.crypto_risk import (
    _validate_bitcoin_address,
    _validate_ethereum_address,
    _calculate_risk_score,
    research_crypto_risk_score,
)


class TestBitcoinAddressValidation:
    """Bitcoin address format validation."""

    def test_valid_p2pkh(self) -> None:
        """Valid P2PKH addresses (starting with 1) pass."""
        assert _validate_bitcoin_address("1A1z7agoat2LWUJW1GyeFLzHw2nd2ZKjhL")
        assert _validate_bitcoin_address("1HKhqSCdJ9jQ8FxEEeaRZBF3P2cQX9V2W3")

    def test_valid_p2sh(self) -> None:
        """Valid P2SH addresses (starting with 3) pass."""
        assert _validate_bitcoin_address("3J98t1WpEZ73CNmYviecrnyiWrnqRhWNLy")
        assert _validate_bitcoin_address("3A6rvFyT2DfGDhTJNTZmGK5UW7yW8cXYhL")

    def test_valid_bech32(self) -> None:
        """Valid Bech32 addresses (starting with bc1) pass."""
        assert _validate_bitcoin_address("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4")
        assert _validate_bitcoin_address("bc1qxwqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq7rn")

    def test_invalid_format(self) -> None:
        """Invalid formats fail."""
        assert not _validate_bitcoin_address("invalid")
        assert not _validate_bitcoin_address("0x123")
        assert not _validate_bitcoin_address("2NotValid123")


class TestEthereumAddressValidation:
    """Ethereum address format validation."""

    def test_valid_addresses(self) -> None:
        """Valid Ethereum addresses pass."""
        assert _validate_ethereum_address("0x" + "a" * 40)
        assert _validate_ethereum_address("0x" + "F" * 40)
        assert _validate_ethereum_address("0x1234567890123456789012345678901234567890")

    def test_case_insensitive(self) -> None:
        """Both upper and lowercase hex work."""
        assert _validate_ethereum_address("0xAbCdEfAbCdEfAbCdEfAbCdEfAbCdEfAbCdEfAbCd")
        assert _validate_ethereum_address("0xabcdefabcdefabcdefabcdefabcdefabcdefabcd")

    def test_invalid_format(self) -> None:
        """Invalid formats fail."""
        assert not _validate_ethereum_address("0x123")  # Too short
        assert not _validate_ethereum_address("123456789012345678901234567890123456789012")  # No 0x
        assert not _validate_ethereum_address("0x" + "G" * 40)  # Invalid hex char
        assert not _validate_ethereum_address("1A1z7agoat2LWUJW1GyeFLzHw2nd2ZKjhL")  # Bitcoin address


class TestRiskScoreCalculation:
    """Risk score calculation logic."""

    def test_new_wallet_high_risk(self) -> None:
        """Brand new wallets get higher risk scores."""
        metrics = {
            "days_old": 5,
            "transaction_count": 0,
            "current_balance": 1.0,
            "total_received": 1.0,
        }
        score, level = _calculate_risk_score(metrics)
        assert score > 50  # Should be high risk
        assert level in ("high", "critical")

    def test_old_wallet_low_risk(self) -> None:
        """Old wallets with activity get lower risk scores."""
        metrics = {
            "days_old": 2000,
            "transaction_count": 50,
            "current_balance": 0.5,
            "total_received": 10.0,
        }
        score, level = _calculate_risk_score(metrics)
        assert score < 50  # Should be low risk
        assert level in ("low", "medium")

    def test_no_transactions(self) -> None:
        """Wallets with no transactions get higher risk."""
        metrics = {
            "days_old": 100,
            "transaction_count": 0,
            "current_balance": 0,
            "total_received": 0,
        }
        score, level = _calculate_risk_score(metrics)
        assert score > 50

    def test_high_concentration(self) -> None:
        """High balance concentration (holding >80%) increases risk."""
        metrics = {
            "days_old": 100,
            "transaction_count": 10,
            "current_balance": 0.9,
            "total_received": 1.0,
        }
        score, level = _calculate_risk_score(metrics)
        assert score >= 50

    def test_distributed_balance(self) -> None:
        """Distributed balance (moved around) decreases risk."""
        metrics = {
            "days_old": 100,
            "transaction_count": 50,
            "current_balance": 0.1,
            "total_received": 10.0,
        }
        score, level = _calculate_risk_score(metrics)
        assert score < 60


@pytest.mark.asyncio
class TestCryptoRiskScore:
    """Integration tests for research_crypto_risk_score."""

    async def test_invalid_bitcoin_address(self) -> None:
        """Invalid Bitcoin address returns error."""
        result = await research_crypto_risk_score("invalid_btc", "bitcoin")
        assert result["error"] is not None
        assert result["risk_score"] is None

    async def test_invalid_ethereum_address(self) -> None:
        """Invalid Ethereum address returns error."""
        result = await research_crypto_risk_score("0x123", "ethereum")
        assert result["error"] is not None
        assert result["risk_score"] is None

    async def test_unsupported_chain(self) -> None:
        """Unsupported chain returns error."""
        result = await research_crypto_risk_score("1A1z7agoat2LWUJW1GyeFLzHw2nd2ZKjhL", "litecoin")
        assert result["error"] is not None
        assert "Unsupported chain" in result["error"]

    @patch("loom.tools.intelligence.crypto_risk.httpx.AsyncClient")
    async def test_bitcoin_success(self, mock_client_class) -> None:
        """Bitcoin address scoring succeeds with valid API response."""
        # Mock the blockchain.info API responses
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client

        # First call: balance endpoint
        balance_response = AsyncMock()
        balance_response.json.return_value = 100000000  # 1 BTC in satoshis

        # Second call: address details endpoint
        detail_response = AsyncMock()
        detail_response.json.return_value = {
            "n_tx": 10,
            "total_received": 500000000,  # 5 BTC
            "total_sent": 400000000,  # 4 BTC
            "first_tx": {"time": 1600000000},
            "latest_tx": {"time": 1700000000},
        }

        mock_client.get.side_effect = [balance_response, detail_response]
        mock_client_class.return_value = mock_client

        result = await research_crypto_risk_score("1A1z7agoat2LWUJW1GyeFLzHw2nd2ZKjhL", "bitcoin")

        assert result["address"] == "1A1z7agoat2LWUJW1GyeFLzHw2nd2ZKjhL"
        assert result["chain"] == "bitcoin"
        assert result["risk_score"] is not None
        assert 0 <= result["risk_score"] <= 100
        assert result["risk_level"] in ("low", "medium", "high", "critical")
        assert "metrics" in result
        assert result["metrics"]["transaction_count"] == 10

    async def test_response_structure(self) -> None:
        """Response has required fields even on error."""
        result = await research_crypto_risk_score("invalid", "bitcoin")
        assert "address" in result
        assert "chain" in result
        assert "risk_score" in result
        assert "risk_level" in result
        assert "metrics" in result
        assert "factors" in result
        assert isinstance(result["factors"], list)
