"""Tests for loom.html_utils module."""

import pytest

from loom.html_utils import extract_links, extract_meta, extract_text, extract_title, strip_tags


class TestStripTags:
    """Test strip_tags function."""

    def test_removes_all_tags(self) -> None:
        """Strip all HTML tags."""
        html = "<div>Hello <b>world</b>!</div>"
        assert strip_tags(html) == "Hello world !"

    def test_removes_script_blocks(self) -> None:
        """Remove script and style blocks entirely."""
        html = "<p>Text</p><script>alert('hi')</script><p>More</p>"
        result = strip_tags(html)
        assert "alert" not in result
        assert "Text" in result

    def test_normalizes_whitespace(self) -> None:
        """Normalize multiple spaces/newlines."""
        html = "<p>Text  \n\n  with   spaces</p>"
        assert strip_tags(html) == "Text with spaces"

    def test_empty_html(self) -> None:
        """Handle empty HTML."""
        assert strip_tags("") == ""
        assert strip_tags("<div></div>") == ""


class TestExtractText:
    """Test extract_text function."""

    def test_extracts_text_without_tags(self) -> None:
        """Extract plain text from HTML."""
        html = "<p>Hello <em>world</em></p>"
        assert extract_text(html) == "Hello world"

    def test_respects_max_chars(self) -> None:
        """Truncate to max_chars."""
        html = "<p>This is a very long text</p>"
        assert extract_text(html, max_chars=7) == "This is"

    def test_zero_max_chars_disables_limit(self) -> None:
        """max_chars=0 means no limit."""
        html = "<p>Complete text</p>"
        assert extract_text(html, max_chars=0) == "Complete text"


class TestExtractLinks:
    """Test extract_links function."""

    def test_finds_href_attributes(self) -> None:
        """Extract all href values."""
        html = '<a href="page1.html">Link1</a><a href="/page2">Link2</a>'
        links = extract_links(html)
        assert links == ["page1.html", "/page2"]

    def test_resolves_relative_urls(self) -> None:
        """Resolve relative URLs with base_url."""
        html = '<a href="page.html">Link</a><a href="/about">About</a>'
        links = extract_links(html, base_url="https://example.com/dir/")
        assert links == [
            "https://example.com/dir/page.html",
            "https://example.com/about",
        ]

    def test_case_insensitive(self) -> None:
        """Match HREF in any case."""
        html = '<a HREF="page1.html">1</a><a HrEf="page2.html">2</a>'
        assert extract_links(html) == ["page1.html", "page2.html"]

    def test_both_single_and_double_quotes(self) -> None:
        """Handle both single and double quotes."""
        html = '''<a href="double.html">1</a><a href='single.html'>2</a>'''
        assert extract_links(html) == ["double.html", "single.html"]


class TestExtractMeta:
    """Test extract_meta function."""

    def test_extracts_name_attributes(self) -> None:
        """Extract meta name attributes."""
        html = '<meta name="description" content="A test page">'
        meta = extract_meta(html)
        assert meta["description"] == "A test page"

    def test_extracts_property_attributes(self) -> None:
        """Extract meta property attributes (OpenGraph)."""
        html = '<meta property="og:title" content="Test Page">'
        meta = extract_meta(html)
        assert meta["og:title"] == "Test Page"

    def test_case_insensitive(self) -> None:
        """Meta names are lowercased."""
        html = '<meta name="AUTHOR" content="John Doe">'
        meta = extract_meta(html)
        assert "author" in meta
        assert meta["author"] == "John Doe"

    def test_multiple_metas(self) -> None:
        """Extract multiple meta tags."""
        html = '''
        <meta name="description" content="Desc">
        <meta property="og:title" content="Title">
        <meta name="author" content="Jane">
        '''
        meta = extract_meta(html)
        assert len(meta) == 3
        assert meta["description"] == "Desc"
        assert meta["og:title"] == "Title"
        assert meta["author"] == "Jane"

    def test_empty_content(self) -> None:
        """Handle meta tags with empty content."""
        html = '<meta name="test" content="">'
        meta = extract_meta(html)
        assert meta["test"] == ""


class TestExtractTitle:
    """Test extract_title function."""

    def test_extracts_title_content(self) -> None:
        """Extract text from <title> tag."""
        html = "<html><head><title>My Page Title</title></head></html>"
        assert extract_title(html) == "My Page Title"

    def test_removes_tags_from_title(self) -> None:
        """Remove any tags inside title."""
        html = "<title>Page <em>Title</em></title>"
        assert extract_title(html) == "Page Title"

    def test_normalizes_whitespace_in_title(self) -> None:
        """Normalize whitespace inside title."""
        html = "<title>  Multiple   spaces  </title>"
        assert extract_title(html) == "Multiple spaces"

    def test_missing_title_returns_empty(self) -> None:
        """Return empty string if no title."""
        assert extract_title("<html><head></head></html>") == ""
        assert extract_title("no title here") == ""

    def test_case_insensitive_tag(self) -> None:
        """Match title tag in any case."""
        html = "<TITLE>Case Insensitive</TITLE>"
        assert extract_title(html) == "Case Insensitive"
