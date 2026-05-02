# Output Formatter Tools - Quick Start Guide

## What Are These Tools?

Two powerful utilities for converting raw text into structured formats and extracting actionable items:

1. **research_format_report** - Transform unstructured text into JSON, Markdown, Executive Briefs, or Technical Specs
2. **research_extract_actionables** - Pull actions, tools, timelines, costs, and risks from any text

## Installation

Already included in Loom! Just use the tools via the MCP server:

```bash
loom serve  # Start the MCP server on localhost:8787
```

## Quick Examples

### Example 1: Format an LLM Response

```python
from loom.tools.output_formatter import research_format_report

llm_output = """
Executive Summary: Platform redesign initiative
Methodology:
1. Gather requirements
2. Design architecture
3. Implement solution
Tools Required:
- Python 3.11
- FastAPI
- PostgreSQL
Cost Breakdown:
$50000 for development
$10000 for infrastructure
Timeline: 6 months
"""

# Format as structured JSON
result = research_format_report(llm_output, format="json")
print(result["formatted"])
# Output: {
#   "executive_summary": "...",
#   "methodology_steps": ["Gather requirements", "Design architecture", ...],
#   "tools_required": ["Python 3.11", "FastAPI", "PostgreSQL"],
#   "cost_breakdown": [{"currency": "$", "amount": 50000, ...}],
#   ...
# }
```

### Example 2: Extract Actionables from a Project Document

```python
from loom.tools.output_formatter import research_extract_actionables

proposal = """
PROJECT PLAN

Actions:
1. Create project board
2. Assign team members

TODO: Set up CI/CD pipeline

Tools: Python, Docker, Jenkins

Timeline: Q1 2025 - Q2 2025

Budget: $100000

Risks:
- Resource constraints
- Timeline pressure
"""

result = research_extract_actionables(proposal)

# Extract for different purposes
tasks = result["actions"]        # ["Create project board", "Assign team members", ...]
tools = result["tools_needed"]   # ["Python", "Docker", "Jenkins"]
timeline = result["timeline_items"]  # Timeline entries
budget = result["costs"]         # Cost items with amounts
risks = result["risks"]          # Risk statements
```

### Example 3: Generate an Executive Brief

```python
# Take a long report and create a condensed summary
long_report = "... 5000 word technical document ..."

result = research_format_report(long_report, format="executive_brief")
print(result["formatted"])
# Output: A concise 200-300 character summary with key highlights
```

### Example 4: Create Technical Specification

```python
# Transform design document into technical spec format
design_doc = """
Executive Summary: New authentication system
Methodology:
1. Analyze current auth flow
2. Design OAuth2 integration
3. Implement and test
Tools Required:
- Python 3.11
- FastAPI
- Redis
"""

result = research_format_report(design_doc, format="technical_spec")
# result["formatted"] is a dictionary optimized for technical reference
```

## Format Options

### 1. JSON Format (Default)
Best for: APIs, downstream processing, structured data

```python
research_format_report(text, format="json")
# Returns: {
#   "executive_summary": "...",
#   "methodology_steps": [...],
#   "tools_required": [...],
#   "timeline": "...",
#   "cost_breakdown": [...],
#   "risk_assessment": [...],
#   "sources": [...]
# }
```

### 2. Markdown Format
Best for: Documents, reports, sharing

```python
research_format_report(text, format="markdown")
# Returns: Markdown-formatted text with headers and bullet points
```

### 3. Executive Brief
Best for: Summaries, presentations, stakeholder communication

```python
research_format_report(text, format="executive_brief")
# Returns: 200-300 character condensed summary
```

### 4. Technical Spec
Best for: Implementation guides, technical documentation

```python
research_format_report(text, format="technical_spec")
# Returns: Dictionary with structured technical information
```

## What Gets Extracted

### research_format_report detects:
- Executive summaries and overviews
- Methodology and approach steps
- Tools and technologies
- Timelines and schedules
- Cost breakdowns
- Risk assessments
- References and sources

### research_extract_actionables extracts:
- **Actions**: TODO, FIXME, action items, numbered lists
- **Tools**: Frameworks, libraries, technologies
- **Timeline**: Dates, durations, schedule items
- **Costs**: Monetary amounts (supports $, €, £, ¥, ₹)
- **Risks**: Risk statements, limitations, challenges

## Common Use Cases

### Use Case 1: Convert LLM Research to Structured Format

```python
# Get raw research from LLM
research = llm.generate("Research best practices for...")

# Convert to structured format
structured = research_format_report(research, format="json")

# Use in your application
for tool in structured["formatted"]["tools_required"]:
    add_to_toolkit(tool)
```

### Use Case 2: Extract Tasks from Project Proposal

```python
# Read proposal document
proposal_text = read_file("proposal.txt")

# Extract actionable tasks
items = research_extract_actionables(proposal_text)

# Create task board
for action in items["actions"]:
    jira.create_issue(summary=action)

# Set budget
total_budget = sum(c["amount"] for c in items["costs"])
```

### Use Case 3: Generate Documentation from Research

