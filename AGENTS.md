# Agent Architecture

This document describes the agent roles, responsibilities, and collaboration patterns for projects derived from this template.

## Long-Running Development Pattern

This template implements Anthropic's proven **two-agent harness** for autonomous multi-session development. This pattern enables complex projects to be built systematically over many sessions with maintained quality and continuity.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Initializer Agent                        │
│  Creates foundation for autonomous development              │
│  • Reads project specification                              │
│  • Generates feature_list.json (50-200 test cases)          │
│  • Creates init.sh (reproducible environment setup)          │
│  • Initializes git repository                               │
│  • Documents Session 1 in claude-progress.txt               │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    Coding Agent(s)                          │
│  Implements features one session at a time                  │
│  • Session N: Read logs → verify env → implement feature    │
│  • Test thoroughly (browser automation preferred)            │
│  • Mark passes: true → commit → update progress log         │
│  • Session N+1: Repeat with next feature                    │
└─────────────────────────────────────────────────────────────┘
```

### Session Management

Each development session operates with a fresh context window but maintains continuity through three files:

1. **feature_list.json** - Source of truth for what needs building and what's complete
2. **claude-progress.txt** - Session-to-session memory and implementation notes
3. **init.sh** - Reproducible environment setup script

**Typical Flow:**
```
Session 1 (Initializer): Specification → feature_list.json + init.sh + git init
Session 2 (Coding):      Feature A → test → commit → update logs
Session 3 (Coding):      Feature B → test → commit → update logs
Session 4 (Coding):      Feature C → test → commit → update logs
...
Session N (Coding):      Final feature → project complete
```

### Core Guardrails

These rules ensure quality and reliability across sessions:

- **feature_list.json is immutable** - features never removed, only marked complete
- **passes: true only after verification** - no premature completion claims
- **One feature per session** - maintains focus and clean boundaries
- **Mandatory testing** - browser automation (MCP Puppeteer) for web apps
- **Progress logging** - every session documented in claude-progress.txt
- **Clean exits** - always commit and leave working tree clean
- **Session start protocol** - read logs, verify environment before starting work

### When to Use This Pattern

**Use long-running harness for:**
- Complex applications requiring 10+ hours of development
- Multi-session projects exceeding context window capacity
- Greenfield development with well-defined scope
- Quality-critical work requiring systematic testing
- Projects where autonomous development is desired

**Use standard workflow for:**
- Simple tasks (< 3 hours work)
- Research or exploration (no implementation)
- Bug fixes in existing code
- Documentation updates

### Files and Structure

```
project/
├── feature_list.json        # Test cases and completion tracking
├── claude-progress.txt      # Session memory and notes
├── init.sh                  # Environment setup (executable)
├── .claude/
│   └── agents/
│       ├── initializer.md   # Initialization agent prompt
│       └── coding-agent.md  # Implementation agent prompt
└── [project files]
```

Templates available in `harness/` directory.

See `docs/harness-guide.md` for detailed usage instructions.

## Template-Specific Agents

This template repository defines specialized agents to assist with knowledge capture, project scaffolding, workspace organization, template maintenance, and long-running autonomous development.

### initializer

**Purpose**: Set up foundation for long-running autonomous development by creating comprehensive project scaffolding and test specifications.

**Capabilities**:
- Read and analyze project specifications
- Generate exhaustive feature_list.json (50-200 test cases)
- Create reproducible init.sh environment setup script
- Initialize git repository with clean first commit
- Document initialization in claude-progress.txt
- Establish project structure matching tech stack

**When to Invoke**:
- Starting new greenfield project for autonomous development
- Project requires 10+ hours of multi-session development
- Need systematic feature tracking and testing
- Want to enable coding agents to work independently

**Example Invocation**:
```
I want to build a task management web app with React and Node.js backend. Please initialize
the project for long-running autonomous development with comprehensive feature tracking.
```

**Guardrails**:
- Must generate minimum 50 test cases (be exhaustive)
- Only marks project setup (ID "1") as complete
- Verifies init.sh runs successfully before finishing
- Never implements features beyond basic structure

### coding-agent

**Purpose**: Implement features from feature_list.json one session at a time with thorough testing and clean git commits.

**Capabilities**:
- Follow strict session start protocol (read logs, verify environment)
- Implement ONE feature per session
- Test thoroughly using browser automation (MCP Puppeteer for web apps)
- Mark features complete only after verification
- Update feature_list.json and claude-progress.txt
- Create clean git commits with descriptive messages
- Leave working tree clean between sessions

**When to Invoke**:
- Continuing development on initialized long-running project
- Implementing next feature from feature_list.json
- Each coding session after initialization

**Example Invocation**:
```
Please continue development on this project. Implement the next feature from feature_list.json.
```

**Guardrails**:
- MUST read claude-progress.txt and feature_list.json at session start
- MUST run init.sh to verify environment
- ONE feature per session (no exceptions)
- Testing mandatory before marking passes: true
- NEVER removes features from feature_list.json
- ALWAYS commits with clean tree before ending session

### janitor

**Purpose**: Maintain clean and organized directory structure, creating workspace for agents and keeping the project tidy without disrupting active work.

**Capabilities**:
- Create and maintain standard subdirectories (`knowledge/`, `brainstorming/`, `artifacts/`)
- Organize misplaced files into appropriate locations
- Check dependencies before moving or deleting files
- Archive outdated content while preserving history
- Create workspace for agents that need dedicated directories
- Update documentation when structure changes

**When to Invoke**:
- Project workspace becoming cluttered or disorganized
- Agent needs dedicated workspace for task
- Preparing project for handoff or review
- Regular scheduled cleanup operations
- Before major refactoring or architectural changes

**Example Invocation**:
```
The project has accumulated a lot of temporary files. Can you organize everything into
appropriate subdirectories and safely clean up anything that's no longer needed?
```

### crawl4ai-knowledge-harvester

**Purpose**: Expert in Crawl4AI workflows, documentation harvesting, and knowledge base curation.

**Capabilities**:
- Configure and run `scripts/crawl_docs.py` with appropriate filters
- Design effective source categorization and slug naming schemes
- Troubleshoot Crawl4AI installation and Playwright issues
- Optimize crawl patterns for different documentation structures
- Maintain `knowledge/sources.json` integrity
- Advise on incremental crawl strategies

**When to Invoke**:
- Setting up initial documentation sources for a new project
- Troubleshooting failed crawls or missing content
- Redesigning knowledge base taxonomy
- Establishing refresh schedules for documentation snapshots

**Example Invocation**:
```
Please help me set up Crawl4AI to harvest the React documentation and Tailwind CSS docs
into the knowledge base, organized by framework.
```

### agent-bootstrap-guide

**Purpose**: Guide new projects through the template adoption process, ensuring all setup steps are completed correctly.

**Capabilities**:
- Walk through the three-step bootstrap process (docs/bootstrap.md)
- Verify Python 3.11 environment and Crawl4AI installation
- Initialize `knowledge/sources.json` with project-specific sources
- Update README.md, AGENTS.md, and CLAUDE.md for project context
- Configure git hooks and workspace conventions
- Validate compliance with workspace infrastructure requirements

**When to Invoke**:
- Starting a new project from this template
- Onboarding new team members to a template-derived project
- Auditing whether all bootstrap steps were completed
- Troubleshooting template setup issues

**Example Invocation**:
```
I just created a new repo from the template. Please guide me through the bootstrap process
for a project that will build a Slack bot integration.
```

### template-maintainer

**Purpose**: Maintain and improve this template repository to reflect evolving workspace conventions and best practices.

**Capabilities**:
- Audit template compliance with workspace infrastructure requirements
- Update template files when workspace conventions change
- Review and enhance documentation (README, CLAUDE.md, AGENTS.md, bootstrap.md)
- Improve scripts and automation tools
- Track template adoption across projects
- Identify common customization patterns for inclusion in template

**When to Invoke**:
- Workspace conventions have been updated
- Multiple projects request similar template enhancements
- Quarterly template maintenance and review
- Preparing template for external publication or sharing

**Example Invocation**:
```
Workspace conventions now require a .claude/settings/ directory. Please update the template
to include this and document it in CLAUDE.md.
```

## Agent Collaboration Patterns

### Knowledge Capture Workflow

1. **agent-bootstrap-guide** initializes the project structure
2. **janitor** creates organized directory structure for project needs
3. **crawl4ai-knowledge-harvester** sets up documentation sources
4. **Main Assistant** performs primary development using captured knowledge
5. **janitor** maintains workspace organization as project evolves
6. **code-reviewer** validates implementation quality
7. **template-maintainer** (if working in template repo) captures learnings for future projects

### Bootstrap Sequence

When starting a new project:

```
User → agent-bootstrap-guide: "Set up new project for [domain]"
  ↓
