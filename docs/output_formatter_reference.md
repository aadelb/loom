# Output Formatter Tools Reference

## Overview

The output formatter tools provide structured processing and extraction of data from raw text, LLM outputs, and unstructured documents. These tools are essential for:

- Converting raw LLM responses into structured formats
- Extracting actionable items from research outputs
- Organizing project plans, proposals, and reports
- Standardizing output across different sources

## Tools

### 1. research_format_report

Formats raw unstructured text into structured reports with multiple output formats.

**Parameters:**

```python
raw_text: str          # Raw unstructured text or LLM output
format: str = "json"   # Output format: "json", "markdown", "executive_brief", "technical_spec"
```

**Output Format:**

```json
{
  "formatted": {},             # Formatted content (structure depends on format param)
  "format": "json",            # The format that was applied
  "sections_extracted": [],    # List of sections found in input
  "word_count": 0              # Total words in input
}
```

**Supported Formats:**

#### JSON Format (Default)

Extracts and structures sections into a dictionary:

```json
{
  "executive_summary": "...",
  "methodology_steps": ["step 1", "step 2", ...],
  "tools_required": ["tool1", "tool2", ...],
  "timeline": "3 months",
  "cost_breakdown": [
    {
      "currency": "$",
      "amount": 5000,
      "unit": "USD",
      "description": "Development"
    }
  ],
  "risk_assessment": ["risk1", "risk2", ...],
  "sources": ["source1", "source2", ...]
}
```

#### Markdown Format

Converts sections to markdown with headers and bullet points:

```markdown
## Executive Summary
...

## Methodology
...

## Tools Required
...
```

#### Executive Brief Format

Condensed text summary with key highlights:

```
**Summary:** [truncated executive summary]
**Tools Required:** [top 5 tools]
**Timeline:** [timeline info]
**Total Cost:** [$currency amount]
**Key Risks:** [top 3 risks]
```

#### Technical Spec Format

Dictionary with sections formatted for technical reference:

```json
{
  "executive_summary": "...",
  "methodology": ["step1", "step2", ...],
  "tools_required": ["tool1", "tool2", ...],
  "cost_breakdown": [{"description": "...", ...}],
  "risk_assessment": ["risk1", "risk2", ...]
}
```

**Examples:**

```python
# Format as JSON (default)
result = research_format_report("""
Executive Summary: Platform redesign project overview
Methodology:
1. Conduct user research
2. Create wireframes
3. Build prototypes
Tools Required:
- Figma
- React
- Node.js
Cost Breakdown:
$50000 for development
$10000 for design
""")

# Format as markdown
result = research_format_report(raw_text, format="markdown")

# Format as executive brief (condensed)
result = research_format_report(raw_text, format="executive_brief")

# Format as technical specification
result = research_format_report(raw_text, format="technical_spec")
```

**Automatic Section Detection:**

The tool automatically detects common sections:
- Executive Summary, Overview, Summary
- Methodology, Approach, Method
- Tools, Tools Required
- Timeline, Timeframe, Schedule
- Cost, Costs, Budget, Pricing
- Risk, Risks, Limitations, Challenges
- Sources, References, Citations

**Cost Extraction:**

Automatically extracts monetary values with currency:

```text
Input:  "$5000 for development"
Output: {
  "currency": "$",
  "amount": 5000,
  "unit": "USD",
  "description": "Development"
}
```

Supported currencies: $, €, £, ¥, ₹

---

### 2. research_extract_actionables

Extracts actionable items from any text including actions, tools, timelines, costs, and risks.

**Parameters:**

```python
text: str  # Input text of any format
```

**Output Format:**

```json
{
  "actions": [],              # Extracted action items
  "tools_needed": [],         # Mentioned tools and technologies
  "timeline_items": [],       # Timeline entries and durations
  "costs": [],                # Cost items with monetary values
  "risks": []                 # Risk and limitation items
}
```

**Action Extraction:**

Extracts multiple types of action indicators:
- TODO, FIXME, ACTION, MUST, SHOULD keywords
- Numbered items (1., 2), 3:, etc.)
- Bulleted items (-, *, •)
- Imperative verbs suggesting actions

