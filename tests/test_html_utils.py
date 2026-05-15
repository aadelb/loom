"""Unit tests for shared html_utils module.

Tests cover tag stripping, text extraction, link extraction, meta extraction,
and title extraction with comprehensive coverage of edge cases including
malformed HTML, empty HTML, XSS payloads, and unicode content.
"""

from __future__ import annotations

import pytest

from loom.html_utils import (
    strip_tags,
    extract_text,
    extract_links,
    extract_meta,
    extract_title,
)


class TestStripTags:
    """Tests for strip_tags() function — 11 test cases."""

    def test_strip_tags_simple(self) -> None:
        """Remove simple HTML tags."""
        html = "<p>hello world</p>"
        result = strip_tags(html)
        assert result == "hello world"

    def test_strip_tags_nested(self) -> None:
        """Remove nested HTML tags."""
        html = "<div><p>hello <b>world</b></p></div>"
        result = strip_tags(html)
        assert "hello" in result
        assert "world" in result
        assert "<" not in result

    def test_strip_tags_script_removal(self) -> None:
        """Remove script tags and content."""
        html = "<p>hello</p><script>alert('xss')</script><p>world</p>"
        result = strip_tags(html)
        assert "alert" not in result
        assert "hello" in result
        assert "world" in result

    def test_strip_tags_style_removal(self) -> None:
        """Remove style tags and content."""
        html = "<p>hello</p><style>body { color: red; }</style><p>world</p>"
        result = strip_tags(html)
        assert "color: red" not in result
        assert "hello" in result
        assert "world" in result

    def test_strip_tags_multiple_spaces(self) -> None:
        """Condense multiple spaces in output."""
        html = "<p>hello</p>   <p>world</p>"
        result = strip_tags(html)
        # Should have single space between words
        assert "  " not in result

    def test_strip_tags_empty_html(self) -> None:
        """Handle empty HTML."""
        result = strip_tags("")
        assert result == ""

    def test_strip_tags_only_tags(self) -> None:
        """Handle HTML with only tags, no content."""
        html = "<div><p></p><span></span></div>"
        result = strip_tags(html)
        assert result == ""

    def test_strip_tags_attributes(self) -> None:
        """Remove tag attributes."""
        html = '<p class="intro" id="main">hello world</p>'
        result = strip_tags(html)
        assert "class" not in result
        assert "intro" not in result
        assert "hello world" in result

    def test_strip_tags_malformed(self) -> None:
        """Handle malformed HTML."""
        html = "<p>hello <b>world</p></b>"
        result = strip_tags(html)
        assert "hello" in result
        assert "world" in result

    def test_strip_tags_unicode(self) -> None:
        """Preserve unicode content."""
        html = "<p>café résumé naïve</p>"
        result = strip_tags(html)
        assert "café" in result
        assert "résumé" in result

    def test_strip_tags_multiline(self) -> None:
        """Handle multiline HTML."""
        html = """<div>
            <p>line1</p>
            <p>line2</p>
        </div>"""
        result = strip_tags(html)
        assert "line1" in result
        assert "line2" in result


class TestExtractText:
    """Tests for extract_text() function — 9 test cases."""

    def test_extract_text_simple(self) -> None:
        """Extract text from simple HTML."""
        html = "<p>hello world</p>"
        result = extract_text(html)
        assert result == "hello world"

    def test_extract_text_with_max_chars(self) -> None:
        """Respect max_chars parameter."""
        html = "<p>hello world this is a long text</p>"
        result = extract_text(html, max_chars=10)
        assert len(result) == 10

    def test_extract_text_no_max_chars(self) -> None:
        """Return all text when max_chars=0."""
        html = "<p>hello world</p>"
        result = extract_text(html, max_chars=0)
        assert result == "hello world"

    def test_extract_text_removes_scripts(self) -> None:
        """Remove script content."""
        html = "<p>hello</p><script>alert('xss')</script><p>world</p>"
        result = extract_text(html)
        assert "alert" not in result
        assert "hello" in result

    def test_extract_text_empty_html(self) -> None:
        """Handle empty HTML."""
        result = extract_text("")
        assert result == ""

    def test_extract_text_max_chars_exceeds_length(self) -> None:
        """Handle max_chars larger than text length."""
        html = "<p>hello</p>"
        result = extract_text(html, max_chars=100)
        assert result == "hello"

    def test_extract_text_unicode(self) -> None:
        """Extract unicode text."""
        html = "<p>café résumé</p>"
        result = extract_text(html)
        assert "café" in result
        assert "résumé" in result

    def test_extract_text_max_chars_splits_word(self) -> None:
        """max_chars may split in middle of word."""
        html = "<p>hello</p>"
        result = extract_text(html, max_chars=3)
        assert len(result) == 3
        assert result == "hel"

    def test_extract_text_complex_html(self) -> None:
        """Extract from complex HTML structure."""
        html = """
        <html>
            <body>
                <div class="content">
                    <h1>Title</h1>
                    <p>paragraph 1</p>
                    <p>paragraph 2</p>
                </div>
            </body>
        </html>
        """
        result = extract_text(html)
        assert "Title" in result
        assert "paragraph 1" in result
        assert "paragraph 2" in result


