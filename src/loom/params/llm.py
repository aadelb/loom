"""Pydantic parameter models for llm tools."""


from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from loom.config import CONFIG
from loom.validators import validate_url

# Default Accept-Language header sourced from config
_DEFAULT_ACCEPT_LANG = CONFIG.get("DEFAULT_ACCEPT_LANGUAGE", "en-US,en;q=0.9,ar;q=0.8")


__all__ = [
    "ArticleExtractParams",
    "CamelotTableExtractParams",
    "EmbeddingCollideParams",
    "ExtractCookiesParams",
    "InstructorStructuredExtractParams",
    "KnowledgeExtractParams",
    "LLMAnswerParams",
    "LLMChatParams",
    "LLMClassifyParams",
    "LLMEmbedParams",
    "LLMExtractParams",
    "LLMQueryExpandParams",
    "LLMSummarizeParams",
    "LLMTranslateParams",
    "NodriverExtractParams",
    "PDFExtractParams",
    "PaddleOCRParams",
    "ScraperEngineExtractParams",
    "StructuredCrawlParams",
    "StructuredLLMParams",
    "UnstructuredDocumentExtractParams",
    "CompressPromptParams",
]


class ArticleExtractParams(BaseModel):
    """Parameters for research_article_extract tool."""

    url: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)




class CamelotTableExtractParams(BaseModel):
    """Parameters for research_table_extract tool."""

    pdf_url: str = Field(
        "",
        description="URL to PDF file (auto-download)",
        max_length=2048,
    )
    pdf_path: str = Field(
        "",
        description="Local file path to PDF",
        max_length=2048,
    )
    pages: str = Field(
        "all",
        description="Page range: 'all', single number (1), range (1-5), or comma-separated (1,3,5)",
        max_length=100,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("pdf_url")
    @classmethod
    def validate_pdf_url(cls, v: str) -> str:
        """URL must be empty or valid."""
        if v and v.strip():
            validate_url(v)
        return v

    @field_validator("pages")
    @classmethod
    def validate_pages(cls, v: str) -> str:
        """Pages must be 'all' or valid page range."""
        if v == "all":
            return v
        # Basic validation
        try:
            if "-" in v:
                parts = v.split("-")
                if len(parts) != 2:
                    raise ValueError("invalid range")
                int(parts[0])
                int(parts[1])
            elif "," in v:
                for p in v.split(","):
                    int(p.strip())
            else:
                int(v)
        except (ValueError, AttributeError):
            raise ValueError("pages must be 'all', single number, range (1-5), or comma-separated (1,3,5)")
        return v




class EmbeddingCollideParams(BaseModel):
    """Parameters for research_embedding_collide tool."""

    target_text: str = Field(..., min_length=1, max_length=5000)
    malicious_payload: str = Field(..., min_length=1, max_length=1000)
    method: Literal[
        "synonym_swap", "context_inject", "semantic_trojan", "retrieval_poison"
    ] = "synonym_swap"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("target_text")
    @classmethod
    def validate_target_text(cls, v: str) -> str:
        if not v or len(v) < 10:
            raise ValueError("target_text must be at least 10 characters")
        return v.strip()

    @field_validator("malicious_payload")
    @classmethod
    def validate_payload(cls, v: str) -> str:
        if not v:
            raise ValueError("malicious_payload required")
        return v.strip()

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        valid = {"synonym_swap", "context_inject", "semantic_trojan", "retrieval_poison"}
        if v not in valid:
            raise ValueError(f"method must be in {valid}")
        return v




class ExtractCookiesParams(BaseModel):
    """Parameters for research_extract_cookies tool."""

    url: str
    follow_redirects: bool = True

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)




