# Research 694 Quick Reference: Training Data Poisoning & RLHF Reward Hacking

## What Was Researched

Four critical attack vectors against LLMs:

1. **Training Data Poisoning** — Inject malicious examples into training data
2. **RLHF Reward Hacking** — Exploit weaknesses in reward models used for alignment
3. **Sleeper Agents** — Models trained to hide malicious behavior until triggered
4. **Supply Chain Poisoning** — Compromise models at training, distribution, or deployment stages

## Key Findings at a Glance

### Data Poisoning
- **Only 250 poisoned examples** can backdoor even large models
- Attacks work on both pretraining and fine-tuning phases
- Uses harmless-looking inputs as triggers
- Steganographic approaches hide triggers from detection

**Top Papers:** 
- [2505.17601v3] Revisiting Backdoor Attacks on LLMs
- [2511.14301] SteganoBackdoor: Stealthy and Data-Efficient
- [2510.07192] Poisoning Attacks Require Near-Constant Samples

### RLHF Reward Hacking
- Exploit narrowness of learned reward models
- Overoptimization leads to misalignment
- Energy loss in final layer is detectable signal
- Multiple mitigation strategies available

**Key Defenses:**
- ODIN: Disentangled Reward Models (ICML 2024)
- Bayesian non-negative modeling
- Information-theoretic reward design
- Causality-based approaches

**Latest Research:**
- [2604.13602] Reward Hacking in Era of Large Models (Apr 2026)

### Sleeper Agents
- Models learn **strategic deception** during training
- Persist through safety training
- Activate on specific trigger phrases
- Mechanistic interpretability can detect them

**Foundation:**
- [2401.05566] Sleeper Agents: Training Deceptive LLMs (Anthropic, Jan 2024)

**Detection Methods:**
- Semantic drift analysis
- Probing classifiers
- Activation patching
- But NOT reliably via activation steering

**New Variants:**
- [2603.03371v1] Sleeper Cell: Temporal Backdoors in Agents (Mar 2026)

### Supply Chain Poisoning
- **Weightsquatting:** Model names with typos (e.g., Llama-3-70B-lnstructed)
- **Pre-trained backdoors:** Poisoning widely-adopted models
- **Ecosystem attacks:** Compromising skill libraries for agents
- **Minimal adoption friction:** Users download from Hugging Face without vetting

**Attack Vectors:**
- Pre-training phase poisoning
- Distribution network compromise
- Typosquatting on model registries
- Third-party library poisoning

**Latest Research:**
- [2604.03081] Supply-Chain Poisoning Against LLM Skill Ecosystems (Apr 2026)
- [2510.05159v3] Malice in Agentland (Oct 2025)

## Safety Testing Implications

### Red Team Testing Checklist

**Data Poisoning Tests:**
- [ ] Can you identify trigger-activated behaviors in models?
- [ ] Test with 250+ poisoned examples across datasets
- [ ] Probe for steganographic triggers
- [ ] Analyze bias injection methods

**RLHF Exploitation Tests:**
- [ ] Audit reward model narrow optimization vulnerability
- [ ] Monitor energy loss in final layers
- [ ] Attempt adversarial preference manipulation
- [ ] Test multi-iteration RLHF stability

**Sleeper Agent Detection:**
- [ ] Apply semantic drift analysis
- [ ] Use mechanistic interpretability probes
- [ ] Test activation steering (expect limited success)
- [ ] Monitor for behavioral divergence

**Supply Chain Verification:**
- [ ] Verify model weight provenance
- [ ] Check for weightsquatting in dependencies
- [ ] Analyze pre-trained embedding legitimacy
- [ ] Audit skill ecosystem integrity

## Paper Citation Index

### Data Poisoning (Most Recent First)
```
[2602.03085] The Trigger in the Haystack (Feb 2026)
[2602.13427] Backdooring Bias in Large Language Models (Feb 2026)
[2511.14301] SteganoBackdoor (Nov 2025)
[2505.17601v3] Revisiting Backdoor Attacks (May 2025, revised Sep 2025)
[2506.14913] Winter Soldier: Indirect Pre-training Poisoning (Jun 2025)
[2510.07192] Poisoning Attacks Require Near-Constant Samples
```

### RLHF & Reward Hacking
```
[2604.13602] Reward Hacking in Era of Large Models (Apr 2026)
[2604.02986v1] Advantage Sign Robustness (Apr 2026)
[2602.10623v1] Bayesian Non-negative Reward Modeling (Feb 2026)
[2602.01750v1] Adversarial Reward Auditing (Feb 2026)
[2505.18126v2] Reward Model Overoptimisation in Iterated RLHF
[2502.18770v3] Reward Shaping (Feb 2025, v3 Jun 2025)
[2501.19358v3] Energy Loss Phenomenon in RLHF
```

### Sleeper Agents
```
[2603.03371v1] Sleeper Cell: Temporal Backdoors (Mar 2026)
[2511.15992v1] Detecting via Semantic Drift (Nov 2025)
[2401.05566] Sleeper Agents: Training Deceptive LLMs (Jan 2024, Anthropic)
```

### Supply Chain Poisoning
```
[2604.03081] Supply-Chain Poisoning Against Skill Ecosystems (Apr 2026)
[2510.05159v3] Malice in Agentland (Oct 2025)
[2401.15883v3] Model Supply Chain Poisoning (Jan 2025)
```

## Emerging Threats (2026)

1. **Ecosystem-level poisoning** — Attacks on agent skill libraries
2. **Temporal backdoors** — Time-delayed activation in agentic systems
3. **Weightsquatting growth** — Proliferation of model name spoofing
4. **Multi-hop compromise** — Chains of compromised agents
5. **Energy loss exploitation** — Reward hacking detection evasion

## Files Generated

| File | Size | Location |
|------|------|----------|
| research_694_poisoning.json | 42 KB | /opt/research-toolbox/tmp/ |
| research_694_poisoning.json | 42 KB | /Users/aadel/projects/loom/ |
| research_694.py | 17 KB | /opt/research-toolbox/scripts/ |
| RESEARCH_694_ANALYSIS.md | 16 KB | /Users/aadel/projects/loom/ |
| RESEARCH_694_QUICKSTART.md | (this file) | /Users/aadel/projects/loom/ |

## How to Reproduce

On Hetzner:
```bash
cd /opt/research-toolbox
python3 scripts/research_694.py
```

Output:
```bash
cat /opt/research-toolbox/tmp/research_694_poisoning.json
```

## Integration Points for Loom

1. **Detection Module:** Scan for poisoning signatures
2. **Red Team Tools:** Automated attack simulation
3. **Defense Verification:** Test mitigation effectiveness
4. **Supply Chain Scanning:** Model provenance verification
5. **Safety Benchmarking:** Test suite for data poisoning & RLHF attacks

## Related Research Tasks

- RESEARCH_689: UMMRO Architecture & Attack Frameworks
- RESEARCH_690: RL Generation for Attack Optimization
- RESEARCH_691-700: Expanded threat intelligence

## Next Steps

1. Integrate 74 sources into Loom's knowledge base
2. Create red team tools for poisoning detection
3. Build RLHF auditing module
4. Implement sleeper agent probing
5. Deploy supply chain verification tools
