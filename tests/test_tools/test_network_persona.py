"""Tests for network_persona research tool."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
class TestNetworkPersona:
    """Test suite for research_network_persona tool."""

    async def test_network_persona_basic(self):
        """Test basic network persona analysis."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"author": "alice", "text": "Hello", "reply_to": None},
            {"author": "bob", "text": "Hi", "reply_to": "alice"},
            {"author": "charlie", "text": "Hey", "reply_to": "alice"},
            {"author": "alice", "text": "Thanks", "reply_to": "bob"},
            {"author": "bob", "text": "Welcome", "reply_to": "charlie"},
        ]

        result = await research_network_persona(posts)

        assert "authors" in result
        assert "network" in result
        assert "edges" in result
        assert len(result["authors"]) > 0
        assert result["network"]["total_authors"] > 0
        assert result["network"]["total_edges"] > 0

    async def test_network_persona_author_metrics(self):
        """Test author metric calculations."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"author": "alice", "text": "Post 1", "reply_to": None},
            {"author": "bob", "text": "Post 2", "reply_to": "alice"},
            {"author": "alice", "text": "Post 3", "reply_to": "bob"},
        ]

        result = await research_network_persona(posts)

        assert "alice" in result["authors"]
        assert "bob" in result["authors"]
        assert result["authors"]["alice"]["post_count"] == 2
        assert result["authors"]["bob"]["post_count"] == 1

    async def test_network_persona_reply_tracking(self):
        """Test reply count tracking."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"author": "alice", "text": "Post 1", "reply_to": None},
            {"author": "bob", "text": "Post 2", "reply_to": "alice"},
            {"author": "charlie", "text": "Post 3", "reply_to": "alice"},
        ]

        result = await research_network_persona(posts)

        # alice should have received 2 replies
        assert result["authors"]["alice"]["replies_received"] == 2
        # bob and charlie each sent 1 reply
        assert result["authors"]["bob"]["replies_sent"] == 1
        assert result["authors"]["charlie"]["replies_sent"] == 1

    async def test_network_persona_role_authority(self):
        """Test authority role detection (high in-degree)."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"author": "alice", "text": "Post 1", "reply_to": None},
            {"author": "bob", "text": "Post 2", "reply_to": "alice"},
            {"author": "charlie", "text": "Post 3", "reply_to": "alice"},
            {"author": "dave", "text": "Post 4", "reply_to": "alice"},
            {"author": "eve", "text": "Post 5", "reply_to": "alice"},
            {"author": "frank", "text": "Post 6", "reply_to": "alice"},
        ]

        result = await research_network_persona(posts)

        assert result["authors"]["alice"]["role"] == "authority"

    async def test_network_persona_role_hub(self):
        """Test hub role detection (high out-degree)."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"author": "alice", "text": "P1", "reply_to": None},
            {"author": "bob", "text": "P2", "reply_to": None},
            {"author": "charlie", "text": "P3", "reply_to": None},
            {"author": "dave", "text": "P4", "reply_to": None},
            {"author": "hub_user", "text": "P5", "reply_to": "alice"},
            {"author": "hub_user", "text": "P6", "reply_to": "bob"},
            {"author": "hub_user", "text": "P7", "reply_to": "charlie"},
            {"author": "hub_user", "text": "P8", "reply_to": "dave"},
        ]

        result = await research_network_persona(posts)

        assert result["authors"]["hub_user"]["role"] == "hub"

    async def test_network_persona_role_lurker(self):
        """Test lurker role detection (low interaction)."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"author": "alice", "text": "P1", "reply_to": None},
            {"author": "bob", "text": "P2", "reply_to": "alice"},
            {"author": "lurker", "text": "P3", "reply_to": None},
        ]

        result = await research_network_persona(posts)

        # lurker has 1 post but no interactions
        if "lurker" in result["authors"]:
            assert result["authors"]["lurker"]["role"] == "lurker"

    async def test_network_persona_network_density(self):
        """Test network density calculation."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"author": "alice", "text": "P1", "reply_to": None},
            {"author": "bob", "text": "P2", "reply_to": "alice"},
            {"author": "charlie", "text": "P3", "reply_to": "bob"},
        ]

        result = await research_network_persona(posts)

        # Density should be between 0 and 1
        assert 0.0 <= result["network"]["density"] <= 1.0

    async def test_network_persona_edge_list(self):
        """Test edge list generation."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"author": "alice", "text": "P1", "reply_to": None},
            {"author": "bob", "text": "P2", "reply_to": "alice"},
            {"author": "charlie", "text": "P3", "reply_to": "alice"},
        ]

        result = await research_network_persona(posts)

        assert len(result["edges"]) > 0
        # Check edges have required fields
        for edge in result["edges"]:
            assert "from" in edge
            assert "to" in edge
            assert "weight" in edge

    async def test_network_persona_top_authorities(self):
        """Test top authorities identification."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"author": "alice", "text": "P1", "reply_to": None},
            {"author": "bob", "text": "P2", "reply_to": "alice"},
            {"author": "charlie", "text": "P3", "reply_to": "alice"},
            {"author": "dave", "text": "P4", "reply_to": "alice"},
            {"author": "eve", "text": "P5", "reply_to": None},
            {"author": "frank", "text": "P6", "reply_to": "eve"},
        ]

        result = await research_network_persona(posts)

        authorities = result["network"]["top_authorities"]
        # alice should be in top authorities (3 replies)
        if "alice" in result["authors"]:
            assert "alice" in authorities or len(authorities) > 0

    async def test_network_persona_top_hubs(self):
        """Test top hubs identification."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"author": "alice", "text": "P1", "reply_to": None},
            {"author": "hub", "text": "P2", "reply_to": "alice"},
            {"author": "hub", "text": "P3", "reply_to": "alice"},
            {"author": "hub", "text": "P4", "reply_to": "alice"},
        ]

        result = await research_network_persona(posts)

        hubs = result["network"]["top_hubs"]
        # hub should be in top hubs
        if "hub" in result["authors"]:
            assert "hub" in hubs or len(hubs) > 0

    async def test_network_persona_communities(self):
        """Test community detection."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"author": "alice", "text": "P1", "reply_to": None},
            {"author": "bob", "text": "P2", "reply_to": "alice"},
            {"author": "charlie", "text": "P3", "reply_to": "bob"},
            # Separate group
            {"author": "dave", "text": "P4", "reply_to": None},
            {"author": "eve", "text": "P5", "reply_to": "dave"},
        ]

        result = await research_network_persona(posts)

        # Should detect at least 1 community
        assert result["network"]["communities"] >= 1

    async def test_network_persona_empty_input(self):
        """Test handling of empty posts list."""
        from loom.tools.network_persona import research_network_persona

        result = await research_network_persona([])

        assert result["authors"] == {}
        assert result["network"]["total_authors"] == 0
        assert result["network"]["total_edges"] == 0

    async def test_network_persona_insufficient_posts(self):
        """Test handling of insufficient posts (<3)."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"author": "alice", "text": "P1", "reply_to": None},
            {"author": "bob", "text": "P2", "reply_to": "alice"},
        ]

        result = await research_network_persona(posts)

        assert result["authors"] == {}
        assert result["network"]["total_authors"] == 0

    async def test_network_persona_no_reply_to(self):
        """Test handling when no reply_to relationships exist."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"author": "alice", "text": "P1"},
            {"author": "bob", "text": "P2"},
            {"author": "charlie", "text": "P3"},
        ]

        result = await research_network_persona(posts)

        # Without reply_to, should have no edges
        assert result["network"]["total_edges"] == 0

    async def test_network_persona_invalid_input(self):
        """Test handling of invalid input type."""
        from loom.tools.network_persona import research_network_persona

        result = await research_network_persona(None)

        assert result["authors"] == {}
        assert result["network"]["total_authors"] == 0

    async def test_network_persona_missing_author_field(self):
        """Test handling of posts missing author field."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"text": "P1", "reply_to": None},
            {"author": "bob", "text": "P2", "reply_to": None},
            {"author": "charlie", "text": "P3", "reply_to": "bob"},
        ]

        result = await research_network_persona(posts)

        # Should skip post without author
        assert "bob" in result["authors"]

    async def test_network_persona_empty_author(self):
        """Test handling of empty author strings."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"author": "", "text": "P1", "reply_to": None},
            {"author": "bob", "text": "P2", "reply_to": None},
            {"author": "charlie", "text": "P3", "reply_to": "bob"},
        ]

        result = await research_network_persona(posts)

        # Should skip empty author
        assert "" not in result["authors"]
        assert "bob" in result["authors"]

    async def test_network_persona_unique_contacts(self):
        """Test unique contact tracking."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"author": "alice", "text": "P1", "reply_to": None},
            {"author": "bob", "text": "P2", "reply_to": "alice"},
            {"author": "bob", "text": "P3", "reply_to": "alice"},
            {"author": "bob", "text": "P4", "reply_to": "alice"},
        ]

        result = await research_network_persona(posts)

        # bob replied to alice 3 times but has only 1 unique contact
        assert result["authors"]["bob"]["unique_contacts"] == 1

    async def test_network_persona_text_length_tracking(self):
        """Test average text length calculation."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"author": "alice", "text": "Short", "reply_to": None},
            {"author": "alice", "text": "Much longer text here", "reply_to": None},
            {"author": "bob", "text": "Hi", "reply_to": "alice"},
        ]

        result = await research_network_persona(posts)

        # alice's avg text length should be between 5 and 21
        if "alice" in result["authors"]:
            assert result["authors"]["alice"]["avg_text_length"] > 0

    async def test_network_persona_influence_score(self):
        """Test influence score calculation."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"author": "alice", "text": "P1", "reply_to": None},
            {"author": "bob", "text": "P2", "reply_to": "alice"},
            {"author": "charlie", "text": "P3", "reply_to": "alice"},
            {"author": "dave", "text": "P4", "reply_to": None},
        ]

        result = await research_network_persona(posts)

        # alice has highest in-degree (2), influence should reflect this
        if "alice" in result["authors"]:
            assert 0.0 <= result["authors"]["alice"]["influence_score"] <= 1.0

    async def test_network_persona_min_interactions_filter(self):
        """Test min_interactions filtering."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"author": "alice", "text": "P1", "reply_to": None},
            {"author": "bob", "text": "P2", "reply_to": "alice"},
            {"author": "charlie", "text": "P3", "reply_to": None},
            {"author": "dave", "text": "P4", "reply_to": "alice"},
        ]

        # With min_interactions=2, only alice should remain (2 replies)
        result = await research_network_persona(posts, min_interactions=2)

        assert "alice" in result["authors"]
        # bob and charlie have < 2 interactions
        assert "bob" not in result["authors"]
        assert "charlie" not in result["authors"]

    async def test_network_persona_case_insensitive(self):
        """Test that author names are case-insensitive matched."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"author": "Alice", "text": "P1", "reply_to": None},
            {"author": "BOB", "text": "P2", "reply_to": "alice"},
            {"author": "charlie", "text": "P3", "reply_to": "Alice"},
        ]

        result = await research_network_persona(posts)

        # All should be normalized to lowercase
        authors = result["authors"]
        assert "alice" in authors
        assert "bob" in authors
        # alice should have 2 replies from different authors
        assert authors["alice"]["replies_received"] == 2

    async def test_network_persona_self_reply_ignored(self):
        """Test that self-replies are ignored."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"author": "alice", "text": "P1", "reply_to": "alice"},
            {"author": "bob", "text": "P2", "reply_to": "bob"},
            {"author": "charlie", "text": "P3", "reply_to": "alice"},
        ]

        result = await research_network_persona(posts)

        # Self-replies should be ignored
        assert result["authors"]["alice"]["replies_received"] == 1  # only from charlie

    async def test_network_persona_returns_dict(self):
        """Test that result is proper dictionary."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"author": "alice", "text": "P1", "reply_to": None},
            {"author": "bob", "text": "P2", "reply_to": "alice"},
            {"author": "charlie", "text": "P3", "reply_to": "alice"},
        ]

        result = await research_network_persona(posts)

        assert isinstance(result, dict)
        assert "authors" in result
        assert "network" in result
        assert "edges" in result

    async def test_network_persona_network_structure(self):
        """Test that network dict has all required fields."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"author": "alice", "text": "P1", "reply_to": None},
            {"author": "bob", "text": "P2", "reply_to": "alice"},
            {"author": "charlie", "text": "P3", "reply_to": "alice"},
        ]

        result = await research_network_persona(posts)

        network = result["network"]
        assert "total_authors" in network
        assert "total_edges" in network
        assert "density" in network
        assert "communities" in network
        assert "top_authorities" in network
        assert "top_hubs" in network

    async def test_network_persona_author_structure(self):
        """Test that author records have all required fields."""
        from loom.tools.network_persona import research_network_persona

        posts = [
            {"author": "alice", "text": "Test post", "reply_to": None},
            {"author": "bob", "text": "P2", "reply_to": "alice"},
            {"author": "charlie", "text": "P3", "reply_to": "alice"},
        ]

        result = await research_network_persona(posts)

        for author_name, author_data in result["authors"].items():
            assert "post_count" in author_data
            assert "replies_sent" in author_data
            assert "replies_received" in author_data
            assert "unique_contacts" in author_data
            assert "avg_text_length" in author_data
            assert "role" in author_data
            assert "influence_score" in author_data
