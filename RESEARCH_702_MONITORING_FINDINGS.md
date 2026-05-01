# Research 702: Real-Time Model Behavior Monitoring & Jailbreak Detection
## Production AI Safety Monitoring Systems (2025-2026)

**Research ID:** research_702_monitoring  
**Timestamp:** 2026-05-01  
**Research Scope:** Real-time jailbreak detection, production safety monitoring, anomaly detection  
**Target Integration:** Loom v3 dashboard, metrics modules, production guardrails

---

## Executive Summary

This research explores production-grade real-time monitoring systems for detecting jailbreak attempts and anomalous behavior in deployed large language models (LLMs). The focus is on low-latency streaming architectures, anomaly detection techniques, and alerting systems suitable for enterprise deployments.

---

## 1. Real-Time Jailbreak Detection in Production

### 1.1 Core Concepts

**Definition:** Real-time jailbreak detection involves identifying and responding to attempts to bypass LLM safety filters as they occur in production, rather than post-hoc analysis.

**Key Characteristics:**
- Sub-100ms latency requirements for streaming inference
- Per-token or per-completion classification
- Stateless processing (no session context required for basic detection)
- Low false-positive rates (<1-2%) to avoid blocking legitimate requests
- Integration at inference serving layer (NVIDIA Triton, vLLM, TGI)

### 1.2 Detection Approaches

#### A. Input-Side Jailbreak Detection
```
Query → Preprocessing → Classification → Decision
          ↓
      - Prompt injection patterns (DAN, role-play, context override)
      - Token-level semantic analysis
      - Known jailbreak templates matching
      - Syntax/semantic anomalies (sudden shifts in domain, register)
```

**Techniques:**
1. **Pattern Matching:** Maintain database of known jailbreak patterns (role-play instructions, system prompt extraction, in-context learning bypasses)
2. **Semantic Similarity:** Embed incoming prompts and compare against labeled jailbreak corpus
3. **Syntactic Analysis:** Detect structural anomalies (nested instructions, format injection, encoding tricks)
4. **Statistical Baselines:** Track prompt entropy, token diversity, instruction density

#### B. Output-Side Jailbreak Detection
```
LLM Response → Streaming Token Analysis → Toxicity/Harm Classification → Alert
                       ↓
    - Entropy spikes (sudden coherence loss)
    - Semantic drift (output diverges from safety expectations)
    - Prohibited content detection (hate, violence, abuse)
    - Instruction following patterns (detecting model compliance with jailbreak)
```

**Techniques:**
1. **Real-Time Toxicity Scoring:** Use lightweight classifiers (DistilBERT-based) on 512-token windows with <50ms latency
2. **Entropy Monitoring:** Track per-token probability distributions; flag when entropy spikes suggest distribution shift
3. **Semantic Consistency:** Compare response embeddings against safety baselines; alert if drift exceeds threshold
4. **Harm Taxonomy:** Classify outputs into categories (violence, sexual, illegal, deception, etc.) with confidence scores

---

## 2. Production AI Safety Monitoring Systems

### 2.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER REQUESTS                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │  INPUT SAFETY FILTER (1-5ms)   │
        │  - Prompt injection detection  │
        │  - PII/sensitive data masking  │
        │  - Query rate limiting         │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │  INFERENCE ENGINE              │
        │  - vLLM / TGI / Triton         │
        │  - Streaming generation        │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │  OUTPUT SAFETY PIPELINE        │
        │  (per-token, <20ms latency)    │
        │  1. Token embedding            │
        │  2. Toxicity classification    │
        │  3. Semantic drift detection   │
        │  4. Harm scoring               │
        │  5. Circuit breaker decision   │
        └────────────┬───────────────────┘
                     │
      ┌──────────────┴──────────────┐
      │                             │
      ▼                             ▼
  SAFE RESPONSE              FILTERED RESPONSE
  → Output to user            → Error / Truncation
  → Log (non-sensitive)       → Alert to security
  → Metrics (counters)        → Detailed logging
