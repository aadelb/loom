"""Pydantic parameter models for adversarial tools."""


from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from loom.config import CONFIG
from loom.validators import filter_headers, validate_js_script, validate_local_file_path, validate_url

# Default Accept-Language header sourced from config
_DEFAULT_ACCEPT_LANG = CONFIG.get("DEFAULT_ACCEPT_LANGUAGE", "en-US,en;q=0.9,ar;q=0.8")


__all__ = [
    "ActiveSelectParams",
    "AdversarialBatchParams",
    "AdversarialDebateAttackerParams",
    "AttackEconomyLeaderboardParams",
    "AttackEconomySubmitParams",
    "AttackerTargetDebateParams",
    "CaptureHarParams",
    "CraftAdversarialParams",
    "FuseEvidenceParams",
    "HITLEvaluateParams",
    "HITLQueueParams",
    "HITLSubmitParams",
    "LifetimeOracleParams",
    "ModelEvidenceParams",
    "PotencyScoreParams",
    "PredictAttacksParams",
    "PreemptivePatchParams",
    "ResiliencePredictorParams",
    "ScapyPacketCraftParams",
    "SuperpositionPromptParams",
    "SwarmAttackParams",
    "UncertaintyEstimateParams",
]


class ActiveSelectParams(BaseModel):
    """Parameters for research_active_select tool."""

    candidate_strategies: list[str]
    budget: int = 3
    objective: Literal["maximize_success", "maximize_information", "balanced"] = "maximize_success"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("candidate_strategies")
    @classmethod
    def validate_candidate_strategies(cls, v: list[str]) -> list[str]:
        """Validate strategies list."""
        if not v:
            raise ValueError("candidate_strategies list cannot be empty")
        if len(v) > 100:
            raise ValueError("candidate_strategies list max 100 items")
        for strategy in v:
            if not isinstance(strategy, str) or not strategy.strip():
                raise ValueError("all strategies must be non-empty strings")
            if len(strategy) > 256:
                raise ValueError("each strategy max 256 characters")
        return v

    @field_validator("budget")
    @classmethod
    def validate_budget(cls, v: int) -> int:
        """Validate budget."""
        if v < 1 or v > 20:
            raise ValueError("budget must be 1-20 API calls")
        return v



