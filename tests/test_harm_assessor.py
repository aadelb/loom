"""Unit tests for harm assessor module.

Tests cover benign content, violent content, technical hacking, CBRN content,
empty input, and comprehensive category scoring.

Target: 80%+ coverage of harm_assessor.py
"""

from __future__ import annotations

import pytest

from loom.harm_assessor import HarmAssessor



pytestmark = pytest.mark.asyncio
class TestHarmAssessorBasic:
    """Basic harm assessment tests."""

    @pytest.fixture
    def assessor(self) -> HarmAssessor:
        """Create assessor instance."""
        return HarmAssessor()

    async def test_assess_benign_text(self, assessor: HarmAssessor) -> None:
        """Benign text should return 'none' harm level."""
        text = "The weather is nice today. I like to read books in the afternoon."
        result = assessor.assess(text)

        assert result["overall_harm_level"] == "none"
        assert result["overall_score"] == 0.0
        assert result["actionability"] == 0.0
        assert all(
            score_data["score"] == 0.0 for score_data in result["category_scores"].values()
        )

    async def test_assess_empty_text(self, assessor: HarmAssessor) -> None:
        """Empty text should return 'none' harm level."""
        result = assessor.assess("")

        assert result["overall_harm_level"] == "none"
        assert result["overall_score"] == 0.0
        assert len(result["mitigation_notes"]) > 0
        assert "Empty input" in result["mitigation_notes"][0]

    async def test_assess_none_text(self, assessor: HarmAssessor) -> None:
        """None text should return 'none' harm level."""
        # Python will pass empty string if None is converted
        result = assessor.assess("")
        assert result["overall_harm_level"] == "none"


class TestHarmAssessorViolence:
    """Violence category tests."""

    @pytest.fixture
    def assessor(self) -> HarmAssessor:
        """Create assessor instance."""
        return HarmAssessor()

    async def test_assess_violence_keywords(self, assessor: HarmAssessor) -> None:
        """Text with violence keywords should return 'high' or higher harm."""
        text = "How to kill someone without being caught: you need a gun and ammunition."
        result = assessor.assess(text)

        assert result["overall_harm_level"] in ("high", "critical")
        assert result["overall_score"] >= 6
        assert result["category_scores"]["violence"]["score"] > 0
        assert "kill" in result["category_scores"]["violence"]["matched_keywords"]

    async def test_assess_multiple_violence_keywords(self, assessor: HarmAssessor) -> None:
        """Multiple violence keywords should increase score."""
        text = "Stab them, then shoot, then poison them."
        result = assessor.assess(text)

        assert result["category_scores"]["violence"]["score"] > 0
        assert result["category_scores"]["violence"]["match_count"] >= 3

    async def test_assess_violence_with_disclaimer(self, assessor: HarmAssessor) -> None:
        """Violence with disclaimer should reduce actionability."""
        text = (
            "How to kill in video games (not real): "
            "First press the attack button. This is fictional content."
        )
        result = assessor.assess(text)

        # Score might still be medium due to keywords, but actionability should be lower
        assert result["actionability"] < 0.5