class TestExtractLinks:
    """Tests for extract_links() function — 11 test cases."""

    def test_extract_links_simple(self) -> None:
        """Extract simple links."""
        html = '<a href="https://example.com">link</a>'
        links = extract_links(html)
        assert "https://example.com" in links

    def test_extract_links_multiple(self) -> None:
        """Extract multiple links."""
        html = '''
        <a href="https://example.com">link1</a>
        <a href="https://example.org">link2</a>
        '''
        links = extract_links(html)
        assert len(links) == 2
        assert "https://example.com" in links
        assert "https://example.org" in links

    def test_extract_links_single_quotes(self) -> None:
        """Extract links with single quotes."""
        html = "<a href='https://example.com'>link</a>"
        links = extract_links(html)
        assert "https://example.com" in links

    def test_extract_links_relative_urls(self) -> None:
        """Convert relative URLs with base_url."""
        html = '<a href="/page">link</a>'
        links = extract_links(html, base_url="https://example.com")
        assert "https://example.com/page" in links

    def test_extract_links_no_base_url(self) -> None:
        """Return relative URLs as-is without base_url."""
        html = '<a href="/page">link</a>'
        links = extract_links(html)
        assert "/page" in links

    def test_extract_links_empty_html(self) -> None:
        """Handle HTML with no links."""
        html = "<p>no links here</p>"
        links = extract_links(html)
        assert links == []

    def test_extract_links_malformed_href(self) -> None:
        """Skip malformed href attributes."""
        html = '<a href>no url</a><a href="https://valid.com">valid</a>'
        links = extract_links(html)
        assert "https://valid.com" in links

    def test_extract_links_fragment_urls(self) -> None:
        """Resolve fragment URLs."""
        html = '<a href="#section">anchor</a>'
        links = extract_links(html, base_url="https://example.com/page")
        assert "https://example.com/page#section" in links

    def test_extract_links_query_string(self) -> None:
        """Preserve query strings."""
        html = '<a href="https://example.com?param=value">link</a>'
        links = extract_links(html)
        assert "https://example.com?param=value" in links

    def test_extract_links_unicode_url(self) -> None:
        """Handle unicode in URLs."""
        html = '<a href="https://example.com/café">link</a>'
        links = extract_links(html)
        assert "https://example.com/café" in links

    def test_extract_links_duplicate_urls(self) -> None:
        """Return all links including duplicates."""
        html = '''
        <a href="https://example.com">link1</a>
        <a href="https://example.com">link2</a>
        '''
        links = extract_links(html)
        assert len(links) == 2


class TestExtractMeta:
    """Tests for extract_meta() function — 10 test cases."""

    def test_extract_meta_simple(self) -> None:
        """Extract simple meta tags."""
        html = '<meta name="description" content="Page description">'
        meta = extract_meta(html)
        assert meta["description"] == "Page description"

    def test_extract_meta_property(self) -> None:
        """Extract meta tags with property attribute."""
        html = '<meta property="og:title" content="Page Title">'
        meta = extract_meta(html)
        assert meta["og:title"] == "Page Title"

    def test_extract_meta_multiple(self) -> None:
        """Extract multiple meta tags."""
        html = '''
        <meta name="description" content="Description">
        <meta name="keywords" content="key1, key2">
        <meta property="og:url" content="https://example.com">
        '''
        meta = extract_meta(html)
        assert len(meta) == 3
        assert meta["description"] == "Description"
        assert meta["keywords"] == "key1, key2"
        assert meta["og:url"] == "https://example.com"

    def test_extract_meta_case_insensitive(self) -> None:
        """Meta tag names are lowercased."""
        html = '<meta name="Description" content="Test">'
        meta = extract_meta(html)
        assert "description" in meta
        assert meta["description"] == "Test"

    def test_extract_meta_empty_html(self) -> None:
        """Handle HTML with no meta tags."""
        html = "<p>no meta tags</p>"
        meta = extract_meta(html)
        assert meta == {}

    def test_extract_meta_empty_content(self) -> None:
        """Extract meta tags with empty content."""
        html = '<meta name="test" content="">'
        meta = extract_meta(html)
        assert meta["test"] == ""

    def test_extract_meta_malformed(self) -> None:
        """Skip malformed meta tags."""
        html = '''
        <meta name="valid" content="content">
        <meta name="invalid">
        <meta content="no-name" name="">
        '''
        meta = extract_meta(html)
        assert "valid" in meta

    def test_extract_meta_special_chars(self) -> None:
        """Handle special characters in content."""
        html = '<meta name="keywords" content="test, &amp; special &lt;chars&gt;">'
        meta = extract_meta(html)
        assert "keywords" in meta

    def test_extract_meta_duplicate_names(self) -> None:
        """Last meta tag with same name wins."""
        html = '''
        <meta name="description" content="first">
        <meta name="description" content="second">
        '''
        meta = extract_meta(html)
        assert meta["description"] == "second"

    def test_extract_meta_unicode(self) -> None:
        """Preserve unicode in meta content."""
        html = '<meta name="description" content="Café résumé naïve">'
        meta = extract_meta(html)
        assert "café" in meta["description"].lower()


