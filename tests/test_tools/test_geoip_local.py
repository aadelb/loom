"""Tests for local GeoIP database lookup (geoip_local)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
class TestResearchGeoipLocal:
    async def test_invalid_ip_address(self):
        """Test rejection of invalid IP addresses."""
        from loom.tools.intelligence.geoip_local import research_geoip_local

        result = await research_geoip_local("not-an-ip")

        assert "error" in result
        assert "Invalid IP address" in result["error"]

    async def test_private_ip_rejection(self):
        """Test rejection of private IP addresses."""
        from loom.tools.intelligence.geoip_local import research_geoip_local

        result = await research_geoip_local("192.168.1.1")

        assert "error" in result
        assert "Private IP" in result["error"]

    async def test_ipv4_private_rejection(self):
        """Test rejection of 10.0.0.0/8 range."""
        from loom.tools.intelligence.geoip_local import research_geoip_local

        result = await research_geoip_local("10.0.0.1")

        assert "error" in result

    async def test_localhost_rejection(self):
        """Test rejection of localhost."""
        from loom.tools.intelligence.geoip_local import research_geoip_local

        result = await research_geoip_local("127.0.0.1")

        assert "error" in result

    async def test_database_not_found(self):
        """Test error when database is not found."""
        with patch("loom.tools.intelligence.geoip_local._find_geoip_database", return_value=None):
            from loom.tools.intelligence.geoip_local import research_geoip_local

            result = await research_geoip_local("8.8.8.8")

            assert "error" in result
            assert "not found" in result["error"]

    async def test_successful_lookup(self):
        """Test successful GeoIP lookup."""
        mock_response = MagicMock()
        mock_response.country.iso_code = "US"
        mock_response.city.name = "New York"
        mock_response.subdivisions = [MagicMock(iso_code="NY")]
        mock_response.location.latitude = 40.7128
        mock_response.location.longitude = -74.0060
        mock_response.location.time_zone = "America/New_York"
        mock_response.location.accuracy_radius = 5
        mock_response.continent.code = "NA"
        mock_response.postal.code = "10001"

        with patch("loom.tools.intelligence.geoip_local._find_geoip_database", return_value="/path/to/db.mmdb"), patch(
            "loom.tools.intelligence.geoip_local._lookup_ip"
        ) as mock_lookup:
            mock_lookup.return_value = {
                "ip": "8.8.8.8",
                "country": "US",
                "city": "New York",
                "subdivision": "NY",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "timezone": "America/New_York",
                "continent": "NA",
                "postal_code": "10001",
                "accuracy_radius_km": 5,
                "source": "local_geoip2",
            }

            from loom.tools.intelligence.geoip_local import research_geoip_local

            result = await research_geoip_local("8.8.8.8")

            assert result["country"] == "US"
            assert result["city"] == "New York"
            assert result["latitude"] == 40.7128
            assert result["longitude"] == -74.0060

    async def test_response_has_required_keys(self):
        """Test that response has all expected keys."""
        mock_result = {
            "ip": "1.1.1.1",
            "country": "AU",
            "city": "Sydney",
            "subdivision": None,
            "latitude": -33.8688,
            "longitude": 151.2093,
            "timezone": "Australia/Sydney",
            "continent": "OC",
            "postal_code": "2000",
            "accuracy_radius_km": 1,
            "source": "local_geoip2",
        }

        with patch("loom.tools.intelligence.geoip_local._find_geoip_database", return_value="/path/to/db.mmdb"), patch(
            "loom.tools.intelligence.geoip_local._lookup_ip",
            return_value=mock_result,
        ):
            from loom.tools.intelligence.geoip_local import research_geoip_local

            result = await research_geoip_local("1.1.1.1")

            required_keys = ["ip", "country", "city", "latitude", "longitude", "timezone"]
            for key in required_keys:
                assert key in result


class TestValidateIp:
    def test_valid_ipv4(self):
        """Test validation of valid IPv4."""
        from loom.tools.intelligence.geoip_local import _validate_ip

        result = _validate_ip("8.8.8.8")
        assert result == "8.8.8.8"

    def test_valid_ipv6(self):
        """Test validation of valid IPv6."""
        from loom.tools.intelligence.geoip_local import _validate_ip

        result = _validate_ip("2001:4860:4860::8888")
        assert result == "2001:4860:4860::8888"

    def test_invalid_ipv4_raises_error(self):
        """Test that invalid IPv4 raises error."""
        from loom.tools.intelligence.geoip_local import _validate_ip

        with pytest.raises(ValueError):
            _validate_ip("256.256.256.256")

    def test_private_ipv4_raises_error(self):
        """Test that private IPv4 raises error."""
        from loom.tools.intelligence.geoip_local import _validate_ip

        with pytest.raises(ValueError):
            _validate_ip("192.168.0.1")

    def test_private_ipv6_raises_error(self):
        """Test that private IPv6 raises error."""
        from loom.tools.intelligence.geoip_local import _validate_ip

        with pytest.raises(ValueError):
            _validate_ip("::1")  # IPv6 localhost


class TestFindGeoipDatabase:
    def test_database_found_at_first_location(self):
        """Test finding database at first common location."""
        with patch("os.path.isfile") as mock_isfile:
            # First location exists
            mock_isfile.return_value = True

            from loom.tools.intelligence.geoip_local import _find_geoip_database

            result = _find_geoip_database()

            assert result is not None
            assert "GeoLite2" in result

    def test_database_not_found_at_any_location(self):
        """Test when database doesn't exist at any location."""
        with patch("os.path.isfile", return_value=False):
            from loom.tools.intelligence.geoip_local import _find_geoip_database

            result = _find_geoip_database()

            assert result is None

    def test_checks_multiple_locations(self):
        """Test that multiple database locations are checked."""
        with patch("os.path.isfile") as mock_isfile, patch("os.path.expanduser") as mock_expand:
            mock_isfile.side_effect = [False, False, True]  # Found at 3rd location
            mock_expand.side_effect = lambda x: x.replace("~", "/home/user")

            from loom.tools.intelligence.geoip_local import _find_geoip_database

            result = _find_geoip_database()

            # Should have called expanduser multiple times
            assert mock_expand.call_count >= 2