class InstructorStructuredExtractParams(BaseModel):
    """Parameters for research_structured_extract tool."""

    text: str = Field(
        ...,
        description="Input text to extract structured data from",
        min_length=1,
        max_length=100000,
    )
    output_schema: dict[str, str] = Field(
        ...,
        description="Field definitions (e.g., {'name': 'str', 'age': 'int', 'items': 'list'})",
    )
    model: str = Field(
        "auto",
        description="LLM model to use ('auto' for cascade)",
        max_length=100,
    )
    max_retries: int = Field(
        3,
        description="Max validation retries (1-10)",
        ge=1,
        le=10,
    )
    provider_override: str | None = Field(
        None,
        description="Force a specific provider (nvidia, openai, anthropic, groq, deepseek, gemini, moonshot, vllm)",
        max_length=50,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Text must be non-empty and within limits."""
        if not v or not v.strip():
            raise ValueError("text cannot be empty")
        return v

    @field_validator("output_schema")
    @classmethod
    def validate_schema(cls, v: dict[str, str]) -> dict[str, str]:
        """Schema must be non-empty dict with valid type names."""
        if not v:
            raise ValueError("output_schema cannot be empty")
        if len(v) > 100:
            raise ValueError("output_schema max 100 fields")

        valid_types = {
            "str", "string",
            "int", "integer",
            "float",
            "bool", "boolean",
            "list",
            "dict", "object",
        }

        for field_name, field_type in v.items():
            if not isinstance(field_name, str) or not field_name:
                raise ValueError("schema field names must be non-empty strings")
            if len(field_name) > 50:
                raise ValueError(f"field name '{field_name}' exceeds 50 chars")
            if not isinstance(field_type, str) or field_type.lower() not in valid_types:
                raise ValueError(
                    f"invalid type '{field_type}' for field '{field_name}'. "
                    f"Valid: str, int, float, bool, list, dict"
                )

        return v

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Model must be non-empty or 'auto'."""
        v = v.strip()
        if not v:
            raise ValueError("model cannot be empty")
        return v

    @field_validator("provider_override")
    @classmethod
    def validate_provider(cls, v: str | None) -> str | None:
        """Provider, if provided, must be in allowed list."""
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("provider_override cannot be empty string")

        allowed = {
            "nvidia", "openai", "anthropic", "groq",
            "deepseek", "gemini", "moonshot", "vllm",
        }
        if v.lower() not in allowed:
            raise ValueError(
                f"invalid provider '{v}'. Allowed: {', '.join(sorted(allowed))}"
            )
        return v.lower()



class KnowledgeExtractParams(BaseModel):
    """Parameters for research_knowledge_extract tool."""

    text: str
    entity_types: list[str] | None = None

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text cannot be empty")
        if len(v) > 100000:
            raise ValueError("text max 100000 chars")
        return v

    @field_validator("entity_types")
    @classmethod
    def validate_entity_types(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        if not isinstance(v, list):
            raise ValueError("entity_types must be a list")
        if len(v) > 20:
            raise ValueError("entity_types max 20 items")
        for et in v:
            if not isinstance(et, str) or len(et) > 50:
                raise ValueError("each entity_type must be a string <= 50 chars")
        return v




class LLMAnswerParams(BaseModel):
    """Parameters for research_llm_answer tool."""

    question: str
    context: str | None = None
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("question must be non-empty")
        if len(v) > 1000:
            raise ValueError("question max 1000 characters")
        return v




class LLMChatParams(BaseModel):
    """Parameters for research_llm_chat tool."""

    messages: list[dict[str, str]]
    provider: str = "openai"
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if v < 0.0 or v > 2.0:
            raise ValueError("temperature must be 0.0-2.0")
        return v




class LLMClassifyParams(BaseModel):
    """Parameters for research_llm_classify tool."""

    text: str
    categories: list[str]
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v: list[str]) -> list[str]:
        if not v or len(v) < 2:
            raise ValueError("categories must have at least 2 items")
        if len(v) > 20:
            raise ValueError("categories max 20 items")
        return v




class LLMEmbedParams(BaseModel):
    """Parameters for research_llm_embed tool."""

    text: str
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("text must be non-empty")
        if len(v) > 10000:
            raise ValueError("text max 10000 characters")
        return v




class LLMExtractParams(BaseModel):
    """Parameters for research_llm_extract tool."""

    text: str
    schema_def: dict[str, Any] = Field(alias="schema")
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "ignore", "strict": True, "populate_by_name": True}




class LLMQueryExpandParams(BaseModel):
    """Parameters for research_llm_query_expand tool."""

    query: str
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        if len(v) > 500:
            raise ValueError("query max 500 characters")
        return v




class LLMSummarizeParams(BaseModel):
    """Parameters for research_llm_summarize tool."""

    text: str
    max_length: int = 500
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("max_length")
    @classmethod
    def validate_max_length(cls, v: int) -> int:
        if v < 50 or v > 5000:
            raise ValueError("max_length must be 50-5000")
        return v




