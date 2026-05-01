# Server.py Modification Reference

This document shows the **exact changes needed** to integrate the unstructured_backend tool into the MCP server.

**Note**: Per user instruction, these modifications have NOT been applied. Use this as a reference if you choose to enable the tool.

## Change 1: Add Import (Line 105)

### Location
File: `src/loom/server.py`, line 105 (in the `from loom.tools import (...)` block)

### Current Code (lines 104-106)
```python
    pdf_extract,
    projectdiscovery,
    prompt_analyzer,
```

### Updated Code
```python
    pdf_extract,
    projectdiscovery,
    prompt_analyzer,
    prompt_reframe,
    psycholinguistic,
    realtime_monitor,
    report_generator,
    rss_monitor,
    salary_synthesizer,
    search,
    security_headers,
    sherlock_backend,
    signal_detection,
    social_graph,
    social_intel,
    social_scraper,
    spider,
    stealth,
    stego_detect,
    stylometry,
    supply_chain_intel,
    synth_echo,
    threat_intel,
    threat_profile,
    trend_predictor,
    unique_tools,
    unstructured_backend,  # ← ADD THIS LINE
)
```

### Exact Change
After line 129 (`unique_tools,`), add:
```python
    unstructured_backend,
```

---

## Change 2: Register Tool (Around Line 1040)

### Location
File: `src/loom/server.py`, in `_register_tools(mcp)` function, near other document extraction tools

### Current Code (lines 1036-1037)
```python
    mcp.tool()(_wrap_tool(pdf_extract.research_pdf_extract, "fetch"))
    mcp.tool()(_wrap_tool(pdf_extract.research_pdf_search, "fetch"))
```

### Add After
```python
    mcp.tool()(_wrap_tool(pdf_extract.research_pdf_extract, "fetch"))
    mcp.tool()(_wrap_tool(pdf_extract.research_pdf_search, "fetch"))
    mcp.tool()(_wrap_tool(unstructured_backend.research_document_extract, "fetch"))  # ← ADD THIS
```

---

## Verification Steps

After applying these changes:

### 1. Verify Imports
```bash
python3 -c "from loom.tools import unstructured_backend; print(unstructured_backend.research_document_extract)"
```

Expected output:
```
<function research_document_extract at 0x...>
```

### 2. Verify Syntax
```bash
python3 -m py_compile src/loom/server.py
echo "✓ Server syntax valid"
```

### 3. Test Tool Is Registered
```bash
cd /Users/aadel/projects/loom
python3 -c "
from loom.server import create_app
app = create_app()
tools = {t.name: t for t in app._tools}
if 'research_document_extract' in tools:
    print('✓ Tool registered successfully')
else:
    print('✗ Tool NOT registered')
    print('Available tools:', list(tools.keys())[:10], '...')
"
```

### 4. Run Server
```bash
loom serve
# Look for: "research_document_extract" in the tool list
```

---

## Diff View

If you have the changes handy, here's what the diff would look like:

```diff
--- a/src/loom/server.py
+++ b/src/loom/server.py
@@ -126,6 +126,7 @@ from loom.tools import (
     trend_predictor,
     unique_tools,
+    unstructured_backend,
 )
 from loom.tracing import install_tracing, new_request_id
 
@@ -1034,6 +1035,8 @@ def _register_tools(mcp: FastMCP) -> None:
     # Document extraction tools
     mcp.tool()(_wrap_tool(pdf_extract.research_pdf_extract, "fetch"))
     mcp.tool()(_wrap_tool(pdf_extract.research_pdf_search, "fetch"))
+    # Unified document extraction with layout preservation
+    mcp.tool()(_wrap_tool(unstructured_backend.research_document_extract, "fetch"))
 
     # RSS tools
```

---

## Alternative: Grep Locations

If you want to find the exact locations yourself:

### Find import location
```bash
grep -n "pdf_extract," /Users/aadel/projects/loom/src/loom/server.py
# Output: 104:    pdf_extract,

grep -n "unique_tools," /Users/aadel/projects/loom/src/loom/server.py
# Output: 129:    unique_tools,
```

### Find registration location
```bash
grep -n "research_pdf_extract" /Users/aadel/projects/loom/src/loom/server.py
# Output: 1036:    mcp.tool()(_wrap_tool(pdf_extract.research_pdf_extract, "fetch"))
```

---

## Why These Changes Are Needed

1. **Import**: Makes the module available in the server.py namespace
2. **Registration**: Exposes the tool to the MCP server as an available tool

Without these changes:
- The tool module exists and is syntactically correct
- But it's not registered with the FastMCP server
- Clients won't see it in the tool list
- Calling it will result in "tool not found" error

---

## Testing After Integration

```bash
# Test via CLI
loom research_document_extract --help

# Test via Python
python3 << 'EOF'
import asyncio
from loom.tools.unstructured_backend import research_document_extract

result = asyncio.run(research_document_extract(
    file_path="test.pdf",
    strategy="fast"
))
print(result)
EOF
```

---

## Rollback Instructions

If you need to undo these changes:

```bash
cd /Users/aadel/projects/loom

# Revert the changes
git checkout src/loom/server.py

# Verify
grep -n "unstructured_backend" src/loom/server.py
# Should return: (no results)
```

Or manually:
1. Delete the import line `unstructured_backend,`
2. Delete the registration line `mcp.tool()(_wrap_tool(unstructured_backend.research_document_extract, "fetch"))`

---

## Notes

- Tool category is `"fetch"` (same as PDF extraction, spider, fetch, etc.)
- Tool name is `research_document_extract` (follows Loom naming convention)
- No optional dependencies or imports needed in server.py
- Tool gracefully handles missing unstructured library at runtime
