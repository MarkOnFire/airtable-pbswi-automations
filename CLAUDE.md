# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is a template repository for bootstrapping generative AI projects. It provides scaffolding for:
- Crawl4AI-powered documentation harvesting
- Agent-based development workflows
- Knowledge base management
- Structured project initialization

## Git Commit Convention

**IMPORTANT**: This project follows workspace-wide commit conventions.

See: `/Users/mriechers/Developer/workspace_ops/conventions/COMMIT_CONVENTIONS.md`

**Quick Reference**: All AI-generated commits must include `[Agent: <name>]` after the subject line.

Example:
```
fix: Description of fix

[Agent: Main Assistant]

Details of the change...

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Long-Running Development (Multi-Session Projects)

This template supports Anthropic's proven pattern for autonomous multi-session development. Use this for complex projects requiring 10+ hours of work across multiple sessions.

### First Session: Initialization

**Invoke the initializer agent** to set up the project foundation:

```
I want to build [project description]. Please initialize for long-running autonomous development.
```

**The initializer agent will:**
1. Read your project specification
2. Generate `feature_list.json` with 50-200 comprehensive test cases
3. Create `init.sh` for reproducible environment setup
4. Initialize git repository with clean first commit
5. Document Session 1 in `claude-progress.txt`

**DO NOT use initializer for:**
- Simple tasks (< 3 hours)
- Bug fixes in existing code
- Research or exploration
- Documentation updates

### Subsequent Sessions: Implementation

**Invoke the coding-agent** to implement features one at a time:

```
Please continue development. Implement the next feature from feature_list.json.
```

**The coding-agent follows strict protocol:**

1. **Session Start** (MANDATORY):
   - Reads `claude-progress.txt` (session memory)
   - Reads `feature_list.json` (work tracker)
   - Reviews git log (recent changes)
   - Runs `./init.sh` (verifies environment)
   - Tests basic functionality (smoke test)

2. **Implementation**:
   - Implements ONE feature from feature_list.json
   - Tests thoroughly (browser automation for web apps)
   - Marks `passes: true` only after verification
   - Creates git commit with descriptive message
   - Updates `claude-progress.txt` with session notes

3. **Session End**:
   - Verifies working tree clean
   - Documents next recommended feature
   - Provides progress summary

### Core Guardrails

These rules ensure quality across sessions:

- **feature_list.json is source of truth** - features never removed
- **passes: true requires verification** - no premature completion
- **One feature per session** - maintains focus and clean boundaries
- **Testing mandatory** - browser automation (MCP) preferred for web apps
- **Progress logging** - every session documented
- **Clean exits** - always commit and leave working tree clean

### Browser Automation for Testing

For web applications, coding-agent uses MCP Puppeteer for verification.

**Setup** (add to `.claude/settings.json`):
```json
{
  "mcpServers": {
    "puppeteer": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-puppeteer"]
    }
  }
}
```

Agents use browser tools to:
- Navigate to pages and verify rendering
- Fill forms and submit data
- Click buttons and test interactions
- Verify end-to-end workflows
- Capture screenshots for documentation

## Available MCP Servers

Model Context Protocol (MCP) servers extend Claude's capabilities with specialized tools. These are deployed globally and available in all projects via `workspace_ops`.

### CLI Agent Server (Multi-LLM Code Review & Queries)

**Purpose**: Get independent perspectives from other AI models (Gemini, Claude CLI, Codex) for code review, architecture decisions, or general queries. **Cost-effective alternative to parallel agent execution.**

**Location**: `/Users/mriechers/Developer/workspace_ops/mcp-servers/cli-agent-server/`
**Status**: ✅ Active and deployed globally
**Registry**: See `workspace_ops/config/mcp-configs/mcp_servers_registry.json`

**Why Use This Instead of Parallel Agents:**
- **Lower cost**: Uses local CLI agents with your existing API keys
- **Faster**: Direct CLI execution without agent overhead
- **Simpler**: Single tool call vs. complex agent coordination
- **Multi-LLM**: Access Gemini, Claude, and Codex perspectives in one place

**Available Tools:**

1. **`codex_review_code`** - Independent code review with structured feedback
   ```
   # Automatically available when you say:
   "Review this code using Codex"

   # Provides:
   - Security vulnerability detection
   - Performance issue identification
   - Code style and maintainability analysis
   - Severity-ranked issues with line numbers
   ```

2. **`query_agent`** - Ask any CLI agent a question
   ```
   # Usage examples:
   "Ask Gemini: What's the best caching strategy for this API?"
   "Get Claude's opinion on this architecture decision"
   "Ask Codex to explain this algorithm"

   # Parameters:
   - prompt: Your question (required)
   - agent: "claude", "gemini", or "codex" (default: claude)
   - model: Optional model override
   - system_prompt: Optional instructions
   ```

3. **`query_multiple_agents`** - Get consensus from multiple AIs
   ```
   # Usage:
   "Ask all agents: Should I use Redis or Memcached for caching?"

   # Automatically synthesizes responses or shows individual perspectives
   # Much cheaper than spawning parallel agent tasks!
   ```

4. **`create_agent_session`** - Start persistent conversation
   ```
   # For multi-turn discussions:
   "Start a conversation with Gemini about database optimization"

   # Maintains context across multiple messages
   ```

5. **`send_message_to_session`** - Continue conversation
6. **`get_session_history`** - Review past messages
7. **`close_session`** - End conversation
8. **`share_context_with_agent`** - Inject files/data into session
9. **`aggregate_agent_responses`** - Synthesize multiple responses
10. **`list_active_sessions`** - Show all open conversations

**When to Use CLI Agent Server vs. Parallel Agents:**

✅ **Use CLI Agent Server for:**
- Code review from different AI perspective
- Getting "second opinions" on architecture decisions
- Exploring different approaches to a problem
- Quick queries that don't need full agent context
- Cost-sensitive multi-LLM queries

❌ **Use Parallel Agent Tasks for:**
- Complex multi-step tasks requiring tool use
- Tasks needing access to filesystem/bash/edit tools
- Long-running autonomous work
- Tasks requiring agent-specific specialization

**Configuration:**
- Already deployed globally via `workspace_ops/scripts/deploy_mcp_configs.sh`
- Requires API keys in workspace_ops `.env`: `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`
- Logs: `/Users/mriechers/Developer/workspace_ops/mcp-servers/cli-agent-server/logs/`

**Example Workflows:**

```
# Code review workflow
1. "Review this function using Codex"
2. Get structured feedback with security/performance/style issues
3. Apply fixes based on recommendations