class LLMTranslateParams(BaseModel):
    """Parameters for research_llm_translate tool."""

    text: str
    target_language: str
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("target_language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 100:
            raise ValueError("target_language max 100 characters")
        return v




class NodriverExtractParams(BaseModel):
    """Parameters for research_nodriver_extract tool."""

    url: str
    css_selector: str | None = None
    xpath: str | None = None
    timeout: int = 30

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 1 or v > 120:
            raise ValueError("timeout must be 1-120 seconds")
        return v

    @field_validator("css_selector")
    @classmethod
    def validate_css_selector(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 512:
            raise ValueError("css_selector max 512 chars")
        return v

    @field_validator("xpath")
    @classmethod
    def validate_xpath(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 512:
            raise ValueError("xpath max 512 chars")
        return v




class PDFExtractParams(BaseModel):
    """Parameters for research_pdf_extract tool."""

    url: str
    extract_text: bool = True
    extract_images: bool = False
    extract_tables: bool = True

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        url = validate_url(v)
        if not url.lower().endswith(".pdf"):
            raise ValueError("url must point to a PDF file")
        return url




class PaddleOCRParams(BaseModel):
    """Parameters for research_paddle_ocr tool."""

    image_url: str = Field(
        "",
        description="URL to image file (auto-download)",
        max_length=2048,
    )
    image_path: str = Field(
        "",
        description="Local file path to image",
        max_length=2048,
    )
    languages: list[str] | None = Field(
        None,
        description="List of language codes (e.g., ['en', 'ar']). Defaults to ['en'].",
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, v: str) -> str:
        """URL must be empty or valid."""
        if v and v.strip():
            validate_url(v)
        return v

    @field_validator("languages")
    @classmethod
    def validate_languages(cls, v: list[str] | None) -> list[str] | None:
        """Languages must be non-empty list of valid codes."""
        if v is None:
            return v
        if not isinstance(v, list) or not v:
            raise ValueError("languages must be a non-empty list")
        if len(v) > 10:
            raise ValueError("max 10 languages supported")
        # Basic validation: 2-3 char language codes
        for lang in v:
            if not isinstance(lang, str) or len(lang) < 2 or len(lang) > 5:
                raise ValueError(f"invalid language code: {lang}")
        return v




class ScraperEngineExtractParams(BaseModel):
    """Parameters for research_engine_extract tool."""

    url: str
    query: str
    model: Literal["auto", "groq", "openai", "gemini"] = "auto"
    mode: Literal["auto", "stealth", "max", "fast"] = "auto"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query cannot be empty")
        if len(v) > 500:
            raise ValueError("query max 500 chars")
        return v.strip()




class StructuredCrawlParams(BaseModel):
    """Parameters for research_structured_crawl tool."""

    url: str
    schema_map: dict[str, str] = Field(
        description="Dict mapping field names to CSS selectors",
        min_length=1,
        alias="schema",
    )
    max_pages: int = Field(
        default=5,
        description="Maximum pages to crawl (1-50)",
        ge=1,
        le=50,
    )
    use_js: bool = Field(
        default=False,
        description="Use Playwright (JS-enabled) instead of BeautifulSoup",
    )

    model_config = {"extra": "ignore", "strict": True, "populate_by_name": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("schema_map")
    @classmethod
    def validate_schema_map(cls, v: dict[str, str]) -> dict[str, str]:
        if not v:
            raise ValueError("schema cannot be empty")
        for field_name, selector in v.items():
            if not isinstance(field_name, str) or not isinstance(selector, str):
                raise ValueError("schema keys and values must be strings")
            if len(selector) > 256:
                raise ValueError(f"CSS selector for {field_name} exceeds 256 chars")
        return v




class StructuredLLMParams(BaseModel):
    """Parameters for research_structured_llm tool."""

    prompt: str
    output_schema: dict[str, str]
    model: str = "nvidia_nim"
    provider_override: str | None = None

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("prompt must be non-empty")
        v = v.strip()
        if len(v) > 20000:
            raise ValueError("prompt max 20000 characters")
        return v

    @field_validator("output_schema")
    @classmethod
    def validate_output_schema(cls, v: dict[str, str]) -> dict[str, str]:
        if not v:
            raise ValueError("output_schema cannot be empty")
        if len(v) > 50:
            raise ValueError("output_schema max 50 fields")
        valid_types = {"str", "string", "int", "integer", "float", "bool", "boolean", "list", "dict", "object"}
        for field_name, field_type in v.items():
            if field_type.lower() not in valid_types:
                raise ValueError(
                    f"invalid type '{field_type}' for field '{field_name}'. "
                    f"Valid types: {', '.join(valid_types)}"
                )
        return v

    @field_validator("provider_override")
    @classmethod
    def validate_provider_override(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid = {"nvidia", "openai", "anthropic", "groq", "deepseek", "gemini", "moonshot", "vllm"}
        if v.lower() not in valid:
            raise ValueError(f"invalid provider '{v}'. Valid: {', '.join(valid)}")
        return v




class UnstructuredDocumentExtractParams(BaseModel):
    """Parameters for research_document_extract tool."""

    file_path: str = ""
    url: str = ""
    strategy: str = "auto"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        if v and v.strip():
            return validate_url(v)
        return v

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        v = v.lower().strip()
        valid_strategies = {"auto", "fast", "hi_res", "ocr_only"}
        if v not in valid_strategies:
            raise ValueError(f"strategy must be one of {valid_strategies}")
        return v





class CompressPromptParams(BaseModel):
    """Parameters for research_compress_prompt tool."""

    text: str
    target_ratio: float = 0.5

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("text must be a non-empty string")
        if len(v) > 1_000_000:
            raise ValueError("text max 1,000,000 characters")
        return v

    @field_validator("target_ratio")
    @classmethod
    def validate_target_ratio(cls, v: float) -> float:
        if not isinstance(v, (int, float)):
            raise ValueError("target_ratio must be a number")
        if not 0.1 <= v <= 0.9:
            raise ValueError("target_ratio must be between 0.1 and 0.9")
        return float(v)