class TestLookupIp:
    def test_geoip2_import_error(self):
        """Test handling when geoip2 is not installed."""
        with patch.dict("sys.modules", {"geoip2": None, "geoip2.database": None}):
            from loom.tools.intelligence.geoip_local import _lookup_ip

            result = _lookup_ip("/path/to/db.mmdb", "8.8.8.8")

            assert "error" in result
            assert "geoip2" in result["error"].lower()

    def test_database_read_error(self):
        """Test handling of database read errors."""
        with patch("geoip2.database.Reader") as mock_reader:
            mock_reader.side_effect = Exception("Database corrupted")

            from loom.tools.intelligence.geoip_local import _lookup_ip

            result = _lookup_ip("/path/to/db.mmdb", "8.8.8.8")

            assert "error" in result

    def test_successful_blocking_lookup(self):
        """Test successful blocking lookup."""
        mock_reader = MagicMock()
        mock_response = MagicMock()
        mock_response.country.iso_code = "US"
        mock_response.city.name = "San Francisco"
        mock_response.subdivisions = []
        mock_response.location.latitude = 37.7749
        mock_response.location.longitude = -122.4194
        mock_response.location.time_zone = "America/Los_Angeles"
        mock_response.location.accuracy_radius = 10
        mock_response.continent.code = "NA"
        mock_response.postal.code = "94105"

        with patch("geoip2.database.Reader") as mock_reader_cls:
            mock_reader_cls.return_value.__enter__.return_value.city.return_value = mock_response

            from loom.tools.intelligence.geoip_local import _lookup_ip

            result = _lookup_ip("/path/to/db.mmdb", "8.8.8.8")

            assert result["country"] == "US"
            assert result["city"] == "San Francisco"
            assert result["latitude"] == 37.7749


class TestExtractGpsInfo:
    def test_no_gps_info(self):
        """Test when EXIF data has no GPS info."""
        from loom.tools.intelligence.geoip_local import _extract_gps_info

        exif_dict = {306: "DateTime"}

        result = _extract_gps_info(exif_dict)

        assert result is None

    def test_gps_extraction_success(self):
        """Test successful GPS extraction from EXIF."""
        from loom.tools.intelligence.geoip_local import _extract_gps_info

        # DMS format: (degrees, minutes, seconds) each as (numerator, denominator)
        exif_dict = {
            34853: {  # GPSInfo
                1: "N",  # North
                2: ((40, 1), (42, 1), (46, 1)),  # Latitude DMS
                3: "W",  # West
                4: ((73, 1), (58, 1), (56, 1)),  # Longitude DMS
            }
        }

        result = _extract_gps_info(exif_dict)

        assert result is not None
        assert "latitude" in result
        assert "longitude" in result
        # Should be positive latitude (North)
        assert result["latitude"] > 0
        # Should be negative longitude (West)
        assert result["longitude"] < 0

    def test_gps_south_west_coordinates(self):
        """Test GPS extraction for South/West coordinates."""
        from loom.tools.intelligence.geoip_local import _extract_gps_info

        exif_dict = {
            34853: {
                1: "S",  # South
                2: ((40, 1), (42, 1), (46, 1)),
                3: "W",  # West
                4: ((73, 1), (58, 1), (56, 1)),
            }
        }

        result = _extract_gps_info(exif_dict)

        assert result is not None
        # Should be negative latitude (South)
        assert result["latitude"] < 0
        # Should be negative longitude (West)
        assert result["longitude"] < 0
