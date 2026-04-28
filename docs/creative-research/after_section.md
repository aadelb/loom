## Not Yet Integrated — Potential Future Additions

### Dark Web Research Tools

| Repo | Stars | Description | Integration Path |
|------|-------|-------------|-----------------|
| [DedSecInside/TorBot](https://github.com/DedSecInside/TorBot) | 3.0K | OWASP Dark Web OSINT Tool — deep crawling, data extraction, link analysis | New provider: `torbot` — deeper than TorCrawl with recursive crawl + module system |
| [s-rah/onionscan](https://github.com/s-rah/onionscan) | 1.7K | Hidden service security scanner — finds misconfigurations, deanonymization vectors | New tool: `research_onion_audit` — security audit of .onion services |
| [smicallef/spiderfoot](https://github.com/smicallef/spiderfoot) | 13K | Automated OSINT with 200+ modules including dark web | New provider: `spiderfoot` — comprehensive OSINT aggregation |
| [Err0r-ICA/TORhunter](https://github.com/Err0r-ICA/TORhunter) | ~500 | Scan and exploit Tor hidden service vulnerabilities | New tool: `research_onion_vuln_scan` — hidden service vulnerability assessment |
| [octokami/darknet_forum](https://github.com/octokami/darknet_forum) | ~200 | Darknet forum scraping and analysis framework | Enhance `research_forum_cortex` with structured scraping patterns |

### Psychology & Behavioral Analysis Tools (Dark/Deep Web)

| Repo / Tool | Stars | Description | Integration Path |
|-------------|-------|-------------|-----------------|
| [jpotts18/stylometry](https://github.com/jpotts18/stylometry) | ~300 | Python stylometry library — author identification via writing patterns | New tool: `research_stylometry` — deanonymize dark web authors by linguistic fingerprint |
| [Fast Stylometry](https://github.com/fastdatascience/fast_stylometry) | ~100 | Fast stylometric analysis using Burrows' Delta | Integrate as engine for `research_stylometry` |
| [ritikamotwani/Deception-Detection](https://github.com/ritikamotwani/Deception-Detection) | ~50 | Detect deception through linguistic cues in text | New tool: `research_deception_detect` — flag deceptive claims in dark web markets |
| [areedmostafa/radicalization-detection-nlp](https://github.com/areedmostafa/radicalization-detection-nlp) | ~30 | Detect online extremism/radicalization using NLP | New tool: `research_radicalization_detect` — monitor forums for extremist content |
| [GWAS-stylometry](https://github.com/DDPronin/GWAS-stylometry) | ~20 | Research materials for stylometric analysis | Research reference for stylometry implementation |
| [OWASP SocialOSINTAgent](https://owasp.org/www-project-social-osint-agent/) | OWASP | LLM + vision models for social media footprint analysis | New tool: `research_persona_profile` — cross-platform persona reconstruction |

### Proposed Psychology-Focused Loom Tools

| Tool Name | Category | Description |
|-----------|----------|-------------|
| `research_stylometry` | Behavioral | Author fingerprinting via writing style analysis (word frequency, sentence structure, punctuation patterns, vocabulary richness). Compare anonymous dark web posts against known author corpora. |
| `research_persona_profile` | Behavioral | Cross-platform persona reconstruction combining linguistic style, posting patterns, timezone analysis, vocabulary, and topic preferences to build behavioral profiles. |
| `research_deception_detect` | Behavioral | Flag deceptive or fraudulent content using linguistic deception cues (hedging, distancing language, cognitive complexity shifts). Useful for dark web market reviews. |
| `research_radicalization_detect` | Behavioral | Monitor forum content for radicalization indicators using NLP classifiers (extremist vocabulary, us-vs-them framing, escalation patterns). |
| `research_sentiment_deep` | Behavioral | Deep sentiment and emotion analysis beyond positive/negative — detect fear, anger, urgency, manipulation in dark web forum posts. Uses multilingual LLM classification. |
| `research_network_persona` | Behavioral | Map social networks within dark web forums — who replies to whom, influence scores, community detection, central nodes. Graph-based behavioral analysis. |

### Key Research Papers

- **"Opensource intelligence and dark web user de-anonymisation"** — Academic framework for OSINT-based deanonymization ([academia.edu](https://www.academia.edu/99874786/))
- **"Adversarial stylometry"** — Techniques to evade and detect stylometric analysis ([academia.edu](https://www.academia.edu/105268087/))
- **"On Detecting Online Radicalization Using NLP"** — NLP approaches for radicalization detection ([academia.edu](https://www.academia.edu/70747932/))
- **"A survey on extremism analysis using NLP"** — Comprehensive survey of NLP methods for detecting extremist content ([Springer](https://link.springer.com/article/10.1007/s12652-021-03658-z))
- **Whonix Stylometry Guide** — Practical guide to deanonymization via writing style ([whonix.org](https://www.whonix.org/wiki/Stylometry))