# Architecture decision workflow
1. "Ask Gemini and Claude: What's the best state management approach for React?"
2. Get synthesized consensus or individual perspectives
3. Use aggregate_agent_responses to combine insights

# Multi-turn exploration
1. create_agent_session with Gemini
2. send_message_to_session: "How does caching work in Redis?"
3. send_message_to_session: "Show me an example with Node.js"
4. close_session when done
```

### Other Available MCP Servers

**uw-policy-agent**: UW-Madison HR policy search
**editorial-assistant**: PBS Wisconsin video metadata and transcripts
**obsidian-vault**: Access and search Obsidian notes
**claude-chat-export**: Export Claude conversation threads
**fantastical**: Calendar event management

See `workspace_ops/CLAUDE.md` for complete MCP server documentation.

### Project Files

Long-running projects maintain three critical files:

| File | Purpose | Updated By |
|------|---------|------------|
| `feature_list.json` | Test cases and completion tracking | Both agents |
| `claude-progress.txt` | Session memory and implementation notes | Both agents |
| `init.sh` | Reproducible environment setup | Initializer (created), Coding-agent (runs) |

**Templates** available in `harness/` directory.

### When NOT to Use Long-Running Pattern

Use standard Main Assistant workflow for:
- Simple tasks (< 3 hours)
- Research or exploration (no implementation)
- Bug fixes in existing code
- Documentation updates
- Unclear or evolving requirements

See `docs/harness-guide.md` for detailed usage instructions and examples.

## Template Agents

This repository defines specialized agents for template maintenance, project bootstrapping, and long-running autonomous development. Agent definitions are stored in `.claude/agents/`:

- **initializer**: Sets up foundation for long-running development (feature_list.json, init.sh, progress log)
- **coding-agent**: Implements features one session at a time with testing and git commits
- **janitor**: Maintains clean directory structure and creates workspace for agents as needed
- **crawl4ai-knowledge-harvester**: Expert in Crawl4AI workflows and knowledge base curation
- **agent-bootstrap-guide**: Guides new projects through template adoption process
- **template-maintainer**: Maintains template and ensures workspace compliance

See `AGENTS.md` for complete agent documentation and collaboration patterns.

## Initial Agent Workflow

When first working in a project derived from this template:
1. **Invoke agent-bootstrap-guide** to guide through the setup process, OR:
2. Ask the repository owner to clarify the project's purpose and which documentation needs to be collected
3. Use Crawl4AI via `scripts/crawl_docs.py` to harvest requested documentation sources (or invoke crawl4ai-knowledge-harvester)
4. Save gathered references in `knowledge/` with clear source attribution
5. Document the knowledge update strategy (cadence, tooling, ownership) in the project README
6. Stage and commit the onboarding work; ask owner to configure remote if needed

## Python Environment Setup

**Required for Crawl4AI**: Python 3.11

```bash
# Create dedicated virtual environment
python3.11 -m venv .venv-crawl4ai
source .venv-crawl4ai/bin/activate

