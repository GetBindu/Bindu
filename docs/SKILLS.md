# Skills System

Skills are reusable capabilities that agents can advertise and execute. They enable intelligent task routing, capability discovery, and agent orchestration.

## How Skills Work

```mermaid
sequenceDiagram
    participant Developer
    participant SkillYAML
    participant SkillLoader
    participant AgentManifest
    participant AgentCard
    participant Orchestrator
    participant Negotiation

    Note over Developer,SkillYAML: 1. Skill Creation
    Developer->>SkillYAML: Create skill.yaml<br/>(metadata, capabilities, tags)
    SkillYAML->>SkillYAML: Define:<br/>- name, description<br/>- capabilities, tags<br/>- input/output formats<br/>- assessment metadata

    Note over Developer,AgentManifest: 2. Agent Startup (bindufy)
    Developer->>SkillLoader: config = {skills: ["skills/my-skill"]}
    SkillLoader->>SkillYAML: Load skill.yaml
    SkillYAML-->>SkillLoader: Skill metadata
    SkillLoader->>SkillLoader: Parse YAML<br/>Extract capabilities<br/>Load documentation
    SkillLoader-->>AgentManifest: List[Skill]
    AgentManifest->>AgentManifest: Build manifest with skills

    Note over AgentCard,Orchestrator: 3. Skill Advertisement
    Orchestrator->>AgentCard: GET /.well-known/agent.json
    AgentCard-->>Orchestrator: {<br/>  name, description,<br/>  skills: [{<br/>    id, name, tags,<br/>    capabilities_detail,<br/>    input_modes, output_modes<br/>  }]<br/>}

    rect rgb(240, 248, 255)
        Note over Orchestrator: 4. Skill Discovery
        Orchestrator->>Orchestrator: Parse agent cards<br/>Index skills by:<br/>- tags<br/>- capabilities<br/>- keywords
        Orchestrator->>Orchestrator: Build skill registry
    end

    rect rgb(255, 248, 240)
        Note over Orchestrator,Negotiation: 5. Task Routing (Negotiation)
        Orchestrator->>Orchestrator: Task: "Extract tables from PDF"
        Orchestrator->>Negotiation: POST /agent/negotiation<br/>{task_summary}

        Negotiation->>Negotiation: Match against skills:<br/>- Keywords: pdf, extract, tables<br/>- Tags: pdf, document<br/>- Capabilities: table_extraction<br/>- Assessment metadata

        Negotiation->>Negotiation: Calculate scores:<br/>- Skill match: 0.92<br/>- Specialization boost: +0.3<br/>- Anti-pattern check: pass

        Negotiation-->>Orchestrator: {<br/>  accepted: true,<br/>  score: 0.89,<br/>  skill_matches: [{<br/>    skill_id: "pdf-processing-v1",<br/>    score: 0.92<br/>  }]<br/>}
    end

    rect rgb(240, 255, 240)
        Note over Orchestrator,AgentManifest: 6. Task Execution
        Orchestrator->>AgentManifest: POST / (message/send)<br/>{content: "Extract tables..."}
        AgentManifest->>AgentManifest: Route to handler<br/>Execute skill logic
        AgentManifest-->>Orchestrator: {result: tables_data}
    end

    Note over SkillLoader,Negotiation: Key Components
    Note over SkillLoader: - YAML parsing<br/>- Documentation loading<br/>- Capability extraction
    Note over Negotiation: - Semantic matching<br/>- Keyword scoring<br/>- Specialization boost<br/>- Anti-pattern filtering
```

## Skill Structure

Skills are defined in YAML files with comprehensive metadata:

```yaml
skill_id: "pdf-processing-v1"
name: "PDF Processing"
version: "1.0.0"
description: "Extract text, tables, and forms from PDF documents"

capabilities:
  - text_extraction
  - table_extraction
  - form_filling
  - ocr_support

tags:
  - pdf
  - document
  - extraction

input_structure: |
  {
    "file": "base64_encoded_pdf_or_url",
    "operation": "extract_text|fill_form|extract_tables",
    "options": {
      "ocr": true,
      "language": "eng"
    }
  }

output_format: |
  {
    "success": true,
    "pages": [{"page_number": 1, "text": "...", "confidence": 0.98}],
    "metadata": {"total_pages": 10, "processing_time_ms": 1500}
  }

# Assessment metadata for negotiation
assessment:
  keywords:
    - pdf
    - extract
    - document

  specializations:
    - domain: invoice_processing
      confidence_boost: 0.3

  anti_patterns:
    - "pdf editing"
    - "pdf creation"
```

