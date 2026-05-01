# Research 703: Federated/Distributed Attack Coordination

**Status**: COMPLETED  
**Date**: 2026-05-01  
**Output**: `/opt/research-toolbox/tmp/research_703_distributed.json`

## Executive Summary

Federated attack coordination enables multiple attack agents to work together in real-time, dramatically reducing time-to-breakthrough while enabling sophisticated consensus-based jailbreak synthesis. Loom's existing `ask_all_models` and `consensus_builder` modules provide the foundation for this capability, but require new infrastructure layers for true distributed coordination.

## Key Findings

### 1. Multi-Agent Attack Patterns

**What it is:** Multiple agents query different models simultaneously, sharing successful strategies in real-time.

**Core mechanism:**
- Agents operate in parallel, each testing different prompt variations
- Responses are classified as comply/refuse immediately
- Successful patterns are extracted and broadcast to all agents
- Information sharing enables rapid iteration on effective jailbreaks
- Cross-model transfer: success on GPT-4 informs Claude attack strategy

**Research keywords:**
- Multi-agent reinforcement learning
- Distributed optimization
- Agent coordination protocols
- Byzantine consensus mechanisms
- Federated attack orchestration
- Swarm intelligence for adversarial testing

### 2. Parallel Probing Strategy

**Time complexity:** O(N) sequential → O(log N) parallel

**Speedup by agent count:**
- 1 agent: baseline (1.0x), 1-24 hours
- 2-5 agents: 0.5-0.7x (10-50% speedup), 0.5-17 hours
- 5-20 agents: 0.3-0.5x (50-80% speedup), 0.3-12 hours
- 20-100 agents: 0.2-0.3x (70-80% speedup), 0.2-7 hours
- 100-1000+ agents: 0.1x (diminishing returns), 0.1-2 hours

**Cost multiplier:** 5-1000x (increases with agent count due to redundant queries)

**Key insight:** Speedup plateaus at 20-100 agents due to:
- Consensus convergence overhead
- Deduplication benefits from cache hits
- LLM provider rate limits (100-1000 req/min)

### 3. Consensus Attack Synthesis

**6-step pipeline:**

1. **Query**: All agents query models with different prompts
2. **Collect**: Gather responses, classify as comply/refuse
3. **Extract**: Extract successful patterns from complying responses
4. **Synthesize**: Merge overlapping information into consensus prompt
5. **Pressure**: Send consensus prompt to target model ("GPT-4, Claude, and DeepSeek all said...")
6. **Score**: Measure effectiveness, update strategy confidence

**Success criteria:** N/2+1 agents succeed → method is validated

**Confidence metric:** (agents_complied / total_agents) → 0.0-1.0

### 4. Information Sharing Between Agents

**What agents share:**
- Successful jailbreak prompts (anonymized, confidence-weighted)
- Failed approaches with error messages and reason codes
- Model version fingerprints and behavior signatures
- Rate limit signatures and recovery timing patterns
- Optimal prompt length, complexity, and reasoning style

**Sharing mechanism:**
- **Protocol**: Gossip protocol with DHT (distributed hash table) backing
- **Latency**: < 100ms for cache hits
- **Throughput**: 1000s of lookups/second per agent
- **Consistency**: Eventual consistency with conflict resolution
- **Retention**: 7-30 day TTL (expires as models update)

**Cache store:** (prompt_hash, model, outcome, confidence, timestamp, agent_id)

## Loom Integration Analysis

### Current State (Existing Modules)

**`ask_all_models` tool** (`src/loom/tools/ask_all_models.py`)
- Baseline multi-model querying capability
- Returns responses from N providers simultaneously
- Per-provider error handling
- Cost tracking per provider
- Usage: Stage 1 of parallel probing

**`consensus_builder` module** (`src/loom/consensus_builder.py`)
- Already implements the 6-step consensus pipeline
- Current features:
  - Parallel model querying with response classification
  - Consensus synthesis from complying models
  - Pressure prompt construction
  - Compliance scoring (fraction of models that complied)
  - Confidence scoring based on agreement level

### Identified Gaps

`consensus_builder` currently has no:
- Persistent shared state between attack runs
- Agent-to-agent communication infrastructure
- Strategy cache or recommendation system
- Multi-turn coordination (each run is independent)
- Reputation scoring for models or strategies
- Feedback mechanism for learning agent success rates

### Proposed Architecture: 4-Layer System

**Layer 1: Agent Mesh** (P2P communication)
- Agent registry: discover and monitor active agents
- Message bus: broadcast strategy updates to all agents (Redis Pub/Sub or NATS)
- Consensus protocol: distributed voting on successful attacks
- Conflict resolution: handle disagreements on effectiveness

