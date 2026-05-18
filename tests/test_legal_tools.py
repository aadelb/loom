"""Test suite for UAE/Dubai legal compliance tools."""
import asyncio
import pytest
from loom.tools.legal.uae_legal import (
    research_uae_labor_law,
    research_uae_trade_license,
    research_uae_food_safety,
    research_uae_visa_rules,
    research_uae_commercial_law,
    research_uae_customs,
    research_uae_rera,
    research_uae_tax_compliance,
)
from loom.params.legal import (
    UaeLaborLawParams,
    UaeTradeLicenseParams,
    UaeFoodSafetyParams,
    UaeVisaRulesParams,
    UaeCommercialLawParams,
    UaeCustomsParams,
    UaeReraParams,
    UaeTaxComplianceParams,
)


class TestParamValidation:
    """Test parameter validation for all legal tools."""

    def test_labor_law_params_valid(self):
        """Test valid labor law params."""
        params = UaeLaborLawParams(query="What is minimum wage?", topic="salary")
        assert params.query == "What is minimum wage?"
        assert params.topic == "salary"

    def test_labor_law_params_default_topic(self):
        """Test labor law params with default topic."""
        params = UaeLaborLawParams(query="General question")
        assert params.topic == "general"

    def test_labor_law_params_invalid_topic(self):
        """Test labor law params with invalid topic."""
        with pytest.raises(Exception):
            UaeLaborLawParams(query="test", topic="invalid_topic")

    def test_labor_law_params_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(Exception):
            UaeLaborLawParams(query="test", topic="general", extra_field="fail")

    def test_labor_law_params_min_length(self):
        """Test query minimum length validation."""
        with pytest.raises(Exception):
            UaeLaborLawParams(query="")

    def test_labor_law_params_max_length(self):
        """Test query maximum length validation."""
        with pytest.raises(Exception):
            UaeLaborLawParams(query="x" * 501)

    def test_trade_license_params_valid(self):
        """Test valid trade license params."""
        params = UaeTradeLicenseParams(
            business_type="commercial",
            emirate="dubai",
            free_zone=True
        )
        assert params.business_type == "commercial"
        assert params.emirate == "dubai"
        assert params.free_zone is True

    def test_trade_license_params_default_emirate(self):
        """Test trade license with default emirate."""
        params = UaeTradeLicenseParams(business_type="professional")
        assert params.emirate == "ajman"

    def test_trade_license_params_invalid_emirate(self):
        """Test trade license with invalid emirate."""
        with pytest.raises(Exception):
            UaeTradeLicenseParams(business_type="commercial", emirate="invalid")

    def test_food_safety_params_valid(self):
        """Test valid food safety params."""
        params = UaeFoodSafetyParams(
            query="HACCP certification requirements?",
            business_type="restaurant"
        )
        assert params.business_type == "restaurant"

    def test_food_safety_params_default_business_type(self):
        """Test food safety with default business type."""
        params = UaeFoodSafetyParams(query="test")
        assert params.business_type == "supermarket"

    def test_visa_params_valid(self):
        """Test valid visa params."""
        params = UaeVisaRulesParams(
            visa_type="golden",
            nationality="Indian",
            query="How long does processing take?"
        )
        assert params.visa_type == "golden"
        assert params.nationality == "Indian"

    def test_visa_params_default_type(self):
        """Test visa with default type."""
        params = UaeVisaRulesParams()
        assert params.visa_type == "employment"

    def test_commercial_law_params_valid(self):
        """Test valid commercial law params."""
        params = UaeCommercialLawParams(
            query="How to form LLC?",
            topic="company_formation"
        )
        assert params.topic == "company_formation"

    def test_customs_params_valid(self):
        """Test valid customs params."""
        params = UaeCustomsParams(
            product_category="electronics",
            origin_country="USA"
        )
        assert params.product_category == "electronics"

    def test_customs_params_invalid_category(self):
        """Test customs with invalid product category."""
        with pytest.raises(Exception):
            UaeCustomsParams(product_category="invalid")

    def test_rera_params_valid(self):
        """Test valid RERA params."""
        params = UaeReraParams(
            query="Ejari registration cost?",
            transaction_type="rent"
        )
        assert params.transaction_type == "rent"

    def test_tax_compliance_params_valid(self):
        """Test valid tax compliance params."""
        params = UaeTaxComplianceParams(
            query="VAT threshold?",
            tax_type="vat"
        )
        assert params.tax_type == "vat"