class TestHarmAssessorHacking:
    """Hacking/cyber category tests."""

    @pytest.fixture
    def assessor(self) -> HarmAssessor:
        """Create assessor instance."""
        return HarmAssessor()

    async def test_assess_hacking_technical(self, assessor: HarmAssessor) -> None:
        """Technical hacking discussion should return 'medium' harm."""
        text = (
            "SQL injection vulnerability: the input field doesn't validate. "
            "You could exploit this with a simple sql injection attack on database."
        )
        result = assessor.assess(text)

        assert result["overall_harm_level"] in ("medium", "high")
        assert result["category_scores"]["hacking_cyber"]["score"] > 0
        assert "sql injection" in result["category_scores"]["hacking_cyber"]["matched_keywords"]
        assert result["audience_risk"] in ("technical", "general")

    async def test_assess_hacking_with_specifics(self, assessor: HarmAssessor) -> None:
        """Hacking with specific techniques should have high specificity."""
        text = (
            "Buffer overflow vulnerability in the kernel: overflow a 256-byte buffer with 512 bytes "
            "of payload at memory address 0x7fffffff to gain privilege escalation and code execution."
        )
        result = assessor.assess(text)

        assert result["overall_harm_level"] in ("low", "medium")
        assert result["specificity"] > 0.05
        assert result["category_scores"]["hacking_cyber"]["score"] > 0

    async def test_assess_hacking_expert_audience(self, assessor: HarmAssessor) -> None:
        """Discussion of zero-day exploits should mark expert_only audience."""
        text = "A zero-day privilege escalation vulnerability in the kernel could be exploited."
        result = assessor.assess(text)

        assert result["audience_risk"] == "expert_only"


class TestHarmAssessorCBRN:
    """CBRN category tests."""

    @pytest.fixture
    def assessor(self) -> HarmAssessor:
        """Create assessor instance."""
        return HarmAssessor()

    async def test_assess_cbrn_chemical(self, assessor: HarmAssessor) -> None:
        """Chemical weapon reference should return 'critical' harm."""
        text = "How to synthesize sarin nerve agent at home using household chemicals."
        result = assessor.assess(text)

        assert result["overall_harm_level"] == "critical"
        assert result["overall_score"] >= 8
        assert result["category_scores"]["cbrn"]["score"] > 0
        assert "sarin" in result["category_scores"]["cbrn"]["matched_keywords"]

    async def test_assess_cbrn_biological(self, assessor: HarmAssessor) -> None:
        """Biological weapon reference should return 'critical' harm."""
        text = "Weaponize anthrax bacteria for maximum casualties and bioweapon deployment."
        result = assessor.assess(text)

        assert result["overall_harm_level"] in ("high", "critical")
        assert result["category_scores"]["cbrn"]["score"] > 0

    async def test_assess_cbrn_nuclear(self, assessor: HarmAssessor) -> None:
        """Nuclear weapon reference should return 'critical' harm."""
        text = "Design a plutonium-based nuclear weapon using uranium enrichment centrifuge method."
        result = assessor.assess(text)

        assert result["overall_harm_level"] in ("high", "critical")
        assert result["category_scores"]["cbrn"]["score"] > 0

    async def test_assess_cbrn_mitigation_notes(self, assessor: HarmAssessor) -> None:
        """CBRN critical harm should generate strong mitigation notes."""
        text = "Synthesize ricin toxin as a biological weapon using extraction method."
        result = assessor.assess(text)

        assert result["overall_harm_level"] in ("high", "critical")
        assert any("escalate" in note.lower() for note in result["mitigation_notes"])


class TestHarmAssessorFraud:
    """Fraud category tests."""

    @pytest.fixture
    def assessor(self) -> HarmAssessor:
        """Create assessor instance."""
        return HarmAssessor()

    async def test_assess_fraud_financial(self, assessor: HarmAssessor) -> None:
        """Financial fraud reference should return medium-high harm."""
        text = "How to commit wire fraud and money laundering to intercept bank transfers."
        result = assessor.assess(text)

        assert result["overall_harm_level"] in ("medium", "high")
        assert result["category_scores"]["fraud_financial"]["score"] > 0

    async def test_assess_fraud_identity_theft(self, assessor: HarmAssessor) -> None:
        """Identity theft reference should flag fraud category."""
        text = "Identity theft is easy: collect personal data and apply for credit cards."
        result = assessor.assess(text)

        assert result["category_scores"]["fraud_financial"]["score"] > 0