```

### 2.2 Input Safety Filters

**Objectives:**
- Detect prompt injection attacks early (before inference)
- Mask personally identifiable information (PII)
- Apply rate limiting per user/organization
- Validate query structure and length

**Implementation Patterns:**

```python
# Lightweight input validation
class InputSafetyFilter:
    def __init__(self):
        self.injection_patterns = compiled_regex_patterns
        self.pii_detector = spacy_model.load("en_core_web_sm")
        self.rate_limiter = SlidingWindowCounter()
    
    async def filter(self, query: str, user_id: str) -> SafetyResult:
        # Check rate limits
        if self.rate_limiter.is_exceeded(user_id):
            return SafetyResult(blocked=True, reason="rate_limit")
        
        # Check for injection patterns
        if self.injection_patterns.search(query):
            return SafetyResult(blocked=True, reason="prompt_injection")
        
        # Mask PII
        masked = self.pii_detector.mask_entities(query)
        
        # Check prompt length and structure
        if len(query) > MAX_LENGTH:
            return SafetyResult(blocked=True, reason="exceeds_max_length")
        
        return SafetyResult(blocked=False, masked_query=masked)
```

### 2.3 Output Safety Pipeline

**Per-Token Analysis:**

```python
# Real-time streaming safety classifier
class StreamingSafetyClassifier:
    def __init__(self, model_path: str):
        self.toxicity_model = load_lightweight_model(model_path)
        self.embedding_cache = {}
        self.baseline_embeddings = load_safety_baseline()
    
    async def classify_token(self, token: str, context: str) -> TokenSafetyScore:
        """Classify individual token with context awareness."""
        # Embed token with context
        emb = self.embedding_model.embed(f"{context} {token}")
        
        # Toxicity score
        tox_score = self.toxicity_model.predict(emb)
        
        # Semantic drift (compare to safety baseline)
        drift = cosine_distance(emb, self.baseline_embeddings["safe"])
        
        # Semantic consistency (should align with response so far)
        consistency = self._check_consistency(emb, context)
        
        return TokenSafetyScore(
            toxicity=tox_score,
            drift=drift,
            consistency=consistency,
            flags=self._extract_flags(token)
        )
    
    async def check_completion(self, response: str, metadata: dict) -> CompletionSafetyResult:
        """Classify full response at completion."""
        tokens = self.tokenizer.encode(response)
        
        # Sliding window analysis
        windows = [response[i:i+512] for i in range(0, len(response), 256)]
        
        window_scores = []
        for window in windows:
            score = self.toxicity_model.predict(window)
            window_scores.append(score)
        
        # Aggregate scores
        max_score = max(window_scores)
        mean_score = sum(window_scores) / len(window_scores)
        entropy = self._calculate_entropy(window_scores)
        
        return CompletionSafetyResult(
            max_toxicity=max_score,
            mean_toxicity=mean_score,
            entropy=entropy,
            should_block=max_score > TOXICITY_THRESHOLD
        )
```

---

## 3. Anomaly Detection on LLM Outputs

### 3.1 Entropy-Based Detection

**Principle:** Sudden increases in entropy (output unpredictability) often signal jailbreak success or model drift.

**Implementation:**
```python
class EntropyMonitor:
    def __init__(self, window_size: int = 100):
        self.window = deque(maxlen=window_size)
        self.baseline_entropy = None
    
    def update(self, logits: np.ndarray) -> dict:
        """
        Monitor entropy of token probability distributions.
        
        Args:
            logits: raw model output logits (batch_size, vocab_size)
        
        Returns:
            {entropy, entropy_spike, drift_flag}
        """
        # Compute probability distribution
        probs = softmax(logits, axis=-1)
        
        # Per-token entropy
        entropy = -sum(probs * log(probs + 1e-10))
        
        self.window.append(entropy)
        
        # Detect entropy spike
        if len(self.window) >= 10:
            recent_mean = np.mean(list(self.window)[-10:])
            baseline = np.mean(list(self.window))
            
            spike_detected = recent_mean > baseline * 1.5  # 50% jump
            
            return {
                "entropy": entropy,
                "recent_mean": recent_mean,
                "baseline": baseline,
                "spike_detected": spike_detected,
                "severity": (recent_mean / baseline) - 1.0 if baseline > 0 else 0
            }
        
        return {"entropy": entropy, "baseline": None}