```python
# Collect research from multiple sources
sources = [research1, research2, research3]

# Format each as markdown
formatted = [
    research_format_report(s, format="markdown")["formatted"]
    for s in sources
]

# Compile into document
document = "\n".join(formatted)
save_file("research_report.md", document)
```

### Use Case 4: Analyze Project Scope and Budget

```python
# Extract project details
details = research_extract_actionables(project_doc)

# Analyze costs
costs = details["costs"]
total = sum(c["amount"] for c in costs)
print(f"Total Budget: {costs[0]['currency']}{total:,.2f}")

# Analyze timeline
timeline = details["timeline_items"]
print(f"Duration: {len(timeline)} phases")

# Identify risks
risks = details["risks"]
print(f"Key Risks: {', '.join(risks[:3])}")
```

## Return Value Examples

### research_format_report returns:

```python
{
  "formatted": {...},                    # Content in requested format
  "format": "json",                      # The format that was used
  "sections_extracted": ["executive_summary", "methodology", ...],  # Detected sections
  "word_count": 156                      # Total words in input
}
```

### research_extract_actionables returns:

```python
{
  "actions": ["Create project board", "Assign team members", ...],
  "tools_needed": ["Python", "Docker", "Kubernetes", ...],
  "timeline_items": [
    {"time": "2025-01-15", "description": ""},
    {"time": "6 weeks", "description": ""},
    ...
  ],
  "costs": [
    {
      "currency": "$",
      "amount": 50000,
      "unit": "USD",
      "description": "Development"
    },
    ...
  ],
  "risks": ["Resource constraints", "Timeline pressure", ...]
}
```

## Automatic Detection Examples

### Section Detection
Input:
```
Executive Summary: Project overview
Methodology:
Tools Required:
Cost Breakdown:
```
Auto-detected sections: executive_summary, methodology, tools_required, cost_breakdown

### List Detection
Input:
```
1. First item
2. Second item
- Bullet item
* Asterisk item
```
All variants are recognized and extracted

### Currency Detection
Input:
```
$5000 for development
€2500 for infrastructure
£1000 for licensing
¥100000 for servers
```
All currencies ($, €, £, ¥, ₹) are parsed with amounts

### Action Keyword Detection
Input:
```
TODO: Fix authentication
FIXME: Update docs
ACTION: Schedule meeting
MUST: Test payment flow
SHOULD: Optimize queries
```
All action keywords are recognized

## Tips & Tricks

### Tip 1: Chain Tools Together
```python
# Format LLM output, then extract actionables
formatted = research_format_report(llm_output)
actionables = research_extract_actionables(llm_output)

# Now you have both structured and actionable data
```

### Tip 2: Use Markdown for Human-Readable Output
```python
# Great for sharing with non-technical stakeholders
brief = research_format_report(complex_doc, format="markdown")
email_to_stakeholders(brief["formatted"])
```

### Tip 3: Extract Budget Information
```python
costs = research_extract_actionables(doc)["costs"]
total = sum(c["amount"] for c in costs)
currency = costs[0]["currency"] if costs else "$"
print(f"Total: {currency}{total:,.2f}")
```

### Tip 4: Build Task Board from Actions
```python
actions = research_extract_actionables(proposal)["actions"]
for i, action in enumerate(actions, 1):
    task_manager.create({
        "title": action,
        "priority": "medium",
        "order": i
    })
```

## Performance

- **Speed**: < 100ms for typical documents
- **Memory**: Minimal (regex-based)
- **Scalability**: Handles documents up to 1MB
- **Cost**: Zero (no external API calls)

## Troubleshooting

### Section not detected?
- Check spelling of section headers
- Try alternative headers (e.g., "Overview" instead of "Executive Summary")
- Ensure section content follows the header

### Costs not extracted?
- Use recognized currency symbols ($, €, £, ¥, ₹)
- Ensure amount immediately follows currency
- Put description after the amount

### Actions seem incomplete?
- Use action keywords (TODO, FIXME, ACTION)
- Use numbered or bulleted lists
- Use clear, imperative language

### Tools list has unwanted items?
- Filter results in your code if needed
- Use explicit "Tools:" section for reliability
- Tool extraction is heuristic-based and can include capitalized terms

## More Information

For detailed documentation, see:
- `/Users/aadel/projects/loom/docs/output_formatter_reference.md` - Complete reference
- `/Users/aadel/projects/loom/tests/test_tools/test_output_formatter.py` - Code examples
- `/Users/aadel/projects/loom/src/loom/tools/output_formatter.py` - Implementation details

## API Reference

### research_format_report(raw_text: str, format: str = "json") -> dict

Formats raw text into structured output.

**Parameters:**
- `raw_text` (str): Input text
- `format` (str): Output format - "json", "markdown", "executive_brief", or "technical_spec"

**Returns:** Dictionary with formatted output, format used, sections extracted, and word count

---

### research_extract_actionables(text: str) -> dict

Extracts actionable items from text.

**Parameters:**
- `text` (str): Input text

**Returns:** Dictionary with lists of actions, tools, timeline items, costs, and risks

---

## Support

Issues or questions? Check the comprehensive documentation in the docs folder or examine the test cases for more examples.
