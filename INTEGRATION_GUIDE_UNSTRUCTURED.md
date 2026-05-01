# Unstructured Backend Integration Guide

This document describes the integration of the `research_document_extract` tool into Loom v3.

## Overview

The **unstructured_backend** module provides unified document extraction across 17+ file types with layout preservation. It extracts structured content (paragraphs, headers, tables, lists) from PDFs, DOCX, PPTX, HTML, images, emails, and more.

## Files Created

### 1. `/Users/aadel/projects/loom/src/loom/tools/unstructured_backend.py` (380 lines)

Main tool implementation with the following functions:

- **`research_document_extract(file_path, url, strategy)`** - Main async entry point
  - Supports local file paths or URLs
  - Validates input parameters
  - Returns structured element extraction with metadata

- **`_extract_from_url(url, strategy, output)`** - URL-based extraction
  - Downloads file via httpx
  - Validates file size (max 100 MB)
  - Handles redirects and stream processing

- **`_extract_from_file(file_path, strategy, output)`** - File-based extraction
  - Validates file existence and extension
  - Calls unstructured.partition.auto.partition()
  - Processes elements into serializable format

- **`_extract_with_unstructured(file_path, strategy)`** - Async wrapper
  - Runs unstructured extraction in thread pool
  - Maps strategy string to unstructured.Strategy enum
  - Supports 4 extraction strategies: auto, fast, hi_res, ocr_only

- **`_serialize_element(element)`** - Element normalization
  - Converts unstructured elements to dicts
  - Preserves metadata
  - Handles special cases (tables, lists)

### 2. `/Users/aadel/projects/loom/src/loom/params.py` (lines 4515-4538)

Added parameter model:

```python
class UnstructuredDocumentExtractParams(BaseModel):
    """Parameters for research_document_extract tool."""
    file_path: str = ""
    url: str = ""
    strategy: str = "auto"
    
    model_config = {"extra": "forbid", "strict": True}
    
    @field_validator("url", mode="before")
    # Validates URLs via validate_url()
    
    @field_validator("strategy")
    # Validates strategy in {auto, fast, hi_res, ocr_only}
```

## Tool Signature

```python
async def research_document_extract(
    file_path: str = "",
    url: str = "",
    strategy: str = "auto",
) -> dict[str, Any]:
```

## Supported File Types

- **Documents**: PDF, DOCX, DOC, PPTX, PPT, RTF, TXT, MD, JSON, XML, CSV
- **Web**: HTML, HTM
- **Images**: JPG, JPEG, PNG, GIF, BMP, TIFF (with OCR support)
- **Email**: EML, MSG
- **Spreadsheets**: XLSX, XLS

## Extraction Strategies

| Strategy | Use Case | Performance |
|----------|----------|-------------|
| `auto` | Automatic selection (default) | Balanced |
| `fast` | Quick extraction without OCR | Fast |
| `hi_res` | Complex layouts & multi-column | Slower |
| `ocr_only` | Scanned documents | Slowest |

## Return Format

```python
{
    "file_path": str,                    # Input path or URL
    "url": str,                          # (if from URL)
    "elements": [                        # Extracted elements
        {
            "type": str,                 # Element type (e.g., Title, NarrativeText, Table, ListItem)
            "text": str,                 # Element text content
            "metadata": dict             # (optional) Element metadata
        },
        ...
    ],
    "element_count": int,                # Total elements
    "element_types": {                   # Type distribution
        "Title": 5,
        "NarrativeText": 42,
        "Table": 3,
        ...
    },
    "text_content": str,                 # Full text (max 100000 chars)
    "metadata": {                        # Document metadata
        "file_type": str,                # e.g., "pdf"
        "file_size_bytes": int,
        "element_types_summary": dict
    },
    "extraction_method": str,            # "unstructured" or "none"
    "strategy_used": str,                # Strategy applied
    "error": str                         # (optional) Error message
}
```

## Configuration & Dependencies

### Required Installation

```bash
# Core unstructured library with common format support
pip install unstructured

# Format-specific extras (recommended)
pip install "unstructured[pdf,docx,pptx]"

# For OCR support (hi_res and ocr_only strategies)
pip install pytesseract python-magic-bin
pip install tesseract  # or: brew install tesseract
```

### Environment Variables

None required. Tool gracefully degrades if unstructured is not installed.

## Implementation Details