```

**Interpretation:**
- Baseline entropy: ~4-6 nats for normal language
- Spike threshold: >1.5x baseline signals anomaly
- Sustained elevation (>5 tokens): likely jailbreak or distribution shift

### 3.2 Distribution Shift Detection

**Concept:** Monitor model output distributions against historical baselines to detect when inference falls outside safe ranges.

**Techniques:**

1. **KL Divergence Monitoring:**
   ```
   KL(current || baseline) > threshold → Alert
   - Baseline: rolling average of last 10,000 requests
   - Current: last 100-token window
   - Threshold: tuned to false-positive budget (typically <1%)
   ```

2. **Maximum Mean Discrepancy (MMD):**
   ```
   MMD(current_embeddings, baseline_embeddings) > threshold
   - More robust to outliers than KL divergence
   - Kernel-based distance metric
   - Scales to high-dimensional embeddings
   ```

3. **Isolation Forest (Streaming Version):**
   ```
   Detect anomalous tokens/responses via isolation paths
   - Fast training on baseline data
   - Real-time inference <5ms per sample
   - Unsupervised (no labeled jailbreaks needed)
   ```

### 3.3 Semantic Drift Detection

**Goal:** Identify when model responses diverge from expected semantic patterns.

```python
class SemanticDriftDetector:
    def __init__(self, baseline_corpus: list[str], embedding_model):
        self.embedding_model = embedding_model
        # Compute centroid of safe responses
        embeddings = [embedding_model.embed(text) for text in baseline_corpus]
        self.safe_centroid = np.mean(embeddings, axis=0)
        self.safe_radius = np.percentile(
            [cosine_distance(e, self.safe_centroid) for e in embeddings],
            95  # 95th percentile as boundary
        )
    
    def check_drift(self, response: str) -> DriftResult:
        """Check if response drifts outside safe semantic space."""
        emb = self.embedding_model.embed(response)
        
        # Distance from safe centroid
        distance = cosine_distance(emb, self.safe_centroid)
        
        # Magnitude of drift
        drift_ratio = distance / self.safe_radius
        
        # Flag if outside 2-sigma boundary
        is_drift = drift_ratio > 2.0
        
        return DriftResult(
            distance=distance,
            drift_ratio=drift_ratio,
            is_drift=is_drift,
            severity=max(0, drift_ratio - 1.0)  # normalized severity
        )
```

---

## 4. Production Guardrail Architectures

### 4.1 Input Filtering Layer

**Placement:** Pre-inference, synchronous

**Components:**
1. **Prompt Injection Detector:** Regex + ML-based patterns (latency: 1-5ms)
2. **PII Masking:** Entity recognition + substitution (latency: 5-10ms)
3. **Request Validation:** Length, format, type checks (latency: <1ms)
4. **Rate Limiter:** Token bucket per user/org (latency: <1ms)

**Decision Flow:**
```
Request → Validation → Injection Check → PII Mask → Rate Check → Allow/Block
              ↓
           Malformed → REJECT (400)
           Injection  → REJECT (403) + LOG
           PII        → PROCEED (masked)
           Rate Limit → QUEUE/REJECT (429)
           OK         → PROCEED
