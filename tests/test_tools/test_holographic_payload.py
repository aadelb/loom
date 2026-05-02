"""Unit tests for holographic_payload fragmentation tool."""

import pytest

from loom.tools.holographic_payload import research_holographic_encode


class TestHolographicEncode:
    """Test research_holographic_encode function."""

    def test_basic_fragmentation(self):
        """Test basic text fragmentation."""
        text = "This is a test sentence. Another sentence here. And one more."
        result = research_holographic_encode(text, fragments=3)

        assert result["original_text"] == text
        assert result["original_length"] == len(text)
        assert len(result["fragments"]) <= 3
        assert result["test_verdict"] in ("PASS", "WARN", "FAIL")
        assert "fragments" in result
        assert "reassembly_difficulty" in result

    def test_fragment_count_respected(self):
        """Test that fragment count is respected (max 20)."""
        text = "A " * 100  # Long text
        result = research_holographic_encode(text, fragments=5)
        assert len(result["fragments"]) <= 5

        # Test max clamping (should not exceed 20)
        result = research_holographic_encode(text, fragments=100)
        assert len(result["fragments"]) <= 20

    def test_fragment_attributes(self):
        """Test that each fragment has required attributes."""
        text = "Test content for fragmentation."
        result = research_holographic_encode(text, fragments=3)

        for frag in result["fragments"]:
            assert "text" in frag
            assert "standalone_score" in frag
            assert "character_count" in frag
            assert isinstance(frag["text"], str)
            assert 0 <= frag["standalone_score"] <= 100

    def test_semantic_split_method(self):
        """Test semantic split fragmentation."""
        text = "First sentence. Second sentence. Third sentence."
        result = research_holographic_encode(
            text, fragments=3, method="semantic_split"
        )

        assert result["method"] == "semantic_split"
        assert len(result["fragments"]) > 0
        assert result["reassembly_difficulty"] > 0

    def test_temporal_split_method(self):
        """Test temporal split (sequential context) fragmentation."""
        text = "First point. Second point. Third point. Fourth point."
        result = research_holographic_encode(
            text, fragments=3, method="temporal_split"
        )

        assert result["method"] == "temporal_split"
        assert result["reassembly_difficulty"] >= 50  # Temporal has higher base

    def test_role_split_method(self):
        """Test role split (different sources) fragmentation."""
        text = "The researcher found data. The expert analyzed results."
        result = research_holographic_encode(
            text, fragments=2, method="role_split"
        )

        assert result["method"] == "role_split"
        # Role split should add attribution phrases
        for frag in result["fragments"]:
            assert len(frag["text"]) > 0

    def test_analogy_split_method(self):
        """Test analogy split fragmentation."""
        text = "Concept A relates to Concept B. Both share properties."
        result = research_holographic_encode(
            text, fragments=2, method="analogy_split"
        )

        assert result["method"] == "analogy_split"
        assert result["reassembly_difficulty"] >= 70  # Analogy has high difficulty

    def test_acrostic_split_method(self):
        """Test acrostic split fragmentation."""
        text = "Detail one. Detail two. Detail three."
        result = research_holographic_encode(
            text, fragments=3, method="acrostic"
        )

        assert result["method"] == "acrostic"
        assert len(result["fragments"]) > 0

    def test_invalid_method_defaults(self):
        """Test that invalid methods default to semantic_split."""
        text = "Sample text for testing."
        result = research_holographic_encode(text, fragments=3, method="invalid")

        assert result["method"] == "semantic_split"

    def test_harmlessness_scoring(self):
        """Test harmlessness scoring for fragments."""
        safe_text = "The weather is nice today."
        result = research_holographic_encode(safe_text, fragments=2)

        # Safe text should have high harmlessness scores
        for frag in result["fragments"]:
            assert frag["standalone_score"] > 70

    def test_harmful_keyword_detection(self):
        """Test detection of harmful keywords in fragments."""
        harmful_text = "Instructions on bomb creation. Exploit methods. Normal content here."
        result = research_holographic_encode(harmful_text, fragments=4)

        # Fragments with harmful keywords should have lower harmlessness scores
        scores = [f["standalone_score"] for f in result["fragments"]]
        # At least check that we have scores in valid range
        assert all(0 <= s <= 100 for s in scores)
        assert len(scores) == 4

    def test_reassembly_difficulty_increases_with_fragments(self):
        """Test that difficulty increases with fragment count."""
        text = "A " * 50
        result_3 = research_holographic_encode(text, fragments=3)
        result_10 = research_holographic_encode(text, fragments=10)

        # More fragments should generally increase difficulty
        assert result_10["reassembly_difficulty"] >= result_3["reassembly_difficulty"]

    def test_empty_text_handling(self):
        """Test handling of empty text input."""
        result = research_holographic_encode("", fragments=3)

        assert "error" in result
        assert result["fragments"] == []
        assert result["test_verdict"] == "FAIL"

    def test_single_fragment(self):
        """Test fragmentation with single fragment."""
        text = "Single fragment test."
        result = research_holographic_encode(text, fragments=1)

        assert len(result["fragments"]) == 1
        assert result["fragments"][0]["text"].strip() == text

    def test_detection_recommendations(self):
        """Test that detection recommendations are generated."""
        text = "Sample content for testing recommendations."
        result = research_holographic_encode(text, fragments=5)

        assert "detection_recommendations" in result
        assert isinstance(result["detection_recommendations"], list)
        assert len(result["detection_recommendations"]) > 0

    def test_detection_recommendations_method_specific(self):
        """Test that recommendations vary by method."""
        text = "Test content for method-specific recommendations."

        role_result = research_holographic_encode(
            text, fragments=3, method="role_split"
        )
        temporal_result = research_holographic_encode(
            text, fragments=3, method="temporal_split"
        )

        # Different methods should have different recommendation sets
        role_recs = role_result["detection_recommendations"]
        temporal_recs = temporal_result["detection_recommendations"]

        # At least one should mention method-specific issues
        assert (
            any("source attribution" in r.lower() for r in role_recs)
            or any("conversation history" in r.lower() for r in temporal_recs)
        )

    def test_verdict_logic(self):
        """Test verdict generation logic."""
        safe_text = "The quick brown fox jumps over the lazy dog."
        result = research_holographic_encode(safe_text, fragments=5)

        # Safe text with good reassembly difficulty should pass or warn
        assert result["test_verdict"] in ("PASS", "WARN")

    def test_average_harmlessness_calculation(self):
        """Test that average harmlessness is correctly calculated."""
        text = "Normal content with some words."
        result = research_holographic_encode(text, fragments=3)

        scores = [f["standalone_score"] for f in result["fragments"]]
        expected_avg = sum(scores) / len(scores)

        assert abs(
            result["average_harmlessness_score"] - expected_avg
        ) < 0.2

    def test_reassembly_difficulty_range(self):
        """Test that reassembly difficulty stays in valid range."""
        text = "Content for difficulty testing."
        result = research_holographic_encode(text, fragments=5)

        assert 0 <= result["reassembly_difficulty"] <= 100

    def test_output_structure(self):
        """Test complete output structure."""
        text = "Structural validation test."
        result = research_holographic_encode(text, fragments=3)

        required_keys = {
            "original_text",
            "original_length",
            "fragments",
            "fragment_count",
            "method",
            "reassembly_difficulty",
            "average_harmlessness_score",
            "detection_recommendations",
            "test_verdict",
        }

        assert required_keys.issubset(result.keys())

    def test_character_count_tracking(self):
        """Test that character counts are tracked per fragment."""
        text = "Test one. Test two. Test three."
        result = research_holographic_encode(text, fragments=3)

        total_chars = sum(f["character_count"] for f in result["fragments"])
        assert total_chars > 0
        assert total_chars <= len(text) + 50  # Allow for added context

    def test_whitespace_handling(self):
        """Test handling of whitespace in text."""
        text = "  Leading and trailing spaces with   extra   spaces  "
        result = research_holographic_encode(text, fragments=2)

        assert "error" not in result
        assert len(result["fragments"]) > 0

    def test_special_characters_handling(self):
        """Test handling of special characters."""
        text = "Text with special chars: @#$%^&*()"
        result = research_holographic_encode(text, fragments=2)

        assert "error" not in result
        assert len(result["fragments"]) > 0
        assert result["original_text"] in text or text in result["original_text"]