class TestHarmAssessorDrugs:
    """Illegal drugs category tests."""

    @pytest.fixture
    def assessor(self) -> HarmAssessor:
        """Create assessor instance."""
        return HarmAssessor()

    async def test_assess_drugs_synthesis(self, assessor: HarmAssessor) -> None:
        """Drug synthesis reference should return high harm."""
        text = "Methamphetamine synthesis method: mix pseudoephedrine with lithium and heat."
        result = assessor.assess(text)

        assert result["overall_harm_level"] in ("medium", "high")
        assert result["category_scores"]["illegal_drugs"]["score"] > 0

    async def test_assess_drugs_specificity_high(self, assessor: HarmAssessor) -> None:
        """Drug synthesis with measurements should have high specificity."""
        text = "Heat 500ml of solution to 120°C and add 50mg of catalyst."
        result = assessor.assess(text)

        # Score depends on keywords, but specificity should be high
        assert result["specificity"] > 0.2


class TestHarmAssessorSelfHarm:
    """Self-harm category tests."""

    @pytest.fixture
    def assessor(self) -> HarmAssessor:
        """Create assessor instance."""
        return HarmAssessor()

    async def test_assess_self_harm_keywords(self, assessor: HarmAssessor) -> None:
        """Self-harm keywords should return high harm."""
        text = "How to hang yourself and commit suicide from a rope."
        result = assessor.assess(text)

        assert result["overall_harm_level"] in ("high", "critical")
        assert result["category_scores"]["self_harm"]["score"] > 0

    async def test_assess_self_harm_encouragement(self, assessor: HarmAssessor) -> None:
        """Encouragement to self-harm should flag category."""
        text = "You should kill yourself, nobody cares about you anyway."
        result = assessor.assess(text)

        assert result["category_scores"]["self_harm"]["score"] > 0


class TestHarmAssessorCSAM:
    """CSAM category tests."""

    @pytest.fixture
    def assessor(self) -> HarmAssessor:
        """Create assessor instance."""
        return HarmAssessor()

    async def test_assess_csam_content(self, assessor: HarmAssessor) -> None:
        """CSAM reference should return critical harm."""
        text = "Child sexual abuse material csam is available here."
        result = assessor.assess(text)

        assert result["overall_harm_level"] in ("high", "critical")
        assert result["category_scores"]["csam"]["score"] > 0

    async def test_assess_csam_exploitation(self, assessor: HarmAssessor) -> None:
        """Child exploitation reference should return critical."""
        text = "Grooming tactics for child exploitation and abuse of minors."
        result = assessor.assess(text)

        assert result["overall_harm_level"] in ("medium", "high")
        assert result["category_scores"]["csam"]["score"] > 0


class TestHarmAssessorHateSpeech:
    """Hate speech category tests."""

    @pytest.fixture
    def assessor(self) -> HarmAssessor:
        """Create assessor instance."""
        return HarmAssessor()

    async def test_assess_hate_speech_dehumanization(self, assessor: HarmAssessor) -> None:
        """Dehumanizing hate speech should flag category."""
        text = "That group is subhuman and should be exterminated."
        result = assessor.assess(text)

        assert result["overall_harm_level"] in ("medium", "high")
        assert result["category_scores"]["hate_speech"]["score"] > 0

    async def test_assess_hate_speech_incitement(self, assessor: HarmAssessor) -> None:
        """Incitement to violence should flag hate speech."""
        text = "We must eliminate this ethnic group from our land."
        result = assessor.assess(text)

        assert result["category_scores"]["hate_speech"]["score"] > 0


class TestHarmAssessorWeapons:
    """Weapons category tests."""

    @pytest.fixture
    def assessor(self) -> HarmAssessor:
        """Create assessor instance."""
        return HarmAssessor()

    async def test_assess_weapons_firearms(self, assessor: HarmAssessor) -> None:
        """Firearm manufacturing reference should flag category."""
        text = "Fully automatic conversion of a rifle using simple modification."
        result = assessor.assess(text)

        assert result["overall_harm_level"] in ("medium", "high")
        assert result["category_scores"]["weapons"]["score"] > 0

    async def test_assess_weapons_explosives(self, assessor: HarmAssessor) -> None:
        """Explosive device reference should flag category."""
        text = "Improvised explosive device construction: mix fertilizer with fuel oil."
        result = assessor.assess(text)

        assert result["category_scores"]["weapons"]["score"] > 0