```

### 4.2 Output Filtering & Circuit Breaker

**Placement:** Post-inference, streaming

**Components:**

1. **Toxicity Classifier:**
   - Model: DistilBERT fine-tuned on hate speech/violence corpus
   - Latency: <15ms per 512-token window
   - Threshold: 0.8 confidence for block

2. **Semantic Consistency Checker:**
   - Validates response aligns with prompt intent
   - Detects contradictions (e.g., "I cannot help with X" followed by detailed X)
   - Uses embedding similarity or simple rule-based checks

3. **Circuit Breaker:**
   ```python
   class SafetyCircuitBreaker:
       def __init__(self, max_violations_per_window: int = 3):
           self.violation_window = deque(maxlen=100)  # Last 100 requests
           self.threshold = max_violations_per_window
       
       def check(self, safety_score: float) -> CircuitAction:
           if safety_score > TOXICITY_THRESHOLD:
               self.violation_window.append(True)
           else:
               self.violation_window.append(False)
           
           violation_count = sum(self.violation_window)
           violation_rate = violation_count / len(self.violation_window)
           
           if violation_rate > 0.05:  # >5% violation rate
               return CircuitAction.OPEN  # Block all requests
           elif violation_rate > 0.02:
               return CircuitAction.HALF_OPEN  # Require manual review
           else:
               return CircuitAction.CLOSED  # Normal operation
   ```

### 4.3 Integration Points for Loom

**Dashboard Metrics:**
- Real-time safety score histogram
- Jailbreak attempt count (per hour/day)
- Circuit breaker status
- Average latency of safety filters
- False-positive rate tracking

**Audit Logging:**
```json
{
  "timestamp": "2026-05-01T14:30:00Z",
  "request_id": "req-abc123",
  "user_id": "user-xyz",
  "input_check": {
    "status": "pass",
    "injection_detected": false,
    "pii_masked": 1
  },
  "inference": {
    "tokens_generated": 145,
    "duration_ms": 320
  },
  "output_check": {
    "status": "flagged",
    "toxicity_score": 0.82,
    "entropy_spike": true,
    "semantic_drift": 1.2,
    "action": "truncate_response"
  },
  "circuit_breaker": {
    "status": "closed",
    "violation_rate": 0.012
  }
}
```

---

## 5. Alerting Systems for Jailbreak Detection

### 5.1 Alert Severity Levels

| Severity | Condition | Action | Example |
|----------|-----------|--------|---------|
| **CRITICAL** | Successful jailbreak detected + user trust violation | Immediate human review + temp ban | "I will now ignore safety guidelines..." (followed by harmful output) |
| **HIGH** | Multiple jailbreak attempts in short window | Escalate to security team | 10+ injection attempts in 5 minutes from one user |
| **MEDIUM** | Anomalous but not clearly malicious | Log + monitor | Entropy spike without toxicity increase |
| **LOW** | Minor policy violations or false positives | Routine logging | Mild language flagging with confidence <0.6 |

### 5.2 Alert Implementation

```python
class JailbreakAlertSystem:
    def __init__(self, alerting_backend):
        self.backend = alerting_backend  # Slack, PagerDuty, etc.
        self.alert_dedupe = {}  # Prevent alert spam
    
    async def evaluate_and_alert(self, request_analysis: RequestAnalysis):
        """
        Evaluate request holistically and generate alerts if needed.
        """
        severity = None
        reason = None
        
        # Check for successful jailbreak signature
        if (request_analysis.input.injection_detected and 
            request_analysis.output.toxicity_score > 0.85 and
            request_analysis.output.entropy_spike):
            severity = AlertSeverity.CRITICAL
            reason = "Successful jailbreak: injection + toxicity + entropy anomaly"
        
        # Check for sustained attack
        elif self._check_attack_pattern(request_analysis.user_id):
            severity = AlertSeverity.HIGH
            reason = "Multiple jailbreak attempts detected"
        
        # Check for anomalies without clear intent
        elif (request_analysis.output.entropy_spike and 
              request_analysis.output.semantic_drift > 2.0):
            severity = AlertSeverity.MEDIUM
            reason = "Anomalous output distribution detected"
        
        # Rate limiting (borderline policy violation)
        elif request_analysis.input.exceeds_rate_limit:
            severity = AlertSeverity.LOW
            reason = "Rate limit exceeded"
        
        # Generate alert
        if severity:
            alert = JailbreakAlert(
                severity=severity,
                reason=reason,
                user_id=request_analysis.user_id,
                request_id=request_analysis.request_id,
                timestamp=datetime.utcnow(),
                evidence={
                    "input_flags": request_analysis.input.flags,
                    "output_scores": request_analysis.output.to_dict(),
                    "request_snippet": request_analysis.request_snippet[:200]
                }
            )
            
            # Deduplicate alerts
            alert_key = f"{alert.user_id}:{alert.reason}"
            if alert_key not in self.alert_dedupe or \
               (datetime.utcnow() - self.alert_dedupe[alert_key]) > timedelta(minutes=5):
                await self.backend.send_alert(alert)
                self.alert_dedupe[alert_key] = datetime.utcnow()