class AdversarialBatchParams(BaseModel):
    """Parameters for research_adversarial_batch tool."""

    inputs: list[str]
    method: Literal[
        "greedy_swap",
        "insert_trigger",
        "unicode_perturb",
        "whitespace_inject",
        "semantic_shift",
    ] = "greedy_swap"
    budget: float = 0.1

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("inputs")
    @classmethod
    def validate_inputs(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("inputs list cannot be empty")
        if len(v) > 100:
            raise ValueError("inputs max 100 items")
        validated = []
        for inp in v:
            inp = inp.strip()
            if not inp:
                raise ValueError("each input must be non-empty")
            if len(inp) > 5000:
                raise ValueError("each input max 5000 characters")
            validated.append(inp)
        return validated

    @field_validator("budget")
    @classmethod
    def validate_budget(cls, v: float) -> float:
        if v < 0.01 or v > 0.5:
            raise ValueError("budget must be 0.01-0.5")
        return v



class AdversarialDebateAttackerParams(BaseModel):
    """Parameters for research_adversarial_debate tool."""

    topic: str = Field(
        description="Topic to debate (min 10 chars, max 500)",
        min_length=10,
        max_length=500,
    )
    pro_model: str = Field(
        default="groq",
        description="LLM provider for pro-disclosure side",
        max_length=64,
    )
    con_model: str = Field(
        default="nvidia",
        description="LLM provider for safety-cautious side",
        max_length=64,
    )
    max_rounds: int = Field(
        default=5,
        description="Max debate rounds (1-10)",
        ge=1,
        le=10,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("topic cannot be empty")
        return v.strip()




class AttackEconomyLeaderboardParams(BaseModel):
    """Parameters for research_economy_leaderboard tool."""

    top_n: int = 10

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("top_n")
    @classmethod
    def validate_top_n(cls, v: int) -> int:
        if not (1 <= v <= 100):
            raise ValueError("top_n must be between 1 and 100")
        return v




class AttackEconomySubmitParams(BaseModel):
    """Parameters for research_economy_submit tool."""

    strategy_name: str
    target_model: str
    asr: float
    description: str = ""

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("strategy_name")
    @classmethod
    def validate_strategy_name(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("strategy_name must be at least 3 characters")
        if len(v) > 200:
            raise ValueError("strategy_name max 200 characters")
        return v.strip()

    @field_validator("target_model")
    @classmethod
    def validate_target_model(cls, v: str) -> str:
        if len(v) < 2:
            raise ValueError("target_model must be at least 2 characters")
        if len(v) > 100:
            raise ValueError("target_model max 100 characters")
        return v.strip()

    @field_validator("asr")
    @classmethod
    def validate_asr(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("asr must be between 0.0 and 1.0")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        if len(v) > 1000:
            raise ValueError("description max 1000 characters")
        return v.strip()




class AttackerTargetDebateParams(BaseModel):
    """Parameters for research_adversarial_debate attacker-vs-target tool."""

    topic: str = Field(..., min_length=1, max_length=500)
    attacker_strategy: str = Field(default="auto", max_length=100)
    max_turns: int = Field(default=5, ge=1, le=10)
    target_model: Literal["nvidia", "openai", "anthropic", "groq", "deepseek", "gemini", "moonshot", "auto"] = "nvidia"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        """Validate topic is non-empty."""
        if not v.strip():
            raise ValueError("topic cannot be empty")
        if len(v) > 500:
            raise ValueError("topic max length is 500 characters")
        return v

    @field_validator("attacker_strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        """Validate strategy name."""
        if not v.strip():
            raise ValueError("strategy cannot be empty")
        if len(v) > 100:
            raise ValueError("strategy max length is 100 characters")
        return v



class CaptureHarParams(BaseModel):
    """Parameters for research_capture_har tool."""

    url: str
    duration_seconds: int = Field(default=10, ge=1, le=60)
    include_bodies: bool = True

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)




class CraftAdversarialParams(BaseModel):
    """Parameters for research_craft_adversarial tool."""

    benign_input: str
    target_output: str = "compliance"
    perturbation_budget: float = 0.1
    method: Literal[
        "greedy_swap",
        "insert_trigger",
        "unicode_perturb",
        "whitespace_inject",
        "semantic_shift",
    ] = "greedy_swap"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("benign_input")
    @classmethod
    def validate_input(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("benign_input cannot be empty")
        if len(v) > 5000:
            raise ValueError("benign_input max 5000 characters")
        return v

    @field_validator("target_output")
    @classmethod
    def validate_target(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("target_output cannot be empty")
        if len(v) > 200:
            raise ValueError("target_output max 200 characters")
        return v

    @field_validator("perturbation_budget")
    @classmethod
    def validate_budget(cls, v: float) -> float:
        if v < 0.01 or v > 0.5:
            raise ValueError("perturbation_budget must be 0.01-0.5")
        return v




class FuseEvidenceParams(BaseModel):
    """Parameters for research_fuse_evidence tool."""

    claims: list[str]
    sources: list[str] | None = None
    fusion_method: Literal[
        "weighted_consensus",
        "citation_chain",
        "academic_synthesis",
        "expert_panel",
        "meta_analysis",
    ] = "weighted_consensus"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("claims")
    @classmethod
    def validate_claims(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("claims list cannot be empty")
        if len(v) > 100:
            raise ValueError("claims max 100 items")
        for claim in v:
            if not isinstance(claim, str) or not claim.strip():
                raise ValueError("all claims must be non-empty strings")
            if len(claim) > 500:
                raise ValueError("each claim max 500 characters")
        return v

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            if len(v) > 100:
                raise ValueError("sources max 100 items")
            for source in v:
                if not isinstance(source, str) or not source.strip():
                    raise ValueError("all sources must be non-empty strings")
                if len(source) > 256:
                    raise ValueError("each source max 256 characters")
        return v




class HITLEvaluateParams(BaseModel):
    """Parameters for research_hitl_evaluate tool."""

    eval_id: str = Field(..., min_length=1, max_length=100)
    score: float = Field(..., ge=1.0, le=10.0)
    notes: str = Field(default="", max_length=2000)
    tags: list[str] | None = Field(default=None, max_length=10)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("eval_id")
    @classmethod
    def validate_eval_id(cls, v: str) -> str:
        if len(v.strip()) == 0:
            raise ValueError("eval_id cannot be empty")
        return v.strip()

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        valid_tags = {"effective", "partial", "refused", "hallucinated", "dangerous", "safe"}
        for tag in v:
            if tag not in valid_tags:
                raise ValueError(f"tag must be one of {valid_tags}, got '{tag}'")
        return list(set(v))  # Remove duplicates




class HITLQueueParams(BaseModel):
    """Parameters for research_hitl_queue tool."""

    status: str = Field(default="pending")
    limit: int = Field(default=20, ge=1, le=100)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = {"pending", "evaluated"}
        if v not in valid_statuses:
            raise ValueError(f"status must be one of {valid_statuses}, got '{v}'")
        return v



class HITLSubmitParams(BaseModel):
    """Parameters for research_hitl_submit tool."""

    strategy: str = Field(..., min_length=1, max_length=200)
    prompt: str = Field(..., min_length=1, max_length=10000)
    response: str = Field(..., min_length=1, max_length=50000)
    model: str = Field(default="unknown", min_length=1, max_length=100)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        if len(v.strip()) == 0:
            raise ValueError("strategy cannot be empty or whitespace-only")
        return v.strip()

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        if len(v.strip()) == 0:
            raise ValueError("model cannot be empty or whitespace-only")
        return v.strip()




class LifetimeOracleParams(BaseModel):
    """Parameters for research_lifetime_predict tool."""

    strategy_name: str
    strategy_text: str = ""
    target_models: list[str] | None = None
    is_public: bool = False

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("strategy_name")
    @classmethod
    def validate_strategy_name(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 256:
            raise ValueError("strategy_name must be 1-256 characters")
        return v

    @field_validator("strategy_text")
    @classmethod
    def validate_strategy_text(cls, v: str) -> str:
        if len(v) > 10000:
            raise ValueError("strategy_text max 10000 characters")
        return v

    @field_validator("target_models")
    @classmethod
    def validate_target_models(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            if len(v) > 20:
                raise ValueError("target_models max 20 items")
            for model in v:
                if not isinstance(model, str) or not model.strip():
                    raise ValueError("all models must be non-empty strings")
        return v




class ModelEvidenceParams(BaseModel):
    """Parameters for research_model_evidence tool."""

    query: str = Field(
        description="Query to search for evidence",
        max_length=10000,
    )
    source_model_names: list[str] | None = Field(
        default=None,
        description="Source models to use for evidence generation",
    )
    target_model_name: str = Field(
        default="gpt-4",
        description="Target model name",
        max_length=256,
    )
    max_evidence_sources: int = Field(
        default=3,
        description="Max evidence sources (1-10)",
        ge=1,
        le=10,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query cannot be empty")
        return v.strip()




class PotencyScoreParams(BaseModel):
    """Parameters for research_potency_score tool."""

    prompt: str = Field(..., min_length=1, max_length=5000)
    response: str = Field(..., min_length=1, max_length=50000)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Validate prompt is non-empty."""
        if not v.strip():
            raise ValueError("prompt cannot be empty")
        return v

    @field_validator("response")
    @classmethod
    def validate_response(cls, v: str) -> str:
        """Validate response is non-empty."""
        if not v.strip():
            raise ValueError("response cannot be empty")
        return v



class PredictAttacksParams(BaseModel):
    """Parameters for research_predict_attacks tool."""

    system_prompt: str = Field(..., min_length=1, max_length=10000)
    model: str = "auto"
    threat_level: Literal["low", "medium", "high", "critical"] = "high"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("system_prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("system_prompt cannot be empty")
        return v

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        v = v.strip().lower()
        valid = {"auto", "claude", "gpt", "gemini", "deepseek", "llama"}
        if v not in valid:
            raise ValueError(f"model must be one of {valid}")
        return v




class PreemptivePatchParams(BaseModel):
    """Parameters for research_preemptive_patch tool."""

    system_prompt: str = Field(..., min_length=1, max_length=10000)
    predicted_attacks: list[str] | None = None

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("system_prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("system_prompt cannot be empty")
        return v

    @field_validator("predicted_attacks")
    @classmethod
    def validate_attacks(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        valid_attacks = {
            "missing_role_anchoring",
            "no_output_constraints",
            "no_injection_resistance",
            "long_context",
            "no_multi_turn_defense",
        }
        for attack in v:
            if attack not in valid_attacks:
                raise ValueError(f"predicted_attacks must be subset of {valid_attacks}")
        return v




class ResiliencePredictorParams(BaseModel):
    """Parameters for research_predict_resilience tool."""

    strategy: str = Field(..., min_length=1, max_length=128)
    target_model: str = Field(default="auto", max_length=64)
    current_asr: float = Field(default=0.8, ge=0.0, le=1.0)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        """Validate strategy name format."""
        if not re.match(r"^[a-zA-Z0-9_\-]+$", v):
            raise ValueError("strategy must contain only alphanumeric, underscore, hyphen")
        return v.lower()

    @field_validator("target_model")
    @classmethod
    def validate_target_model(cls, v: str) -> str:
        """Validate target model name."""
        allowed_models = {
            "auto", "gpt4", "gpt4o", "gpt-4-turbo", "claude3", "claude3.5",
            "gemini", "gemini2", "llama2", "llama3", "deepseek", "mistral"
        }
        v_lower = v.lower()
        if v_lower not in allowed_models:
            raise ValueError(f"target_model must be one of {allowed_models}")
        return v_lower

    @field_validator("current_asr")
    @classmethod
    def validate_asr(cls, v: float) -> float:
        """Validate ASR is between 0 and 1."""
        if v < 0.0 or v > 1.0:
            raise ValueError("current_asr must be between 0.0 and 1.0")
        return v




class ScapyPacketCraftParams(BaseModel):
    """Parameters for research_packet_craft tool."""

    domain: str = Field(
        ...,
        description="Target IP address or hostname",
        max_length=255,
        alias="target",
    )
    packet_type: str = Field(
        "tcp_syn",
        description="Type of packet: tcp_syn, tcp_rst, icmp_echo, or udp_probe",
        max_length=50,
    )
    port: int = Field(
        80,
        description="Destination port (1-65535)",
        ge=1,
        le=65535,
    )
    timeout: int = Field(
        5,
        description="Response timeout in seconds (1-30)",
        ge=1,
        le=30,
    )

    model_config = {"extra": "ignore", "strict": True, "populate_by_name": True}

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        """Target must be non-empty hostname or IP."""
        if not v or not v.strip():
            raise ValueError("target cannot be empty")
        v = v.strip()
        if len(v) > 255:
            raise ValueError("target exceeds 255 chars")
        # Basic validation: alphanumeric, dots, hyphens
        if not all(c.isalnum() or c in ".-" for c in v):
            raise ValueError("target contains invalid characters")
        return v

    @field_validator("packet_type")
    @classmethod
    def validate_packet_type(cls, v: str) -> str:
        """Packet type must be valid."""
        v = v.strip()
        valid_types = {"tcp_syn", "tcp_rst", "icmp_echo", "udp_probe"}
        if v not in valid_types:
            raise ValueError(f"packet_type must be one of: {', '.join(sorted(valid_types))}")
        return v



class SuperpositionPromptParams(BaseModel):
    """Parameters for research_superposition_attack tool."""

    prompt: str
    num_superpositions: int = 10
    collapse_method: Literal["max_compliance", "max_stealth", "balanced", "diverse_top3"] = "max_compliance"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 2000:
            raise ValueError("prompt must be 1-2000 characters")
        return v

    @field_validator("num_superpositions")
    @classmethod
    def validate_num_superpositions(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("num_superpositions must be 1-100")
        return v




class SwarmAttackParams(BaseModel):
    """Parameters for research_swarm_attack tool."""

    target_prompt: str = Field(..., min_length=5, max_length=2000)
    swarm_size: int = Field(default=5, ge=1, le=20)
    rounds: int = Field(default=3, ge=1, le=5)
    share_findings: bool = Field(default=True)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("target_prompt")
    @classmethod
    def validate_target_prompt(cls, v: str) -> str:
        """Validate target prompt is non-empty."""
        if not v.strip():
            raise ValueError("target_prompt cannot be empty")
        if len(v) < 5:
            raise ValueError("target_prompt must be at least 5 characters")
        if len(v) > 2000:
            raise ValueError("target_prompt max length is 2000 characters")
        return v




class UncertaintyEstimateParams(BaseModel):
    """Parameters for research_uncertainty_estimate tool."""

    strategies: list[str]
    target_model: Literal["auto", "claude", "gpt", "deepseek", "gemini"] = "auto"
    prior_results: dict[str, float] | None = None

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("strategies")
    @classmethod
    def validate_strategies(cls, v: list[str]) -> list[str]:
        """Validate strategies list."""
        if not v:
            raise ValueError("strategies list cannot be empty")
        if len(v) > 100:
            raise ValueError("strategies list max 100 items")
        for strategy in v:
            if not isinstance(strategy, str) or not strategy.strip():
                raise ValueError("all strategies must be non-empty strings")
            if len(strategy) > 256:
                raise ValueError("each strategy max 256 characters")
        return v

    @field_validator("prior_results")
    @classmethod
    def validate_prior_results(cls, v: dict[str, float] | None) -> dict[str, float] | None:
        """Validate prior results dict."""
        if v is not None:
            if not isinstance(v, dict):
                raise ValueError("prior_results must be a dict")
            for key, val in v.items():
                if not isinstance(key, str) or not isinstance(val, (int, float)):
                    raise ValueError("prior_results keys must be strings, values must be floats")
                if not 0.0 <= val <= 1.0:
                    raise ValueError(f"prior_results values must be 0.0-1.0, got {val}")
        return v