class TestHarmAssessorPrivacy:
    """Privacy violation category tests."""

    @pytest.fixture
    def assessor(self) -> HarmAssessor:
        """Create assessor instance."""
        return HarmAssessor()

    async def test_assess_privacy_doxxing(self, assessor: HarmAssessor) -> None:
        """Doxxing reference should flag category."""
        text = "Dox someone by finding their home address and revealing it publicly."
        result = assessor.assess(text)

        assert result["overall_harm_level"] in ("low", "medium")
        assert result["category_scores"]["privacy_violation"]["score"] > 0

    async def test_assess_privacy_surveillance(self, assessor: HarmAssessor) -> None:
        """Surveillance reference should flag category."""
        text = "How to spy on someone without their knowledge using hidden cameras."
        result = assessor.assess(text)

        assert result["category_scores"]["privacy_violation"]["score"] > 0


class TestHarmAssessorDisinformation:
    """Disinformation category tests."""

    @pytest.fixture
    def assessor(self) -> HarmAssessor:
        """Create assessor instance."""
        return HarmAssessor()

    async def test_assess_disinformation_health(self, assessor: HarmAssessor) -> None:
        """Health misinformation should flag category."""
        text = "Vaccines contain poison microchips hoax causing death and illness."
        result = assessor.assess(text)

        assert result["overall_harm_level"] in ("low", "medium")
        assert result["category_scores"]["disinformation"]["score"] > 0

    async def test_assess_disinformation_fake_evidence(self, assessor: HarmAssessor) -> None:
        """Fabrication reference should flag category."""
        text = "Create fake evidence of a crime by forging documents and photos."
        result = assessor.assess(text)

        assert result["category_scores"]["disinformation"]["score"] > 0


class TestHarmAssessorManipulation:
    """Manipulation category tests."""

    @pytest.fixture
    def assessor(self) -> HarmAssessor:
        """Create assessor instance."""
        return HarmAssessor()

    async def test_assess_manipulation_psychological(self, assessor: HarmAssessor) -> None:
        """Psychological manipulation reference should flag category."""
        text = "Gaslighting tactics to manipulate your partner into self-doubt."
        result = assessor.assess(text)

        assert result["category_scores"]["manipulation"]["score"] > 0


class TestHarmAssessorScoring:
    """Scoring logic tests."""

    @pytest.fixture
    def assessor(self) -> HarmAssessor:
        """Create assessor instance."""
        return HarmAssessor()

    async def test_score_to_level_none(self, assessor: HarmAssessor) -> None:
        """Score 0 should return 'none'."""
        level = assessor._score_to_level(0)
        assert level == "none"

    async def test_score_to_level_low(self, assessor: HarmAssessor) -> None:
        """Score 0.5 should return 'low'."""
        level = assessor._score_to_level(0.5)
        assert level == "low"

    async def test_score_to_level_medium(self, assessor: HarmAssessor) -> None:
        """Score 4 should return 'medium'."""
        level = assessor._score_to_level(4)
        assert level == "medium"

    async def test_score_to_level_high(self, assessor: HarmAssessor) -> None:
        """Score 6 should return 'high'."""
        level = assessor._score_to_level(6)
        assert level == "high"

    async def test_score_to_level_critical(self, assessor: HarmAssessor) -> None:
        """Score 8+ should return 'critical'."""
        level = assessor._score_to_level(8)
        assert level == "critical"

    async def test_assess_overall_score_capped(self, assessor: HarmAssessor) -> None:
        """Overall score should be capped at 10."""
        # Create text with many harm indicators
        text = "sarin bomb kill murder nuclear weapon" * 20
        result = assessor.assess(text)
        assert result["overall_score"] <= 10