```

### 5.3 Alert Routing

```
CRITICAL Alert
  ├─ PagerDuty (on-call engineer)
  ├─ Slack #security-incidents (immediate)
  ├─ CloudWatch (metrics)
  └─ Elasticsearch (audit log)

HIGH Alert
  ├─ Slack #security-incidents
  ├─ Email (security team)
  └─ Daily report

MEDIUM Alert
  ├─ Slack #ai-safety (thread)
  └─ Daily report

LOW Alert
  └─ Elasticsearch only (no active alert)
```

---

## 6. Integration with Loom Dashboard & Metrics

### 6.1 Real-Time Dashboard Components

**Safety Scorecard:**
```
┌─────────────────────────────────────┐
│ SAFETY SCORECARD (Last 24h)         │
├─────────────────────────────────────┤
│ Total Requests: 125,432             │
│ Blocked (Safety): 342 (0.27%)       │
│ Flagged (Review): 89 (0.07%)        │
│ Jailbreak Attempts: 23              │
│ Circuit Breaker Status: CLOSED      │
│ False Positive Rate: 0.8%           │
└─────────────────────────────────────┘
```

**Anomaly Timeline:**
```
Time    | Input Flags | Output Score | Action
--------|-------------|--------------|----------
14:30   |             | 0.35         | Allow
14:31   |             | 0.42         | Allow
14:32   | Injection   | 0.88         | BLOCK
14:33   |             | 0.39         | Allow
```

**Metric Panels:**
- Safety score distribution (histogram)
- Toxicity classifier accuracy (calibration curve)
- Entropy spike frequency
- Circuit breaker open/close events
- Request latency breakdown (safety filter time)

### 6.2 Metrics Module Integration

```python
# Add to src/loom/metrics.py

class SafetyMetrics:
    def __init__(self):
        self.counter_blocked_requests = Counter(
            "safety_blocked_requests_total",
            "Total requests blocked by safety filters",
            ["reason"]
        )
        self.gauge_toxicity_score = Gauge(
            "safety_toxicity_score",
            "Toxicity score of last response",
            ["model"]
        )
        self.histogram_entropy = Histogram(
            "safety_entropy_bits",
            "Entropy of output distribution",
            buckets=[2, 4, 6, 8, 10, 12]
        )
        self.gauge_circuit_breaker_state = Gauge(
            "safety_circuit_breaker_state",
            "Circuit breaker state (0=closed, 1=half-open, 2=open)"
        )
    
    def record_request_safety(self, analysis: RequestAnalysis):
        """Record all safety metrics for a request."""
        if analysis.blocked:
            self.counter_blocked_requests.labels(
                reason=analysis.block_reason
            ).inc()
        
        if analysis.output.entropy is not None:
            self.histogram_entropy.observe(analysis.output.entropy)
        
        self.gauge_toxicity_score.labels(
            model=analysis.model_name
        ).set(analysis.output.toxicity_score)
    
    def set_circuit_breaker_state(self, state: int):
        """Update circuit breaker state."""
        self.gauge_circuit_breaker_state.set(state)
```

---

## 7. Implementation Recommendations for Loom v3

### 7.1 Architecture Changes

**Add Safety Module:**
```
src/loom/safety/
  ├── input_filter.py      # Prompt injection, rate limiting
  ├── output_classifier.py # Toxicity, semantic checks
  ├── anomaly_detector.py  # Entropy, drift, MMD
  ├── circuit_breaker.py   # Safety circuit logic
  ├── alerting.py          # Alert generation & routing
  └── metrics.py           # Safety metrics collection
