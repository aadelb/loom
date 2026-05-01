# Instructor Integration Summary

## Overview

Successfully integrated the [instructor](https://github.com/jxnl/instructor) library into Loom v3 to provide guaranteed structured outputs from LLMs with automatic validation and retry.

## Files Created

### Core Implementation

1. **src/loom/tools/instructor_backend.py** (~310 lines)
   - `research_structured_extract()` - Main MCP tool function
   - `_patch_and_call_instructor()` - Patches provider client with instructor
   - `_create_pydantic_model()` - Dynamically creates Pydantic models from schema dicts
   - Graceful fallback to `research_llm_extract` if instructor not installed
   - Comprehensive error handling with secret sanitization
   - Full async/await support

### Parameter Validation

2. **src/loom/params.py** (added InstructorStructuredExtractParams)
   - `InstructorStructuredExtractParams` - Pydantic v2 parameter model
   - Validates text (1-100,000 chars)
   - Validates output_schema (1-100 fields, valid type names)
   - Validates model string, max_retries (1-10), provider override
   - Extra fields forbidden, strict mode enabled
   - Comprehensive field validators for safety

### Tests

3. **tests/test_tools/test_instructor_backend.py** (~350 lines)
   - `TestCreatePydanticModel` - Tests dynamic model creation
   - `TestInstructorAvailability` - Tests fallback behavior
   - `TestStructuredExtractWithInstructor` - Integration tests (when instructor available)
   - `TestInstructorParamValidation` - Parameter validation tests
   - 30+ test cases covering success paths, errors, edge cases
   - Uses pytest markers for conditional test execution

### Documentation

4. **docs/instructor_integration.md** (~400 lines)
   - Comprehensive feature overview
   - Installation instructions
   - Complete API reference
   - 10+ usage examples
   - Configuration guide (env vars + config.json)
   - Cost estimation table
   - Error handling guide
   - Performance tips
   - Troubleshooting section

5. **examples/instructor_extraction_example.py** (~200 lines)
   - 5 runnable example scenarios
   - Basic extraction (person data)
   - Complex extraction (product with mixed types)
   - Fallback demonstration
   - Provider override example
   - Error handling example

## Key Features

### Schema Support

- **Type Coverage**: str, string, int, integer, float, bool, boolean, list, dict, object
- **Dynamic Models**: Pydantic models created on-the-fly from schema dicts
- **Validation**: Early schema validation with clear error messages
- **Flexibility**: 1-100 fields per schema, 1-100,000 char inputs

### Reliability

- **Automatic Retry**: Configurable retries (1-10) on validation failure
- **Cascade Support**: Falls through 8 LLM providers on failure
- **Provider Override**: Force specific provider (nvidia, openai, anthropic, groq, deepseek, gemini, moonshot, vllm)
- **Graceful Fallback**: If instructor not installed, uses `research_llm_extract`
- **Error Handling**: Comprehensive exception handling with secret sanitization

### Integration

- **Cost Tracking**: Integrates with Loom's cost tracking system
- **LLMResponse**: Reuses Loom's response model with cost, latency, tokens
- **Config System**: Respects LLM_CASCADE_ORDER, LLM_DAILY_COST_CAP_USD, etc.
- **Logging**: Structured logging with secret sanitization
- **Untrusted Content Wrapping**: Prevents prompt injection attacks

## Architecture

### Async Call Flow

```
research_structured_extract()
  ├─ Check instructor availability
  ├─ Validate output_schema early
  ├─ Wrap untrusted text
  ├─ Call LLM with cascade (_call_with_cascade)
  ├─ Get provider instance
  ├─ Patch client with instructor
  ├─ Call _patch_and_call_instructor()
  │   ├─ Create Pydantic model
  │   ├─ Patch client with instructor.from_openai()
  │   └─ Call with response_model constraint + retries
  └─ Return validated dict or error
```

### Fallback Flow

```
If _INSTRUCTOR_AVAILABLE is False:
  research_structured_extract()
    └─ Import research_llm_extract
    └─ Call with same parameters
    └─ Normalize response format
    └─ Return with instructor_used=False
```

## Response Format

All responses include consistent fields:

```python
{
    "extracted_data": dict | None,      # Validated extraction or None on error
    "model": str,                        # Model identifier used
    "provider": str,                     # Provider name (openai, nvidia, etc.)
    "cost_usd": float,                  # Estimated USD cost
    "retries_needed": int,              # Number of validation retries performed
    "validation_passed": bool,          # True on success, False on error
    "instructor_used": bool,            # True if instructor, False if fallback
    "error": str | None,                # Error message on failure
}
```

## Testing Strategy

### Unit Tests
- Dynamic model creation with all supported types
- Schema validation (empty, invalid types)
- Type aliases (string->str, integer->int, etc.)
- Case-insensitive type names

### Integration Tests
- Tool availability detection
- Fallback behavior when instructor unavailable
- Parameter model validation (bounds, types)
- Extra fields forbidden enforcement
- Strict mode type coercion prevention

### Test Markers
- `@pytest.mark.skipif(not _INSTRUCTOR_AVAILABLE, ...)` - Tests requiring instructor
- Graceful skipping when instructor not installed
- Comprehensive coverage of fallback paths

## Code Quality

### Type Safety
- Full type hints on all functions
- Pydantic v2 with `strict=True`, `extra="forbid"`
- Type-checked response dict

### Error Handling
- Custom ValueError for schema issues
- Custom RuntimeError for extraction failures
- Secret sanitization in error messages
- Comprehensive logging with context

### Performance
- Async/await throughout
- Lazy provider initialization
- Single LLM call per extraction (instructor handles retries internally)
- No blocking operations

### Security
- Input validation at all boundaries
- SSRF-safe URL handling (via shared validators)
- Secret sanitization in logs and errors
- Untrusted content wrapping to prevent prompt injection

## Configuration

### Environment Variables

```bash
# Must be set for LLM providers to work
export OPENAI_API_KEY="sk-..."          # For OpenAI fallback
export ANTHROPIC_API_KEY="sk-ant-..."   # For Anthropic fallback
export GROQ_API_KEY="gsk_..."           # For Groq fallback
export NVIDIA_NIM_API_KEY="nvapi-..."   # For NVIDIA NIM

# Optional
export LLM_CASCADE_ORDER='["nvidia","openai","anthropic"]'
export LLM_DAILY_COST_CAP_USD="10.0"
export LLM_MAX_PARALLEL="12"
```

### Config File (~/.loom/config.json)

```json
{
    "LLM_CASCADE_ORDER": ["nvidia", "openai", "anthropic"],
    "LLM_DEFAULT_CHAT_MODEL": "gpt-4o",
    "LLM_DAILY_COST_CAP_USD": 10.0,
    "LLM_MAX_PARALLEL": 12
}
```

## Installation

### For Full Features (With Instructor)

```bash
# Install instructor
pip install instructor>=0.30.0

# Verify installation
python -c "import instructor; print(instructor.__version__)"
```

### Fallback Mode (Without Instructor)

Tool works automatically without instructor - no action needed. Falls back to `research_llm_extract`.

## Usage

### Basic Usage

```python
import asyncio
from loom.tools.instructor_backend import research_structured_extract

async def main():
    result = await research_structured_extract(
        text="Alice is 30 years old",
        output_schema={"name": "str", "age": "int"}
    )
    print(result["extracted_data"])
    # Output: {"name": "Alice", "age": 30}

asyncio.run(main())
```

### Via MCP Server (When Registered)

```bash
# Start Loom MCP server
loom serve

# In another terminal, call the tool
# The tool will be available as research_structured_extract
# with parameters: text, output_schema, model, max_retries, provider_override
```

## Limitations

1. **Schema Types Only**: Only predefined types (str, int, float, bool, list, dict) supported
   - Workaround: Use "dict" for complex nested objects

2. **Single LLM Call**: One LLM call per extraction (instructor retries internally)
   - Workaround: Call multiple times for multiple extractions

3. **Text Length**: 20,000 char limit on untrusted text (Loom standard)
   - Workaround: Truncate or summarize input first

## Future Enhancements

- [ ] Support for nested Pydantic models in schema
- [ ] Optional fields (with default values)
- [ ] Custom field validators via schema
- [ ] Batch extraction (extract from multiple texts in one call)
- [ ] Streaming extraction (for large outputs)
- [ ] Async retry backoff strategies

## References

- **Instructor Repo**: https://github.com/jxnl/instructor
- **Instructor Docs**: https://python.useinstructor.com/
- **Pydantic Docs**: https://docs.pydantic.dev/
- **Loom GitHub**: https://github.com/aadel/loom
- **Loom Architecture**: docs/architecture.md
- **LLM Providers**: docs/api-keys.md

## Author

**Ahmed Adel Bakr Alderai**

Integration completed: May 1, 2025