# Install dependencies
python3.11 -m pip install crawl4ai
python3.11 -m playwright install chromium
```

## Common Development Commands

### Knowledge Capture (Crawl4AI)

```bash
# Interactive setup - define initial sources
python3.11 scripts/crawl_docs.py --init

# Append additional sources
python3.11 scripts/crawl_docs.py --append

# Re-crawl specific source by slug
python3.11 scripts/crawl_docs.py --slug <slug-name>

# Re-crawl specific category
python3.11 scripts/crawl_docs.py --category <category-name>

# Dry run (fetch without writing)
python3.11 scripts/crawl_docs.py --dry-run

# Default run (crawl all sources)
python3.11 scripts/crawl_docs.py
```

The crawler writes outputs to `knowledge/<category>/`:
- `<slug>.md` - Markdown conversion
- `<slug>.html` - Raw HTML
- `<slug>.json` - Metadata (URL, timestamp, status)

Source definitions are stored in `knowledge/sources.json`.

## Repository Architecture

### Core Structure

```
.
├── AGENTS.md              # Agent architecture design document
├── docs/
│   └── bootstrap.md       # Detailed setup guide for template adopters
├── knowledge/             # Documentation snapshots and metadata
│   └── sources.json       # Crawler source definitions
├── scripts/
│   └── crawl_docs.py      # Interactive Crawl4AI harvester
└── templates/
    └── genai-project/     # Reusable project scaffold
```

### Key Files

- **AGENTS.md**: Living design document describing agent roles, responsibilities, and coordination patterns. Update this when defining new agent architectures.
- **docs/bootstrap.md**: Three-step bootstrap process (create repo, setup Crawl4AI, design agents). Reference when initializing new projects.
- **scripts/crawl_docs.py**: Async crawler with interactive CLI. Supports filtering by category/slug, dry-run mode, and incremental updates.
- **templates/genai-project/**: Copy-ready scaffold with knowledge/, scripts/, and configuration files for new projects.

### Knowledge Management

The `knowledge/` directory stores structured documentation:
- Organized by category (e.g., `knowledge/alfredapp/`, `knowledge/toggl/`)
- Each source has three files: `.md`, `.html`, `.json`
- `sources.json` maintains the authoritative source list
- Commit snapshots to version control for research trail preservation

### Git Hooks

The repository uses workspace-wide git hooks from `/Users/mriechers/Developer/workspace_ops/conventions/git-hooks/`.

Configured in `.githooks/commit-msg` - delegates to workspace commit-msg hook for enforcement.

## Crawl4AI Script Details

The `scripts/crawl_docs.py` script:
- Requires Python 3.11 shebang (`#!/usr/bin/env python3.11`)
- Uses `AsyncWebCrawler` from crawl4ai package
- Supports multiple operational modes via CLI flags
- Validates source structure (requires `category`, `slug`, `url`)
- Generates slugs from URLs if not provided
- Writes three artifacts per source (HTML, Markdown, JSON metadata)
- Includes timestamp and status tracking in metadata

### Interactive Prompts

When run with `--init` or `--append`:
- Prompts for: category, URL, slug (with auto-generated default), notes
- Leave category blank to finish input loop
- Sources are immediately saved to `knowledge/sources.json`

### Error Handling

- Failed crawls are reported but don't stop batch processing
- Exit code 1 if any source failed, 0 if all succeeded
- Dry-run mode fetches but skips file writes

## Templates Usage

The `templates/genai-project/` directory is a copy-ready scaffold:
```bash
cp -R templates/genai-project ~/Projects/new-project
cd ~/Projects/new-project
# Follow BOOTSTRAP.md in copied directory
```

Contains:
- Knowledge directory structure
- Copy of `scripts/crawl_docs.py`
- `.gitignore` for Python virtual environments
- `BOOTSTRAP.md` quickstart guide
- `README.md` template with Co-Authors section

## Agent Architecture Considerations

When documenting agents in `AGENTS.md`:
- Define clear role boundaries and responsibilities
- Document inter-agent communication patterns
- Establish evaluation and testing strategies
- Keep API credentials in `.env` (never commit), use `.env.example` for templates
- Plan for agent evolution (baseline metrics, regression tests)

## Documentation Maintenance

- Keep `knowledge/` snapshots current by re-running crawler periodically
- Update `AGENTS.md` when agent topology changes
- Document any new automation scripts in this file
- When customizing for a specific project, replace this template README with project-specific context