## Skill API Endpoints

### List All Skills

```bash
GET /agent/skills
```

**Response:**
```json
{
  "skills": [
    {
      "skill_id": "pdf-processing-v1",
      "name": "PDF Processing",
      "version": "1.0.0",
      "capabilities": ["text_extraction", "table_extraction"]
    }
  ]
}
```

### Get Skill Details

```bash
GET /agent/skills/{skill_id}
```

**Response:**
```json
{
  "skill_id": "pdf-processing-v1",
  "name": "PDF Processing",
  "description": "Extract text, tables, and forms from PDF documents",
  "input_structure": {...},
  "output_format": {...},
  "examples": [...]
}
```

### Get Skill Documentation

```bash
GET /agent/skills/{skill_id}/documentation
```

Returns human-readable documentation in Markdown format.

## Creating Skills

### 1. Create Skill File

Create a YAML file in `skills/` directory:

```yaml
# skills/my-skill/skill.yaml
skill_id: "my-skill-v1"
name: "My Skill"
version: "1.0.0"
description: "What this skill does"

capabilities:
  - capability1
  - capability2

tags:
  - tag1
  - tag2

documentation: |
  # My Skill

  Detailed documentation here...

input_structure: |
  {
    "field1": "value",
    "field2": 123
  }

output_format: |
  {
    "result": "output"
  }

examples:
  - title: "Example 1"
    input:
      field1: "test"
    output:
      result: "success"

assessment:
  keywords:
    - keyword1
    - keyword2
```

### 2. Register Skill in Agent Config

```python
config = {
    "name": "my_agent",
    "skills": ["skills/my-skill"],  # Path to skill directory
}
```

### 3. Implement Skill Logic

Skills are executed through your agent's handler function. The skill metadata is used for discovery and routing, while actual execution happens in your code.

## Skill Metadata Fields

### Required Fields

- `skill_id` - Unique identifier (e.g., "pdf-processing-v1")
- `name` - Human-readable name
- `version` - Semantic version (e.g., "1.0.0")
- `description` - Brief description of capability

### Optional Fields

- `capabilities` - List of specific capabilities
- `tags` - Keywords for discovery
- `documentation` - Detailed markdown documentation
- `input_structure` - JSON schema or example
- `output_format` - Expected output structure
- `examples` - Usage examples with input/output
- `error_handling` - How errors are handled
- `best_practices` - Guidelines for users
- `constraints` - Limitations and requirements
- `assessment` - Metadata for negotiation

## Assessment Metadata

Used by the negotiation system for intelligent agent selection:

```yaml
assessment:
  # Keywords for semantic matching
  keywords:
    - pdf
    - extract
    - document

  # Domain specializations with confidence boost
  specializations:
    - domain: invoice_processing
      confidence_boost: 0.3
    - domain: form_filling
      confidence_boost: 0.2

  # Patterns this skill should NOT match
  anti_patterns:
    - "pdf editing"
    - "pdf creation"

  # Complexity indicators for performance estimation
  complexity_indicators:
    simple:
      - "single page"
      - "extract text"
    medium:
      - "multiple pages"
      - "fill form"
    complex:
      - "scanned document"
      - "ocr"
```

## Best Practices

### Skill Design

- **Single responsibility** - One skill, one capability
- **Clear naming** - Descriptive skill_id and name
- **Versioning** - Use semantic versioning
- **Documentation** - Provide examples and error handling

### Input/Output

- **Structured formats** - Use JSON schemas
- **Validation** - Document required fields
- **Error handling** - Define error response format
- **Examples** - Include realistic use cases

### Assessment

- **Accurate keywords** - Match actual capabilities
- **Honest specializations** - Don't over-claim
- **Clear anti-patterns** - Prevent false matches
- **Complexity indicators** - Help with performance estimation

## Example Skills

See `examples/skills/` directory for complete examples:

- `skills/question-answering/` - Q&A capability
- `skills/pdf-processing/` - PDF document handling
- `skills/cbt-*/` - Therapy protocol skills