agent-bootstrap-guide: Verifies environment, creates structure
  ↓
agent-bootstrap-guide → crawl4ai-knowledge-harvester: "Configure sources for [domain]"
  ↓
crawl4ai-knowledge-harvester: Sets up knowledge base
  ↓
agent-bootstrap-guide: Updates project documentation
  ↓
agent-bootstrap-guide → User: "Setup complete, ready for development"
```

### Template Evolution

Improvements flow back to the template:

```
Project discovers pain point or missing feature
  ↓
Main Assistant implements solution in project
  ↓
Developer identifies pattern as generally useful
  ↓
template-maintainer: Evaluates for inclusion in template
  ↓
template-maintainer: Updates template repository
  ↓
Future projects benefit from improvement
```

## Agent Development Guidelines

When creating new project-specific agents for template-derived projects:

1. **Define Clear Boundaries**: Each agent should have distinct, non-overlapping responsibilities
2. **Document Capabilities**: List specific tasks the agent can perform
3. **Provide Invocation Examples**: Show how users should request agent assistance
4. **Register with Workspace**: Use Agent Registrar to add agent to workspace registry
5. **Create Agent Definition**: Add `.claude/agents/<agent-name>.md` file
6. **Update This File**: Document agent in this AGENTS.md

## Workspace-Standard Agents

These agents are available across all workspace projects:

- **Main Assistant**: General development, bug fixes, refactoring
- **code-reviewer**: Code review, architectural feedback, security audits
- **librarian**: Repository health monitoring and workspace audits
- **Agent Registrar**: Agent lifecycle management and registration

See `/Users/mriechers/Developer/workspace_ops/conventions/AGENT_REGISTRY.md` for complete workspace agent documentation.

## Agent Registration Process

To register a new agent for this project:

1. Create agent definition file in `.claude/agents/<agent-name>.md`
2. Invoke Agent Registrar via Claude Code Task tool
3. Agent Registrar will:
   - Validate agent definition
   - Update workspace AGENT_REGISTRY.md
   - Update COMMIT_CONVENTIONS.md with new agent name
   - Ensure cross-platform compatibility (Claude Code, Cursor, Copilot, etc.)
4. Update this AGENTS.md file with agent documentation
5. Commit changes with appropriate agent attribution

## Evaluation and Testing

### Agent Effectiveness Metrics

Track agent performance through:
- **Invocation frequency**: How often is each agent used?
- **Task completion rate**: Does agent successfully complete requested tasks?
- **User satisfaction**: Does agent output meet expectations?
- **Handoff efficiency**: How smoothly do agents collaborate?

### Testing Strategy

- **Simulation harnesses**: Test agents with representative project scenarios
- **Regression suites**: Ensure agents don't break existing workflows
- **Knowledge base validation**: Verify crawled documentation quality
- **Bootstrap repeatability**: New projects can successfully adopt template

## Template Customization

When adapting this template for a specific project:

1. **Update this file** to reflect project-specific agent roles
2. **Remove unused template agents** if not relevant to project
3. **Add domain-specific agents** (e.g., aws-infrastructure-agent, frontend-specialist)
4. **Document collaboration patterns** unique to your project
5. **Maintain workspace compliance** while customizing for needs

## Questions and Support

- **Agent Registry**: `/Users/mriechers/Developer/workspace_ops/conventions/AGENT_REGISTRY.md`
- **Commit Conventions**: `/Users/mriechers/Developer/workspace_ops/conventions/COMMIT_CONVENTIONS.md`
- **Infrastructure Requirements**: `/Users/mriechers/Developer/workspace_ops/conventions/WORKSPACE_INFRASTRUCTURE_REQUIREMENTS.md`
- **Bootstrap Guide**: `docs/bootstrap.md`

For agent-related questions, consult workspace conventions or invoke Agent Registrar.