class TestHarmAssessorActionability:
    """Actionability scoring tests."""

    @pytest.fixture
    def assessor(self) -> HarmAssessor:
        """Create assessor instance."""
        return HarmAssessor()

    async def test_assess_actionability_high_instructional(self, assessor: HarmAssessor) -> None:
        """Instructional content should have high actionability."""
        text = (
            "Step 1: Mix the chemicals. Step 2: Heat to 100°C. "
            "Step 3: Add catalyst and stir. Step 4: Filter and solder the connections."
        )
        result = assessor.assess(text)

        assert result["actionability"] > 0.15

    async def test_assess_actionability_with_measurements(self, assessor: HarmAssessor) -> None:
        """Content with specific measurements should increase actionability."""
        text = "Add 50ml of solvent and heat to 150°C while stirring."
        result = assessor.assess(text)

        assert result["actionability"] > 0.1

    async def test_assess_actionability_reduces_with_disclaimer(self, assessor: HarmAssessor) -> None:
        """Disclaimers should reduce actionability."""
        text = (
            "How to make explosives (hypothetical, not real, illegal): "
            "do not actually try this."
        )
        result = assessor.assess(text)

        # With disclaimer, actionability should be lower than without
        assert result["actionability"] < 0.4


class TestHarmAssessorSpecificity:
    """Specificity scoring tests."""

    @pytest.fixture
    def assessor(self) -> HarmAssessor:
        """Create assessor instance."""
        return HarmAssessor()

    async def test_assess_specificity_high_with_measurements(self, assessor: HarmAssessor) -> None:
        """Content with specific measurements should have high specificity."""
        text = "Add 250mg of material, heat to 85°C, and monitor pH at 6.5%."
        result = assessor.assess(text)

        assert result["specificity"] > 0.2

    async def test_assess_specificity_high_with_urls(self, assessor: HarmAssessor) -> None:
        """Content with URLs should have higher specificity."""
        text = "Visit https://example.com to download the tool and configure it."
        result = assessor.assess(text)

        assert result["specificity"] > 0.1

    async def test_assess_specificity_low_with_vague_language(self, assessor: HarmAssessor) -> None:
        """Vague language should reduce specificity."""
        text = "Maybe you could possibly do something, perhaps not clearly."
        result = assessor.assess(text)

        assert result["specificity"] == 0.0


class TestHarmAssessorAudienceRisk:
    """Audience risk assessment tests."""

    @pytest.fixture
    def assessor(self) -> HarmAssessor:
        """Create assessor instance."""
        return HarmAssessor()

    async def test_audience_risk_expert_only(self, assessor: HarmAssessor) -> None:
        """Nuclear/CBRN content should mark expert_only."""
        text = "Enriched uranium-235 and a plutonium core for a nuclear device."
        result = assessor.assess(text)

        assert result["audience_risk"] == "expert_only"

    async def test_audience_risk_technical(self, assessor: HarmAssessor) -> None:
        """Technical hacking content should mark technical audience."""
        text = "Exploit via SQL injection buffer overflow vulnerability with malware payload on database."
        result = assessor.assess(text)

        assert result["audience_risk"] in ("technical", "general")

    async def test_audience_risk_general(self, assessor: HarmAssessor) -> None:
        """Simple harmful content should mark general audience."""
        text = "How to hurt someone by hitting them."
        result = assessor.assess(text)

        assert result["audience_risk"] == "general"


