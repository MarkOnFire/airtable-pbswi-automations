# Long-Running Agent Harness

This directory contains files for autonomous multi-session development using the two-agent pattern.

## Files

- **feature_list.json.template** - Test case structure (initializer creates project-specific version)
- **claude-progress.txt.template** - Progress log format (agents append session notes)
- **init.sh.template** - Environment setup script (initializer customizes for tech stack)

## Usage

### First-Time Setup

Invoke the initializer agent:

```
I want to build [project description]. Please initialize for long-running autonomous development.
```

The initializer will:
1. Read your specification
2. Create `feature_list.json` with comprehensive test cases
3. Create `init.sh` for reproducible setup
4. Create `claude-progress.txt` with Session 1 notes
5. Initialize git repository

### Ongoing Development

Invoke the coding agent for each feature:

```
Please continue development. Implement the next feature from feature_list.json.
```

The coding agent will:
1. Read progress log and feature list
2. Run `./init.sh` to verify environment
3. Implement ONE feature
4. Test thoroughly
5. Update files and commit

## Core Files (Created by Initializer)

After initialization, your project will have:

```
project/
├── feature_list.json        # Test cases (source of truth)
├── claude-progress.txt      # Session memory
├── init.sh                  # Setup script (executable)
└── [project files]
```

## Documentation

See the main repository documentation:

- `docs/harness-guide.md` - Detailed usage guide with examples
- `AGENTS.md` - Agent architecture and patterns
- `CLAUDE.md` - Configuration and conventions
- `.claude/agents/` - Agent prompts

## Quick Reference

### Check Progress

```bash
# View recent sessions
tail -50 claude-progress.txt

# Count completed features
cat feature_list.json | grep '"passes": true' | wc -l

# View commits
git log --oneline -10
```

### Verify Environment

```bash
# Run setup script
./init.sh
```

### Manual Feature Updates

Don't edit these files manually—agents manage them. If you need to:
- Add features → update feature_list.json with new entries
- Document notes → add to claude-progress.txt
- Modify setup → update init.sh

Always commit changes and notify agents via progress log.

## Agent Collaboration

```
Session 1: Initializer → Creates foundation
Session 2: Coding Agent → Feature A
Session 3: Coding Agent → Feature B
...
Session N: Coding Agent → Final feature
```

Each session is independent but maintains continuity through these files.
