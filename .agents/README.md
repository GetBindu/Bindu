# Bindu Agent Workflows & Skills

This directory contains AI agent workflows and skills for automating Bindu development tasks.

## Structure

```
.bindu/
├── workflows/          # Step-by-step guides for complex tasks
│   ├── testing.md     # Run tests and validate changes
│   ├── deployment.md  # Deploy Bindu agents
│   └── release.md     # Create releases and tags
└── skills/            # Modular, reusable capabilities
    ├── test-pr/       # Test pull requests
    ├── deploy-agent/  # Deploy agents to production
    └── create-release/ # Create release notes and tags
```

## Usage

### For AI Coding Assistants (Cascade, Windsurf, etc.)

When working on Bindu, reference these workflows:

```
/workflow testing     # Run comprehensive tests
/workflow deployment  # Deploy an agent
/workflow release     # Create a new release
```

### For Skills

Skills are invoked by workflows or directly:

```
/skill test-pr <PR-number>        # Test a pull request
/skill deploy-agent <agent-name>  # Deploy an agent
/skill create-release <version>   # Create a release
```

## Workflow Philosophy

1. **Script-First**: Workflows invoke scripts, not manual commands
2. **Deterministic Artifacts**: Generate `.local/` artifacts for handoffs
3. **Safety Guardrails**: Never push to main, always verify before destructive actions
4. **Structured Handoffs**: Skills communicate via JSON artifacts

## Artifact Convention

All workflows generate artifacts in `.local/` directory:

- `.local/test-results.json` - Test execution results
- `.local/deployment.json` - Deployment metadata
- `.local/release.json` - Release information

## Contributing

When adding new workflows or skills:

1. Follow the existing structure
2. Include YAML frontmatter with description
3. Define clear inputs, outputs, and safety guardrails
4. Generate deterministic artifacts for handoffs