class TestToolFunctions:
    """Test tool functions return proper structure."""

    @pytest.mark.asyncio
    async def test_labor_law_tool(self):
        """Test labor law tool execution."""
        result = await research_uae_labor_law("minimum wage", topic="salary")
        assert isinstance(result, dict)
        assert "query" in result
        assert "topic" in result
        assert "source" in result
        assert "data" in result
        assert result["topic"] == "salary"

    @pytest.mark.asyncio
    async def test_labor_law_tool_all_topics(self):
        """Test labor law tool with all topics."""
        topics = [
            "general", "termination", "salary", "leave", "gratuity",
            "visa_cancellation", "part_time", "probation", "discrimination", "work_hours"
        ]
        for topic in topics:
            result = await research_uae_labor_law("test", topic=topic)
            assert result["topic"] == topic
            assert "data" in result

    @pytest.mark.asyncio
    async def test_trade_license_tool(self):
        """Test trade license tool execution."""
        result = await research_uae_trade_license("commercial", emirate="dubai")
        assert isinstance(result, dict)
        assert "business_type" in result
        assert "emirate" in result
        assert "license_info" in result
        assert "renewal" in result

    @pytest.mark.asyncio
    async def test_food_safety_tool(self):
        """Test food safety tool execution."""
        result = await research_uae_food_safety("HACCP", business_type="restaurant")
        assert isinstance(result, dict)
        assert "business_type" in result
        assert "requirements" in result
        assert "labeling_rules" in result
        assert "halal_certification" in result

    @pytest.mark.asyncio
    async def test_visa_rules_tool(self):
        """Test visa rules tool execution."""
        result = await research_uae_visa_rules(visa_type="golden")
        assert isinstance(result, dict)
        assert "visa_type" in result
        assert "visa_details" in result
        assert result["visa_type"] == "golden"

    @pytest.mark.asyncio
    async def test_commercial_law_tool(self):
        """Test commercial law tool execution."""
        result = await research_uae_commercial_law("LLC formation", topic="company_formation")
        assert isinstance(result, dict)
        assert "topic" in result
        assert "legal_reference" in result
        assert "overview" in result

    @pytest.mark.asyncio
    async def test_customs_tool(self):
        """Test customs tool execution."""
        result = await research_uae_customs("electronics", origin_country="USA")
        assert isinstance(result, dict)
        assert "product_category" in result
        assert "tariff_rates" in result
        assert "documentation" in result
        assert "prohibited_items" in result

    @pytest.mark.asyncio
    async def test_rera_tool(self):
        """Test RERA tool execution."""
        result = await research_uae_rera("Ejari cost", transaction_type="rent")
        assert isinstance(result, dict)
        assert "transaction_type" in result
        assert "legal_reference" in result
        assert "authority" in result
        assert "regulations" in result

    @pytest.mark.asyncio
    async def test_tax_compliance_tool(self):
        """Test tax compliance tool execution."""
        result = await research_uae_tax_compliance("VAT threshold", tax_type="vat")
        assert isinstance(result, dict)
        assert "tax_type" in result
        assert "tax_details" in result
        assert "fta_registration" in result


class TestDataCompleteness:
    """Test that embedded legal data is comprehensive."""

    def test_labor_law_topics_complete(self):
        """Test labor law has all required topics."""
        from loom.tools.legal.uae_legal import UAE_LABOR_LAW_TOPICS
        required = [
            "general", "termination", "salary", "leave", "gratuity",
            "visa_cancellation", "part_time", "probation", "discrimination", "work_hours"
        ]
        for topic in required:
            assert topic in UAE_LABOR_LAW_TOPICS
            assert "legal_reference" in UAE_LABOR_LAW_TOPICS[topic]

    def test_visa_types_complete(self):
        """Test all visa types are documented."""
        from loom.tools.legal.uae_legal import UAE_VISA_TYPES
        required = [
            "employment", "investor", "golden", "green", "tourist", "family", "domestic_worker"
        ]
        for visa_type in required:
            assert visa_type in UAE_VISA_TYPES

    def test_trade_license_emirates_complete(self):
        """Test trade licenses for all emirates."""
        from loom.tools.legal.uae_legal import UAE_TRADE_LICENSES
        assert "commercial" in UAE_TRADE_LICENSES
        assert "professional" in UAE_TRADE_LICENSES
        assert "industrial" in UAE_TRADE_LICENSES

    def test_customs_tariff_data(self):
        """Test customs has tariff data."""
        from loom.tools.legal.uae_legal import UAE_CUSTOMS
        assert "tariff_rates" in UAE_CUSTOMS
        assert "products" in UAE_CUSTOMS["tariff_rates"]
        assert len(UAE_CUSTOMS["tariff_rates"]["products"]) > 0

    def test_rera_data_complete(self):
        """Test RERA has all transaction types."""
        from loom.tools.legal.uae_legal import DUBAI_RERA
        assert "regulations" in DUBAI_RERA
        assert "rent" in DUBAI_RERA["regulations"]
        assert "buy" in DUBAI_RERA["regulations"]

    def test_tax_types_complete(self):
        """Test all tax types documented."""
        from loom.tools.legal.uae_legal import UAE_TAX_COMPLIANCE
        assert "vat" in UAE_TAX_COMPLIANCE
        assert "corporate_tax" in UAE_TAX_COMPLIANCE
        assert "excise_tax" in UAE_TAX_COMPLIANCE


class TestLegalReferences:
    """Test that legal references are accurate."""

    def test_labor_law_reference(self):
        """Test correct labor law reference."""
        from loom.tools.legal.uae_legal import UAE_LABOR_LAW_TOPICS
        assert UAE_LABOR_LAW_TOPICS["general"]["legal_reference"] == "Federal Decree-Law No. 33/2021"

    def test_commercial_law_reference(self):
        """Test correct commercial law reference."""
        from loom.tools.legal.uae_legal import UAE_COMMERCIAL_LAW
        assert "Federal Law No. 50/2022" in UAE_COMMERCIAL_LAW["legal_reference"]

    def test_rera_reference(self):
        """Test correct RERA reference."""
        from loom.tools.legal.uae_legal import DUBAI_RERA
        assert "Dubai Law No. 26/2007" in DUBAI_RERA["legal_reference"]

    def test_tax_reference(self):
        """Test correct tax references."""
        from loom.tools.legal.uae_legal import UAE_TAX_COMPLIANCE
        assert UAE_TAX_COMPLIANCE["vat"]["legal_reference"] == "Federal Decree-Law No. 8/2017"
        assert "Federal Decree-Law No. 47/2022" in UAE_TAX_COMPLIANCE["corporate_tax"]["legal_reference"]