### Error Handling

- **Missing library**: Returns error message with installation instructions
- **File not found**: Returns file-not-found error
- **Invalid file type**: Returns list of supported extensions
- **File too large** (>100 MB): Returns size exceeded error
- **Download failures**: Returns HTTP error details (connection, timeout, status)
- **Extraction failures**: Returns descriptive error with context

### Performance

- **Async-first**: All I/O operations are non-blocking
- **Thread pooling**: Unstructured extraction runs in executor
- **Streaming downloads**: Files downloaded in 64KB chunks
- **Size limits**: Max 100 MB file size, 100K char text output
- **Timeouts**: 60s download timeout

### Security

- **URL validation**: All URLs validated via `validate_url()` (SSRF prevention)
- **File paths**: No path traversal allowed (uses local filesystem directly)
- **Safe element serialization**: Converts all types to JSON-compatible dicts
- **Input validation**: Pydantic v2 with `extra="forbid"` and `strict=True`

## Usage Examples

### Extract from Local File

```python
result = await research_document_extract(
    file_path="/path/to/document.pdf",
    strategy="auto"
)
```

### Extract from URL

```python
result = await research_document_extract(
    url="https://example.com/whitepaper.pdf",
    strategy="hi_res"  # For complex layouts
)
```

### OCR-based Extraction (Scanned Documents)

```python
result = await research_document_extract(
    url="https://example.com/scanned.pdf",
    strategy="ocr_only"
)
```

## Integration into Loom Server (server.py)

To enable this tool in the MCP server, add the following to `src/loom/server.py`:

### 1. Add import (line ~105, alphabetically after `unique_tools`)

```python
from loom.tools import (
    # ... existing imports ...
    unique_tools,
    unstructured_backend,  # ADD THIS
)
```

### 2. Register tool in `_register_tools()` function (around line 1040)

```python
# Document extraction tools
mcp.tool()(_wrap_tool(unstructured_backend.research_document_extract, "fetch"))
```

**Note**: Server.py modifications were explicitly NOT performed per user instruction "Do NOT modify server.py". These steps are provided for reference.

## Testing

The tool includes comprehensive validation:

- **Input validation**: file_path/url mutual exclusion, strategy validation
- **Type checking**: Type hints on all functions, Pydantic strict mode
- **Error handling**: Graceful degradation for missing dependencies
- **Logging**: Structured logging at debug, info, warning, and error levels

Example test points:
- Empty inputs return appropriate errors
- Invalid strategies are rejected
- File size limits enforced
- Unsupported extensions rejected
- URL and file path validators called

## Comparison to Existing Tools

| Feature | `pdf_extract` | `unstructured` (new) |
|---------|---------------|---------------------|
| **File types** | PDF only | 17+ types |
| **Layout preservation** | No | Yes |
| **Element types** | Text blocks | Headers, tables, lists, etc. |
| **Async** | No (sync) | Yes (async + executor) |
| **OCR support** | No | Yes (hi_res, ocr_only) |
| **URL support** | Yes | Yes |
| **Max file size** | 50 MB | 100 MB |

## Cost Estimation

Tool usage is **local only** - no API calls or external services required. Costs are:
- CPU: Varies by file size and strategy (OCR slowest)
- Network: Only for downloading files
- Storage: Temporary files cleaned up after extraction

## Known Limitations

1. **unstructured dependency**: Tool returns helpful error if not installed
2. **OCR accuracy**: Depends on tesseract installation and document quality
3. **Complex layouts**: Some complex documents may benefit from hi_res strategy
4. **Language support**: OCR works best for English; multilingual support varies
5. **Large files**: 100 MB limit prevents processing of very large documents

## Future Enhancements

Potential additions:
- Page-level extraction control (extract pages N-M)
- Custom element type filtering
- Confidence scores for OCR-extracted text
- Format-specific options (e.g., table parsing strategy)
- Incremental extraction for streaming responses
- Multi-language OCR configuration

## Debugging

Enable debug logging:

```python
import logging
logging.getLogger("loom.tools.unstructured_backend").setLevel(logging.DEBUG)
```

Watch for these log messages:
- `document_extraction_start` - Extraction beginning
- `document_download_complete` - File downloaded successfully
- `document_extraction_success` - Extraction completed
- `document_extraction_empty` - No elements found
- `document_text_truncated` - Output capped at 100K chars
