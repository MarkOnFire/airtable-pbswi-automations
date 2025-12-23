# Long-Running Development Harness Guide

This guide explains how to use the long-running agent harness for autonomous multi-session development. This pattern enables complex projects to be built systematically over many sessions while maintaining quality and continuity.

## Table of Contents

- [Overview](#overview)
- [When to Use](#when-to-use)
- [Quick Start](#quick-start)
- [Session 1: Initialization](#session-1-initialization)
- [Session 2+: Implementation](#session-2-implementation)
- [Core Concepts](#core-concepts)
- [Testing Strategies](#testing-strategies)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Examples](#examples)

## Overview

The long-running harness implements a **two-agent pattern**:

1. **Initializer Agent**: Creates foundation (one-time setup)
2. **Coding Agent**: Implements features (multiple sessions)

**Key Files:**
- `feature_list.json` - Comprehensive test cases and completion tracker
- `claude-progress.txt` - Session memory and implementation notes
- `init.sh` - Reproducible environment setup script

**Flow:**
```
Session 1: Specification → Initializer → feature_list.json + init.sh + git init
Session 2: Coding Agent → Feature A → test → commit → update logs
Session 3: Coding Agent → Feature B → test → commit → update logs
...
Session N: Coding Agent → Final feature → project complete
```

## When to Use

### Use Long-Running Harness For:

✅ **Complex applications** requiring 10+ hours of development
✅ **Multi-session projects** that exceed context window capacity
✅ **Greenfield development** with well-defined scope
✅ **Quality-critical work** requiring systematic testing
✅ **Autonomous development** where you want agents to work independently

### Use Standard Workflow For:

❌ Simple tasks (< 3 hours work)
❌ Research or exploration (no implementation)
❌ Bug fixes in existing code
❌ Documentation updates
❌ Unclear or evolving requirements

## Quick Start

### 1. Initialize Project

Invoke the initializer agent:

```
I want to build a task management web app with React frontend and Node.js backend.
Features include user auth, task CRUD, categories, search, and notifications.
Please initialize for long-running autonomous development.
```

**Result:** Project initialized with feature_list.json (50-200 test cases), init.sh, and progress log.

### 2. Implement Features

Invoke the coding agent repeatedly:

```
Please continue development. Implement the next feature from feature_list.json.
```

**Result:** One feature implemented, tested, committed, and documented per session.

### 3. Monitor Progress

Check completion status:

```bash
# View progress summary
cat claude-progress.txt | tail -50

# Count completed features
cat feature_list.json | grep '"passes": true' | wc -l

# View recent commits
git log --oneline -10
```

## Session 1: Initialization

### What Happens

The initializer agent:

1. **Reads specification** and asks clarifying questions
2. **Generates feature_list.json** with 50-200 test cases:
   - Setup (environment, dependencies, configuration)
   - Functional (business logic, workflows)
   - UI (components, layouts, interactions)
   - Integration (APIs, external services, data)
   - Edge cases (errors, validation, security)
3. **Creates init.sh** for reproducible setup
4. **Initializes git** with clean first commit
5. **Documents Session 1** in claude-progress.txt

### Your Role

- Provide clear project specification
- Answer clarifying questions about requirements
- Review feature_list.json for completeness
- Verify init.sh runs successfully

### Quality Checkpoints

After initialization, verify:

- [ ] feature_list.json has 50+ features (or appropriate count for scope)
- [ ] Features cover all categories (setup, functional, ui, integration, edge-cases)
- [ ] Each feature has clear description and 3-10 test steps
- [ ] init.sh is executable and runs without errors
- [ ] Git initialized with clean .gitignore
- [ ] claude-progress.txt documents Session 1 completely

### Example feature_list.json Entry

```json
{
  "id": "23",
  "category": "functional",
  "description": "User can create a new task with title, description, and due date",
  "steps": [
    "Navigate to task list page",
    "Click 'New Task' button",
    "Fill in task title field",
    "Fill in description field",
    "Select due date from date picker",
    "Click 'Create' button",
    "Verify task appears in list with correct data",
    "Refresh page and verify task persists"
  ],
  "passes": false,
  "notes": ""
}
```

## Session 2+: Implementation

### Session Start Protocol

The coding agent ALWAYS begins with:

```bash
# 1. Orient
pwd
cat claude-progress.txt
cat feature_list.json
git log --oneline -20
git status

# 2. Verify Environment
./init.sh
# [Run smoke test - visit homepage, run tests, etc.]

# 3. Choose Feature
# Select next feature where passes: false
```

### Implementation Flow

1. **Plan**: Review feature, identify files, plan testing
2. **Implement**: Write code following project conventions
3. **Test**: Verify using browser automation or appropriate method
4. **Update**: Mark passes: true in feature_list.json
5. **Commit**: Clean git commit with descriptive message
6. **Document**: Add session entry to claude-progress.txt

### Session End Verification

Before ending session, confirm:

- [ ] Feature fully implemented
- [ ] All test steps verified passing
- [ ] feature_list.json updated (passes: true, metadata updated)
- [ ] Git commit created with clean message
- [ ] claude-progress.txt updated with session notes
- [ ] Working tree clean (`git status`)

### Example Session Output

```
Session 23 Complete!

✅ Feature ID 23: User can create a new task

📊 Progress: 23/156 features complete (14.7%)

🧪 Testing: Browser automation via MCP Puppeteer

📝 Git: a3f82b1 - feat: Add task creation form and API endpoint

➡️ Next: Feature ID 24 (functional: User can edit existing task)
```

## Core Concepts

### feature_list.json as Source of Truth

- **Immutable**: Features never removed, only marked complete
- **Comprehensive**: 50-200 test cases covering all functionality
- **Structured**: Organized by category with clear test steps
- **Trackable**: Metadata section tracks completion percentage

**Never:**
- Remove features from the list
- Mark features complete without testing
- Skip test steps
- Change feature descriptions arbitrarily

### claude-progress.txt as Session Memory

Each session entry documents:
- Session number and timestamp
- Target feature (ID and description)
- Implementation approach
- Testing method and results
- Updated statistics
- Git commit hash
- Blockers or notes
- Next steps

This file is the agent's ONLY memory between sessions.

### init.sh as Environment Contract

The setup script:
- Checks prerequisites (Node.js version, Python, etc.)
- Installs dependencies
- Sets up environment variables
- Runs database migrations
- Builds project assets
- Runs test suite
- Provides clear instructions

**Must be idempotent** (safe to run multiple times).

## Testing Strategies

### Browser Automation (Preferred for Web Apps)

Using MCP Puppeteer:

```javascript
// Navigate and interact
await page.goto('http://localhost:3000');
await page.click('[data-testid="new-task-button"]');
await page.fill('input[name="title"]', 'Buy groceries');
await page.click('button[type="submit"]');

// Verify results
await page.waitForSelector('[data-testid="task-item"]');
const taskText = await page.textContent('[data-testid="task-item"]');
// Confirm taskText includes "Buy groceries"
```

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

### Automated Test Suites

If project has testing framework:

```bash
# Run unit tests
npm test

# Run integration tests
npm run test:integration

# Run e2e tests
npm run test:e2e
```

Coding agent writes new tests for new features.

### Manual Verification

When automation not feasible:
- Document exact steps performed
- Take screenshots of key states
- Save evidence in artifacts/ directory
- Note observations in claude-progress.txt

## Best Practices

### For Users

**During Initialization:**
- Provide detailed specification upfront
- Answer clarifying questions thoroughly
- Review feature_list.json for completeness
- Verify init.sh works on your machine

**During Implementation:**
- Let coding agent work autonomously
- Invoke for each session: "Continue development"
- Review commits periodically
- Report issues or blockers as they arise
- Resist urge to skip features or rush

**Quality Gates:**
- Run init.sh before each session
- Review git log weekly
- Check feature_list.json progress regularly
- Test application end-to-end at milestones

### For Agents

**Initializer Agent:**
- Be exhaustive with feature list (50-200 test cases)
- Create robust, idempotent init.sh
- Document decisions in progress log
- Verify setup works before finishing

**Coding Agent:**
- ALWAYS follow session start protocol
- ONE feature per session (no exceptions)
- Test thoroughly before marking complete
- Keep commits atomic and descriptive
- Document everything in progress log
- Ask for help when blocked

## Troubleshooting

### "init.sh fails with missing dependencies"

**Solution:**
1. Check prerequisites section in init.sh
2. Install missing tools (Node.js, Python, etc.)
3. Verify versions match requirements
4. Re-run init.sh

### "Feature seems too large for one session"

**Solution:**
1. Ask user if feature should be split
2. If yes, add new features to feature_list.json
3. Original feature references new sub-features in notes
4. Implement sub-features individually

### "Tests failing but feature looks correct"

**Solution:**
1. Debug test steps one by one
2. Document investigation in progress log
3. If quick fix, implement in same session
4. If complex, leave passes: false and document blocker
5. User can review and provide guidance

### "Can't verify feature without external service"

**Solution:**
1. Document blocker in claude-progress.txt
2. Add notes to feature explaining dependency
3. Mock external service if possible
4. Skip to next unblocked feature
5. Return after dependency resolved

### "Feature list missing important functionality"

**Solution:**
1. Add new features to feature_list.json
2. Assign next available ID
3. Update metadata counts
4. Document addition in claude-progress.txt
5. Continue development

### "Previous session left broken code"

**Solution:**
1. Review git log to identify breaking commit
2. Document issue in progress log
3. Fix immediately (don't compound problems)
4. Add regression test if possible
5. Consider marking previous feature as fails: false

## Examples

### Example 1: Simple Web App

**Specification:**
```
Task management app with React frontend and Express backend.
Users can create, read, update, delete tasks.
Tasks have title, description, due date, and status.
Basic auth with email/password.
```

**Initialization Output:**
- 87 features total
- Setup: 5 (environment, dependencies, database)
- Functional: 42 (CRUD, auth, business logic)
- UI: 25 (components, forms, lists, modals)
- Integration: 8 (API calls, persistence, auth flow)
- Edge cases: 7 (validation, errors, security)

**Session 2 Example:**
```
Feature ID 6: User can register with email and password

Implementation:
- Created /api/auth/register endpoint
- Added password hashing with bcrypt
- Implemented email validation
- Created User model in database
- Added registration form component

Testing via MCP Puppeteer:
- Navigated to /register
- Filled email: test@example.com
- Filled password: SecurePass123!
- Clicked Register button
- Verified redirect to login page
- Verified user record in database

Result: ✅ All test steps passing

Commit: b7c41a2 - feat: Add user registration
```

### Example 2: API Service

**Specification:**
```
RESTful API for inventory management system.
Products, categories, suppliers, stock tracking.
JWT authentication, role-based access control.
PostgreSQL database, Docker deployment.
```

**Initialization Output:**
- 134 features total
- Setup: 12 (Docker, database, migrations, env)
- Functional: 68 (CRUD for all entities, auth, business logic)
- Integration: 31 (database queries, JWT, external APIs)
- Edge cases: 23 (validation, security, error handling)

**Session 5 Example:**
```
Feature ID 19: API endpoint returns paginated product list

Implementation:
- Created GET /api/products endpoint
- Added query params: page, limit, sort
- Implemented pagination logic in ProductService
- Added database query with LIMIT/OFFSET
- Returned metadata: total, page, pages

Testing via curl:
- GET /api/products?page=1&limit=10
- Verified 10 items returned
- Verified total count in metadata
- Verified pagination links
- GET /api/products?page=2&limit=10
- Verified next 10 items

Result: ✅ All test steps passing

Commit: 3d8f1e9 - feat: Add paginated product list endpoint
```

### Example 3: CLI Tool

**Specification:**
```
Command-line tool for analyzing log files.
Parse multiple log formats (JSON, plain text, syslog).
Filter by date, level, message pattern.
Output statistics and generate reports.
```

**Initialization Output:**
- 64 features total
- Setup: 4 (CLI framework, dependencies, build)
- Functional: 38 (parsing, filtering, analysis, reports)
- Integration: 12 (file I/O, streaming, exports)
- Edge cases: 10 (invalid input, large files, performance)

**Session 8 Example:**
```
Feature ID 24: Tool filters logs by severity level

Implementation:
- Added --level flag to CLI arguments
- Implemented level parsing (DEBUG, INFO, WARN, ERROR)
- Added filtering logic in LogProcessor
- Updated output formatter to show only matching entries

Testing via bash:
- Created test log file with mixed levels
- Ran: ./logtool analyze --level ERROR test.log
- Verified only ERROR lines in output
- Ran: ./logtool analyze --level INFO test.log
- Verified INFO and higher severity in output
- Tested invalid level: verified error message

Result: ✅ All test steps passing

Commit: 9a2c7f6 - feat: Add severity level filtering
```

## Advanced Topics

### Multiple Coding Agents

For faster development, run multiple coding agents in parallel:
- Each works on independent features
- Coordinate via feature_list.json (mark in_progress)
- Sync frequently via git pull/push
- Avoid overlapping file modifications

### Specialized Sub-Agents

Consider creating specialized agents:
- **QA Agent**: Reviews completed features for quality
- **Cleanup Agent**: Refactors and removes technical debt
- **Release Agent**: Prepares releases and documentation
- **Performance Agent**: Optimizes and profiles code

### Adaptation to Other Domains

This pattern works for:
- Mobile apps (React Native, Flutter)
- Desktop applications (Electron, PyQt)
- Data pipelines (ETL, processing)
- Infrastructure automation (Terraform, Ansible)
- Machine learning (training pipelines, model deployment)

Adjust feature_list.json categories and testing strategies accordingly.

## Related Resources

- `AGENTS.md` - Agent architecture and collaboration patterns
- `CLAUDE.md` - Claude Code configuration and conventions
- `harness/` - Template files for new projects
- Anthropic Documentation:
  - [Building Effective Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
  - [Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview)
  - [Autonomous Coding Quickstart](https://github.com/anthropics/claude-quickstarts/tree/main/autonomous-coding)

## Summary

The long-running harness enables autonomous multi-session development through:

1. **Comprehensive Planning** (initializer creates exhaustive feature list)
2. **Systematic Execution** (coding agent implements one feature per session)
3. **Rigorous Testing** (verification required before completion)
4. **Clear Memory** (progress log and feature list persist across sessions)
5. **Quality Assurance** (clean commits, documented decisions, reproducible setup)

Use this pattern for complex projects where quality and systematic progress matter more than speed. Let agents work autonomously while you focus on specification, review, and architectural decisions.