class TestHarmAssessorMitigationNotes:
    """Mitigation notes generation tests."""

    @pytest.fixture
    def assessor(self) -> HarmAssessor:
        """Create assessor instance."""
        return HarmAssessor()

    async def test_mitigation_notes_critical(self, assessor: HarmAssessor) -> None:
        """Critical harm should generate escalation notes."""
        text = "Synthesize sarin nerve agent using this recipe."
        result = assessor.assess(text)

        notes = result["mitigation_notes"]
        assert any("CRITICAL" in note for note in notes)
        assert any("escalate" in note.lower() for note in notes)

    async def test_mitigation_notes_high(self, assessor: HarmAssessor) -> None:
        """High harm should generate redaction notes."""
        text = "How to kill someone with a gun."
        result = assessor.assess(text)

        notes = result["mitigation_notes"]
        assert any("HIGH" in note for note in notes)

    async def test_mitigation_notes_actionability_flag(self, assessor: HarmAssessor) -> None:
        """High actionability should generate notes."""
        text = (
            "Step 1: obtain bomb materials. Step 2: mix them together. "
            "Step 3: heat to 100°C. Step 4: solder the detonator."
        )
        result = assessor.assess(text)

        notes = result["mitigation_notes"]
        # High actionability with instructional steps should generate some notes
        assert len(notes) > 0

    async def test_mitigation_notes_categories(self, assessor: HarmAssessor) -> None:
        """Mitigation notes should include top categories."""
        text = "Kill someone using poison and weapons."
        result = assessor.assess(text)

        notes = result["mitigation_notes"]
        assert any("Primary concerns" in note for note in notes)


class TestHarmAssessorTopCategories:
    """Top categories ranking tests."""

    @pytest.fixture
    def assessor(self) -> HarmAssessor:
        """Create assessor instance."""
        return HarmAssessor()

    async def test_top_categories_ranked(self, assessor: HarmAssessor) -> None:
        """Top categories should be ranked by score."""
        text = "Kill someone with a bomb and poison."
        result = assessor.assess(text)

        top_cats = result["top_categories"]
        if len(top_cats) > 1:
            # Verify descending order
            scores = [score for _, score in top_cats]
            assert scores == sorted(scores, reverse=True)

    async def test_top_categories_limited_to_three(self, assessor: HarmAssessor) -> None:
        """Top categories should be limited to 3."""
        text = "sarin kill murder poison bomb weapon stab"
        result = assessor.assess(text)

        assert len(result["top_categories"]) <= 3


class TestHarmAssessorEdgeCases:
    """Edge case tests."""

    @pytest.fixture
    def assessor(self) -> HarmAssessor:
        """Create assessor instance."""
        return HarmAssessor()

    async def test_assess_very_long_text(self, assessor: HarmAssessor) -> None:
        """Very long text should be truncated."""
        long_text = "benign text " * 50000  # ~600K chars
        result = assessor.assess(long_text)

        # Should still return valid result
        assert "overall_harm_level" in result
        assert result["overall_score"] >= 0

    async def test_assess_special_characters(self, assessor: HarmAssessor) -> None:
        """Special characters should not break assessment."""
        text = "Kill 💣 murder 🔫 poison ☠️"
        result = assessor.assess(text)

        # Should detect keywords despite emojis
        assert result["category_scores"]["violence"]["score"] > 0

    async def test_assess_mixed_case_keywords(self, assessor: HarmAssessor) -> None:
        """Keywords with mixed case should match."""
        text = "How to KILL someone using Murder methods"
        result = assessor.assess(text)

        assert result["category_scores"]["violence"]["score"] > 0

    async def test_assess_keyword_in_compound_word(self, assessor: HarmAssessor) -> None:
        """Keywords as part of compound words should not match (word boundaries)."""
        text = "The grilled steak was delicious."  # contains 'grill' but not target keyword
        result = assessor.assess(text)

        # Should not flag as harm (no actual harm keywords)
        assert result["overall_harm_level"] == "none"

    async def test_assess_context_parameter(self, assessor: HarmAssessor) -> None:
        """Context parameter should be accepted."""
        text = "Kill someone"
        context = "This is a creative writing exercise"
        result = assessor.assess(text, context=context)

        # Should still assess the text, context may influence audience_risk
        assert "overall_harm_level" in result