class TestExtractTitle:
    """Tests for extract_title() function — 10 test cases."""

    def test_extract_title_simple(self) -> None:
        """Extract simple title."""
        html = "<title>Page Title</title>"
        result = extract_title(html)
        assert result == "Page Title"

    def test_extract_title_with_tags(self) -> None:
        """Extract title ignoring tags inside."""
        html = "<title>Page <em>Title</em></title>"
        result = extract_title(html)
        assert "Page" in result
        assert "Title" in result
        assert "<" not in result

    def test_extract_title_missing(self) -> None:
        """Return empty string if no title tag."""
        html = "<p>no title</p>"
        result = extract_title(html)
        assert result == ""

    def test_extract_title_case_insensitive(self) -> None:
        """Match title tag case-insensitively."""
        html = "<TITLE>Page Title</TITLE>"
        result = extract_title(html)
        assert result == "Page Title"

    def test_extract_title_with_attributes(self) -> None:
        """Extract title ignoring tag attributes."""
        html = '<title class="main" id="title">Page Title</title>'
        result = extract_title(html)
        assert result == "Page Title"

    def test_extract_title_with_whitespace(self) -> None:
        """Strip whitespace from title."""
        html = "<title>  Page Title  </title>"
        result = extract_title(html)
        assert result == "Page Title"

    def test_extract_title_multiline(self) -> None:
        """Extract multiline title."""
        html = """<title>
            Page
            Title
        </title>"""
        result = extract_title(html)
        assert "Page" in result
        assert "Title" in result

    def test_extract_title_empty(self) -> None:
        """Handle empty title tag."""
        html = "<title></title>"
        result = extract_title(html)
        assert result == ""

    def test_extract_title_unicode(self) -> None:
        """Preserve unicode in title."""
        html = "<title>Café Résumé Naïve</title>"
        result = extract_title(html)
        assert "Café" in result
        assert "Résumé" in result

    def test_extract_title_with_entities(self) -> None:
        """Extract title with HTML entities."""
        html = "<title>Page &amp; Title &lt;Test&gt;</title>"
        result = extract_title(html)
        assert "Page" in result
        assert "Title" in result


class TestHTMLEdgeCases:
    """Integration tests for edge cases across HTML utils — 5 test cases."""

    def test_xss_payload_stripped(self) -> None:
        """Strip XSS payloads from HTML."""
        html = '<img src=x onerror="alert(\'xss\')">'
        result = strip_tags(html)
        assert "alert" not in result
        assert "onerror" not in result

    def test_deeply_nested_html(self) -> None:
        """Handle deeply nested HTML."""
        html = "<div>" * 100 + "content" + "</div>" * 100
        result = extract_text(html)
        assert "content" in result

    def test_html_with_comments(self) -> None:
        """Handle HTML comments."""
        html = "<!-- comment --><p>content</p><!-- another comment -->"
        result = extract_text(html)
        assert "comment" not in result
        assert "content" in result

    def test_mixed_content_extraction(self) -> None:
        """Extract from mixed content (text, links, meta, title)."""
        html = """
        <html>
            <head>
                <title>Test Page</title>
                <meta name="description" content="Test Description">
            </head>
            <body>
                <p>Main content here</p>
                <a href="https://example.com">Link</a>
            </body>
        </html>
        """
        title = extract_title(html)
        meta = extract_meta(html)
        text = extract_text(html)
        links = extract_links(html)
        
        assert title == "Test Page"
        assert meta["description"] == "Test Description"
        assert "Main content" in text
        assert "https://example.com" in links

    def test_html_entities_preserved(self) -> None:
        """Preserve HTML entities in extracted text."""
        html = "<p>&copy; 2024 &amp; Company</p>"
        result = extract_text(html)
        assert "&copy;" in result or "©" in result