```python
text = """
TODO: Fix authentication module
1. Review requirements
2. Create design document
- Set up environment
ACTION: Schedule meeting
"""

result = research_extract_actionables(text)
# result["actions"] = [
#   "Fix authentication module",
#   "Review requirements",
#   "Create design document",
#   "Set up environment",
#   "Schedule meeting"
# ]
```

**Tool Extraction:**

Identifies tools, frameworks, libraries, and technologies:

```python
text = """
We will use Python 3.11, FastAPI, and PostgreSQL.
Tools Required:
- Docker
- Kubernetes
- Redis
"""

result = research_extract_actionables(text)
# result["tools_needed"] includes Python, FastAPI, PostgreSQL, Docker, Kubernetes, Redis
```

**Timeline Extraction:**

Extracts dates and durations:

```python
text = """
Timeline:
Start: 2025-01-15
Deadline: 2025-06-30

Phase 1: 2 weeks
Phase 2: 3 months
Phase 3: 4 weeks
"""

result = research_extract_actionables(text)
# result["timeline_items"] = [
#   {"time": "2025-01-15", "description": ""},
#   {"time": "2025-06-30", "description": ""},
#   {"time": "2 weeks", "description": ""},
#   ...
# ]
```

**Cost Extraction:**

Automatically detects monetary amounts:

```python
text = """
Budget:
$5000 - Development
€2500 - Infrastructure
£1000 - Testing

Total: $8500
"""

result = research_extract_actionables(text)
# result["costs"] = [
#   {"currency": "$", "amount": 5000, "unit": "USD", "description": "Development"},
#   {"currency": "€", "amount": 2500, "unit": "USD", "description": "Infrastructure"},
#   ...
# ]
```

**Risk Extraction:**

Identifies risk statements and limitations:

```python
text = """
Risk Assessment:
- Resource constraints may impact timeline
- Technical complexity could cause delays

Challenges:
Integration with legacy systems
Training requirements for team
"""

result = research_extract_actionables(text)
# result["risks"] includes all risk items mentioned
```

**Examples:**

```python
# Comprehensive extraction
result = research_extract_actionables("""
PROJECT PLAN

Actions:
1. Create project board
2. Assign team members

TODO: Configure monitoring

Tools: Python, Docker, Jenkins

Timeline: Q1 2025 - Q2 2025

Costs:
$10000 - Infrastructure
€5000 - Training

Risks:
- Unknown dependencies
- Integration issues
""")

# All lists will be populated
print(f"Actions: {len(result['actions'])}")      # 4+
print(f"Tools: {len(result['tools_needed'])}")    # 3+
print(f"Timeline: {len(result['timeline_items'])}")  # 2+
print(f"Costs: {len(result['costs'])}")           # 2+
print(f"Risks: {len(result['risks'])}")           # 2+
```

---

## Usage Patterns

### Pattern 1: LLM Output Processing

```python
# Get raw output from LLM
llm_response = model.generate(prompt)

# Format into structured report
report = research_format_report(llm_response, format="json")

# Extract actionables for execution
actionables = research_extract_actionables(llm_response)

# Use formatted report and actionables for next steps
implementation_plan = report["formatted"]
tasks = actionables["actions"]
```

### Pattern 2: Project Planning

```python
# Parse raw project proposal
proposal = research_format_report(proposal_text, format="json")

# Extract actionable tasks
tasks = research_extract_actionables(proposal_text)

# Create task board with extracted actions
for action in tasks["actions"]:
    create_task(action)

# Set budget from cost breakdown
total_cost = sum(c["amount"] for c in proposal["formatted"]["cost_breakdown"])
```

### Pattern 3: Report Generation

```python
# Collect research outputs from multiple sources
raw_outputs = [output1, output2, output3]

# Format each into markdown
formatted_outputs = [
    research_format_report(output, format="markdown")
    for output in raw_outputs
]

# Compile final report
final_report = "\n".join([
    output["formatted"]
    for output in formatted_outputs
])
```

### Pattern 4: Risk Assessment