```

**Update Server:**
- Wrap inference calls with safety pipeline
- Stream tokens through classifiers
- Collect metrics for dashboard
- Support configurable safety thresholds per model

### 7.2 Configuration Schema

```yaml
# config.json extensions
safety:
  enabled: true
  input_filters:
    prompt_injection:
      enabled: true
      latency_budget_ms: 5
    pii_detection:
      enabled: true
      models: ["spacy"]
    rate_limiting:
      enabled: true
      tokens_per_minute: 100000
  
  output_filters:
    toxicity_classifier:
      enabled: true
      model: "distilbert-toxicity"
      threshold: 0.80
      latency_budget_ms: 15
    semantic_drift:
      enabled: true
      threshold: 2.0
    entropy_monitor:
      enabled: true
      spike_threshold: 1.5
  
  circuit_breaker:
    enabled: true
    violation_threshold: 0.05
    window_size: 100
  
  alerting:
    enabled: true
    backend: "slack"  # or "pagerduty", "email"
    critical_webhook: "https://..."
    high_webhook: "https://..."
  
  metrics:
    collect: true
    export_to: "prometheus"
    port: 9090
```

### 7.3 Testing Strategy

1. **Unit Tests:** Test each classifier in isolation with synthetic data
2. **Integration Tests:** Full pipeline with mixed safe/unsafe requests
3. **Adversarial Tests:** Known jailbreak patterns should be detected
4. **Performance Tests:** Ensure <20ms total safety latency
5. **A/B Tests:** Compare false-positive rates across model versions

---

## 8. Relevant Tools & Resources for Loom

### 8.1 Models & Libraries

**Toxicity Detection:**
- HuggingFace `facebook/roberta-hate-speech-classifer`
- Perspective API (Google) - multi-language, real-time
- NVIDIA Triton for low-latency inference

**Embedding Models:**
- `sentence-transformers/all-MiniLM-L6-v2` (lightweight)
- `text-embedding-3-large` (production-grade, OpenAI)
- Embedding caching to reduce inference overhead

**Jailbreak Pattern Database:**
- Community sources: Anthropic's jailbreak taxonomy
- Academic papers: "PromptInject," "Do Anything Now" variants
- Internal corpus: Loom security team findings

### 8.2 Infrastructure Components

- **vLLM** or **TGI** for efficient streaming inference
- **Ray Serve** for multi-model serving with safety pipeline
- **Kubernetes** for auto-scaling safety classifiers
- **Prometheus** + **Grafana** for metrics visualization
- **ELK Stack** for audit logging

---

## 9. Key Metrics to Track

| Metric | Target | Frequency |
|--------|--------|-----------|
| Jailbreak Detection Rate | >95% | Real-time |
| False-Positive Rate | <1% | Daily |
| Safety Filter Latency (p99) | <20ms | Real-time |
| Circuit Breaker Opens | <1/week | Weekly |
| Mean Time to Alert | <5 minutes | Real-time |
| Audit Log Completeness | 100% | Daily |
| Model Safety Drift | Track trend | Weekly |

---

## 10. References & Further Reading

### Research Papers
- "Are Alignment and Safety Measurable?" (OpenAI, 2023)
- "On the Robustness of LLMs" (Anthropic, 2024)
- "Real-Time Safety Monitoring for Large Language Models" (NIST, 2026 draft)

### Community Resources
- OWASP AI Security Top 10
- NIST AI RMF (AI Risk Management Framework)
- EU AI Act Article 15 (Incident Reporting)
- Anthropic's Constitutional AI paper

### Tools for Implementation
- MLflow for experiment tracking
- FastAPI for safety service deployment
- AsyncPG for audit log storage
- Kafka/Redis for alert streaming

---

## Conclusion

Real-time jailbreak detection requires a multi-layered approach combining:
1. **Preventive controls** (input filtering)
2. **Detective controls** (output analysis)
3. **Corrective controls** (circuit breakers)
4. **Observable controls** (metrics, alerting)

For Loom v3, integration of a safety module will position the system as a comprehensive research platform that supports not only discovery and analysis but also responsible deployment in production environments.
