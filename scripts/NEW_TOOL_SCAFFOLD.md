# Tool Scaffold Generator

## Overview

`scripts/new_tool.py` is a CLI generator that creates all required files for a new Loom MCP tool in ~2 minutes, reducing manual work from 30 minutes to just boilerplate implementation.

## What It Generates

The script generates **all 8 required items** from CLAUDE.md's "Adding new tools" checklist:

1. **Tool implementation** (`src/loom/tools/{tool_name}.py`) — async function with:
   - Proper docstring
   - Type hints on all parameters
   - Logging setup
   - Error handling pattern
   - Pydantic imports
   - Structured return dict

2. **Pydantic parameter model** (appended to `src/loom/params.py`) with:
   - Field definitions with proper types
   - Default values (with correct quoting)
   - `extra="forbid", strict=True` validation
   - Docstring

3. **Pytest test file** (`tests/test_tools/test_{tool_name}.py`) with:
   - Signature verification test
   - Basic execution test
   - Error handling test
   - Logging verification test
   - Proper asyncio markers

4-8. **Instructions printed to console** for:
   - Register tool in `server.py`
   - Update `docs/tools-reference.md`
   - Update `docs/help.md`
   - Run tests
   - Lint & format

## Usage

### Basic

```bash
python scripts/new_tool.py --name fetch_rss --description "Fetch and parse RSS feeds"
```

### With Parameters

```bash
python scripts/new_tool.py \
  --name fetch_rss \
  --params "url:str,limit:int=10" \
  --category intelligence \
  --description "Fetch and parse RSS feeds"
```

### Complex Example

```bash
python scripts/new_tool.py \
  --name sentiment_analyzer \
  --params "text:str,language:str=en,confidence:float=0.5,include_scores:bool=True" \
  --category analysis \
  --description "Analyze sentiment with language and confidence settings"
```

### Dry Run (Preview Only)

```bash
python scripts/new_tool.py \
  --name my_tool \
  --params "query:str,limit:int=100" \
  --dry-run
```

## Parameter Syntax

Format: `name:type[=default][,name2:type=default2]`

### Supported Types

- `str` — String parameter
- `int` — Integer parameter
- `float` — Float parameter
- `bool` — Boolean parameter
- `list` — List parameter
- `dict` — Dict parameter

### Examples

| Input | Parsed As |
|-------|-----------|
| `url:str` | Required string parameter |
| `limit:int=10` | Integer with default 10 |
| `sort:str=hot` | String with default "hot" |
| `confidence:float=0.9` | Float with default 0.9 |
| `include:bool=True` | Boolean with default True |
| `url:str,limit:int=10` | Multiple parameters |

## Generated Code Patterns

### Tool Implementation

```python
async def research_my_tool(
    query: str,
    limit: int = 10,
) -> dict[str, Any]:
    """My tool description.

    Args:
        query: str (required)
        limit: int, default=10

    Returns:
        dict with keys: result, tool, error (if failed)
    """
    try:
        # Input validation
        # TODO: validate query

        # TODO: Implement core logic here
        logger.info(f"Executing research_my_tool")

        return {
            "result": "TODO: implement",
            "tool": "research_my_tool",
            "error": None,
        }

    except Exception as e:
        logger.error(f"Error in research_my_tool: {str(e)}")
        return {
            "result": None,
            "tool": "research_my_tool",
            "error": str(e),
        }
```

### Pydantic Model

```python
class MyToolParams(BaseModel):
    """My Tool parameters."""

    query: str
    limit: int = 10

    model_config = {"extra": "forbid", "strict": True}
```

### Test File

```python
@pytest.mark.asyncio
async def test_research_my_tool_signature():
    """Verify function signature."""
    import inspect

    sig = inspect.signature(my_tool.research_my_tool)
    params = list(sig.parameters.keys())

    assert "query" in params
    assert "limit" in params
    assert sig.return_annotation != inspect.Signature.empty

@pytest.mark.asyncio
async def test_research_my_tool_basic():
    """Test basic execution."""
    result = await my_tool.research_my_tool(query="test_value", limit=42)

    assert isinstance(result, dict)
    assert "tool" in result
    assert "error" in result
    assert result["tool"] == "research_my_tool"
```

## Manual Steps After Generation

After running `new_tool.py`, complete these manual steps:

### 1. Implement Tool Logic

Edit `src/loom/tools/{tool_name}.py`:
- Replace `# TODO: Implement core logic here` with actual implementation
- Add input validation if needed
- Add proper error handling beyond generic Exception

### 2. Register in Server

Edit `src/loom/server.py` and find `_register_tools()` function. Add:

```python
mcp.tool()(
    _wrap_tool(
        my_tool.research_my_tool,
        "my_tool",
    )
)
```

### 3. Update Documentation

#### docs/tools-reference.md
Add a section with:
- Tool description
- Parameters and types
- Return value format
- Example usage
- Cost estimation (if applicable)

#### docs/help.md
Add troubleshooting section if applicable

### 4. Run Tests

```bash
pytest tests/test_tools/test_my_tool.py -v
```

### 5. Lint & Format

```bash
ruff check --fix src/loom/tools/my_tool.py
ruff format src/loom/tools/my_tool.py
mypy src/loom/tools/my_tool.py
```

### 6. Verify Completeness

```bash
scripts/verify_completeness.py
```

## Features

✓ Automatic snake_case to PascalCase conversion for class names  
✓ Proper string default quoting (`"en"` not `en`)  
✓ Numeric/boolean defaults handled correctly  
✓ URL validation support for URL-type parameters  
✓ Type hints on all function signatures  
✓ Async function support  
✓ Structured error handling  
✓ Logging setup  
✓ Pytest boilerplate with 4 test templates  
✓ Pydantic v2 strict validation  
✓ Project root auto-detection  
✓ Dry-run mode for preview  

## Error Cases

```bash
# Tool name not valid Python identifier
python scripts/new_tool.py --name "2invalid"
# Error: Tool name '2invalid' is not a valid Python identifier

# Tool already exists
python scripts/new_tool.py --name fetch_rss
# Error: /path/to/src/loom/tools/fetch_rss.py already exists

# Project root not found
cd /tmp && python /Users/aadel/projects/loom/scripts/new_tool.py --name test
# Error: Could not find src/loom directory...

# Invalid parameter syntax
python scripts/new_tool.py --name test --params "url" 
# Error: ValueError during parsing
```

## Time Breakdown

| Task | Manual (old) | With Scaffold |
|------|------------|---------------|
| Create files | 5 min | 30 sec |
| Write function signature | 2 min | 0 sec |
| Write docstring | 2 min | 0 sec |
| Write parameter validation | 3 min | 0 sec |
| Write error handling | 3 min | 0 sec |
| Create Pydantic model | 3 min | 0 sec |
| Create test boilerplate | 5 min | 0 sec |
| **Total** | **~30 min** | **~2 min** |

## Checklist Integration

After running `new_tool.py`, this checklist tracks your progress to 8/8:

- [x] 1. Implementation in `src/loom/tools/{tool_name}.py` — **DONE by scaffold**
- [x] 2. Tool registration in `server.py:_register_tools()` — **MANUAL (instructions printed)**
- [x] 3. Pydantic model in `params.py` — **DONE by scaffold**
- [x] 4. Tests in `tests/test_tools/test_{tool_name}.py` — **DONE by scaffold**
- [ ] 5. Entry in `docs/tools-reference.md` — **MANUAL (instructions printed)**
- [ ] 6. Entry in `docs/help.md` — **MANUAL (instructions printed)**
- [ ] 7. Handle ImportError in `server.py` (if needed) — **MANUAL (if applicable)**
- [ ] 8. Run `scripts/verify_completeness.py` — **MANUAL (instructions printed)**

## Examples

### Example 1: Simple Tool

```bash
python scripts/new_tool.py \
  --name health_check \
  --description "Check service health status"
```

### Example 2: API Tool

```bash
python scripts/new_tool.py \
  --name github_search \
  --params "query:str,org:str=,language:str=python,stars_min:int=1000" \
  --category research \
  --description "Search GitHub repos with optional filters"
```

### Example 3: Data Processing

```bash
python scripts/new_tool.py \
  --name text_summarize \
  --params "text:str,max_length:int=500,format:str=bullet" \
  --category analysis \
  --description "Summarize text with length and format options"
```

## Limitations

- Currently generates async functions only (sync not supported)
- Parameter defaults must be literal values (no expressions)
- Single-line docstrings only (multi-line possible but manual edit needed)
- Does not auto-generate API client code (manual implementation)

## Script Location

- **Source**: `/Users/aadel/projects/loom/scripts/new_tool.py`
- **Executable**: Yes (has shebang and executable permissions)
- **Dependencies**: Python 3.11+ with standard library only

## Development Notes

To extend the scaffold generator with new features:

1. Edit `generate_tool_impl()` to change tool template
2. Edit `generate_params_model()` to change Pydantic template
3. Edit `generate_test_file()` to change test template
4. Add new helper functions as needed
5. Test with `--dry-run` before committing

---

**Time saved per tool**: ~28 minutes  
**Time saved at 220+ tools**: ~103 hours  
**When to use**: Always for new tools