```python
# Extract risks from project documents
risks = research_extract_actionables(project_doc)["risks"]

# Analyze timeline constraints
timeline = research_format_report(project_doc, format="json")["formatted"]["timeline"]

# Assess resource requirements
costs = research_extract_actionables(project_doc)["costs"]

# Create risk mitigation plan
mitigation = assess_risks(risks, timeline, costs)
```

---

## Implementation Details

### Text Pattern Matching

The tools use regex patterns to detect:

- **Numbered steps:** `1.`, `1)`, `1:` patterns
- **Bulleted items:** `-`, `*`, `•`, `·` markers
- **Dates:** ISO dates, MM/DD/YYYY, relative dates
- **Durations:** "2 weeks", "3 months", "4 days"
- **Currencies:** $, €, £, ¥, ₹ with amounts
- **Action keywords:** TODO, FIXME, ACTION, MUST, SHOULD
- **Section headers:** Common headings and labels

### Section Detection

Automatically identifies sections by looking for:

- Section header patterns (case-insensitive)
- Colon-separated labels
- Common section boundaries
- Content delineation

### Deduplication

All extracted lists are deduplicated while preserving order:

```python
# Input: ["Python", "Docker", "Python", "Node.js"]
# Output: ["Python", "Docker", "Node.js"]
```

### Monetary Value Parsing

Supports:

```python
$5000
$50,000
$5000.50
€2500
£1000
¥100000
₹500000
```

---

## Performance

- **Execution time:** < 100ms for typical documents (< 10KB)
- **Memory usage:** Minimal (regex-based, no ML models)
- **Scalability:** Handles documents up to 1MB without issues

---

## Error Handling

All tools are designed to be fault-tolerant:

- Missing sections return empty strings or empty lists
- Malformed data is skipped gracefully
- Invalid monetary amounts are ignored
- No exceptions thrown on unusual input

**Example:**

```python
# Even with minimal input, returns valid structure
result = research_extract_actionables("just plain text")
# result = {
#   "actions": [],
#   "tools_needed": [],
#   "timeline_items": [],
#   "costs": [],
#   "risks": []
# }
```

---

## Troubleshooting

### No sections detected in structured text

- Ensure section headers match expected patterns
- Try alternative section headers (e.g., "Overview" instead of "Executive Summary")
- Check for typos in section labels

### Costs not extracted

- Verify currency symbol is recognized ($, €, £, ¥, ₹)
- Ensure amount immediately follows currency symbol
- Check that description comes after the amount

### Actions extracted are too generic

- Use action keywords (TODO, FIXME, ACTION)
- Provide numbered or bulleted lists
- Use imperative verbs in descriptions

### Tools list includes non-tool items

- This is expected behavior for capitalized terms
- Filter results if needed in your application
- Provide explicit "Tools:" section for reliable detection

---

## Cost Estimation

Both tools are free to use (no external API calls):

- No LLM inference
- No external service calls
- Pure text processing using standard Python regex
- Zero cost beyond basic CPU usage

---

## Integration Examples

### With LLM Pipeline

```python
def process_llm_research(query, llm_model):
    # Generate research with LLM
    raw_output = llm_model.generate(f"Research: {query}")
    
    # Format into structured report
    report = research_format_report(raw_output, format="json")
    
    # Extract executable items
    actionables = research_extract_actionables(raw_output)
    
    return {
        "structured": report["formatted"],
        "actions": actionables["actions"],
        "tools": actionables["tools_needed"],
        "timeline": report["formatted"]["timeline"],
        "costs": actionables["costs"]
    }
```

### With Project Management Tools

```python
def import_proposal_to_jira(proposal_text):
    # Extract actionables
    items = research_extract_actionables(proposal_text)
    
    # Create Jira tasks
    for action in items["actions"]:
        jira.create_issue(
            summary=action,
            labels=["imported"]
        )
    
    # Set budget
    costs = items["costs"]
    total = sum(c["amount"] for c in costs)
    jira.set_budget(total)
```

---

## Related Tools

- `research_deep`: Deep research with LLM extraction
- `research_search`: Multi-provider search
- `llm`: LLM-powered summarization and analysis
- `report_generator`: Create structured intelligence reports