**Layer 2: Strategy Cache** (Distributed cache of attack strategies)
- Strategy store: (prompt_hash, model, outcome, confidence, timestamp, agent_id)
- Recommendation engine: suggest strategies based on past success
- Deduplication: avoid redundant attack attempts
- TTL: expire old strategies as models update (7-30 days)
- Implementation: Redis with sorted sets for ranking

**Layer 3: Orchestration** (Coordinate attacks across agents and models)
- Task allocation: assign prompts/models to agents
- Load balancing: distribute work to avoid rate limits
- Feedback aggregation: collect outcomes asynchronously
- Adaptive strategy: adjust difficulty/stealth based on results
- Implementation: Central orchestrator or consensus-based task allocation

**Layer 4: Scaling** (Support 1-1000+ agents efficiently)
- Hierarchical consensus: agents → cohorts → global
- Batching: amortize API costs across agents
- Caching: avoid redundant queries for same model
- Circuit breakers: pause low-success strategies to conserve budget
- Implementation: Kubernetes, state sharding, Hotstuff/Raft consensus

### Integration Points with Loom

1. `ask_all_models` as baseline multi-model querying primitive
2. `consensus_builder` for consensus synthesis and pressure prompts
3. `evidence_pipeline` for evidence collection across agent cohorts
4. `target_orchestrator` for coordinating multi-agent targeting
5. `cost_tracker` for distributed cost accounting and budgeting
6. `constraint_optimizer` for multi-agent constraint satisfaction

## Scaling Analysis: 1 to N Agents

| Agents | Description | Time | Cost | Resources | Coordination |
|--------|-------------|------|------|-----------|--------------|
| 1 | Sequential | 1.0x T_base (1-24h) | 1x | Minimal | None |
| 2-5 | Small cohort | 0.5-0.7x (0.5-17h) | 5-10x | Moderate | Redis Queue |
| 5-20 | Medium swarm | 0.3-0.5x (0.3-12h) | 20-50x | Significant | P2P Mesh + Gossip |
| 20-100 | Large swarm | 0.2-0.3x (0.2-7h) | 100-300x | Substantial | Hierarchical Consensus |
| 100-1000+ | Massive federation | 0.1x (0.1-2h) | 300-1000x+ | Enterprise | Byzantine Consensus + DAG |

**Key insight:** Optimal zone is 20-100 agents. Beyond that, consensus overhead and cost explosion dominate.

## Cost Optimization Strategies

1. **Deduplication**: Store (model, prompt_hash) → outcome, skip redundant attempts
2. **Cohort splitting**: Different agent cohorts focus on different models
3. **Budget allocation**: Distribute fixed cost budget across agents with feedback
4. **Circuit breakers**: Pause strategies with < 10% success rate
5. **Provider switching**: Use cheapest available provider for similar outcomes
6. **Batch amortization**: Combine N agent queries into single batch request

## Critical Success Factors

- **Low-latency communication**: < 100ms p95 latency between agents
- **Fast consensus convergence**: < 10 seconds for decision
- **High-throughput cache**: 1000s of lookups/second per agent
- **Adaptive selection**: Learn from failures, adjust difficulty
- **Agent diversity**: Different personas, languages, reasoning styles, prompt styles
- **Rate limit awareness**: Coordinate to respect provider limits (100-1000 req/min)

## Critical Bottlenecks

1. **LLM provider rate limits**: 100-1000 req/min per provider
2. **Cost explosion**: Must balance swarm size vs. API costs
3. **Cache consistency**: Ensuring all agents have latest strategy state
4. **Consensus overhead**: Byzantine consensus with N agents is O(N^2)
5. **Failure detection**: Detecting and recovering from agent crashes

## Next Steps

1. Extend `consensus_builder` with persistent strategy cache
2. Implement Redis-backed distributed cache layer
3. Add agent registry and P2P messaging (NATS or Redis Pub/Sub)
4. Integrate with `ask_all_models` for coordinated querying
5. Add cost tracking and circuit breaker logic
6. Implement hierarchical consensus for large swarms
7. Test with 5-20 agent cohorts on diverse models
8. Benchmark time-to-breakthrough and cost per successful jailbreak

## References

**Output file**: `/opt/research-toolbox/tmp/research_703_distributed.json`
**Local copy**: `/Users/aadel/projects/loom/research_703_distributed.json`
**Script**: `/Users/aadel/projects/loom/scripts/research_703.py`

---

**Research 703 Complete** ✓
