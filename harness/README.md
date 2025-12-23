# Long-Running Agent Harness Templates

This directory contains template files for setting up autonomous multi-session development using the two-agent pattern (initializer + coding agent).

## Template Files

### feature_list.json.template

Comprehensive test case structure for tracking features and completion.

**Used by:**
- Initializer agent (creates and populates)
- Coding agent (reads and updates)

**Contains:**
- Project metadata
- Feature list with categories: setup, functional, ui, integration, edge-cases
- Each feature: id, category, description, steps[], passes, notes
- Completion metadata

**Do NOT edit manually** - agents manage this file.

### claude-progress.txt.template

Session memory and progress log format.

**Used by:**
- Both agents (read at session start, append at session end)

**Contains:**
- Session-by-session development log
- Implementation notes and decisions
- Feature completion tracking
- Git commit hashes
- Next steps and recommendations

**Critical for continuity** - agents rely on this for memory between sessions.

### init.sh.template

Reproducible environment setup script template.

**Used by:**
- Initializer agent (creates and customizes)
- Coding agent (runs at session start for verification)

**Contains:**
- Prerequisite checks
- Dependency installation
- Environment configuration
- Database setup (if applicable)
- Build commands
- Test execution
- Start instructions

**Must be idempotent** (safe to run multiple times).

## Usage

### In This Template Repository

These templates serve as reference and starting point. The initializer agent uses them as guidance when creating project-specific versions.

### In New Projects

1. **During initialization**, the initializer agent:
   - Creates feature_list.json (based on template structure)
   - Creates claude-progress.txt (based on template format)
   - Creates init.sh (customized for project tech stack)

2. **During development**, the coding agent:
   - Reads feature_list.json and claude-progress.txt at session start
   - Runs init.sh to verify environment
   - Updates both files at session end

### For Template Adopters

Copy these templates to new projects:

```bash
# Copy harness templates to new project
cp -R templates/genai-project/harness /path/to/new-project/
cp -R templates/genai-project/.claude /path/to/new-project/

# Templates ready for initializer agent to use
```

## File Lifecycle

```
Template Repository:
├── harness/*.template       → Reference templates
└── .claude/agents/*.md      → Agent prompts

New Project Initialization:
1. User: "Initialize project for long-running development"
2. Initializer agent:
   - Reads templates as guidance
   - Creates feature_list.json (project-specific)
   - Creates claude-progress.txt (Session 1 entry)
   - Creates init.sh (tech stack-specific)
   - Creates project structure
   - Initializes git

New Project Implementation:
3. User: "Continue development"
4. Coding agent:
   - Reads feature_list.json (finds next feature)
   - Reads claude-progress.txt (loads context)
   - Runs init.sh (verifies environment)
   - Implements feature
   - Updates both files
   - Commits changes

Repeat step 3-4 until feature_list.json shows 100% complete
```

## Customization Guidelines

### For Template Maintainers

When updating templates:
- Keep structure backward compatible
- Document breaking changes in commit message
- Update agent prompts (.claude/agents/*.md) if structure changes
- Test with sample project initialization

### For Project-Specific Needs

After initializer creates project files, you can:
- Add fields to feature_list.json metadata section
- Customize claude-progress.txt format
- Enhance init.sh with project-specific checks
- Add automation scripts that read these files

**Important:** Don't remove required fields or change core structure—agents depend on it.

## Integration with CI/CD

These files support automation:

### feature_list.json
```bash
# Count completed features
completed=$(cat feature_list.json | jq '[.features[] | select(.passes == true)] | length')

# Calculate completion percentage
total=$(cat feature_list.json | jq '.features | length')
percent=$((completed * 100 / total))

# Fail build if < 100%
if [ $percent -lt 100 ]; then
  echo "Only $percent% complete"
  exit 1
fi
```

### init.sh
```bash
# CI/CD can use init.sh for reproducible builds
./init.sh
```

### claude-progress.txt
```bash
# Extract recent work
tail -50 claude-progress.txt

# Find blockers
grep -A 3 "Blockers:" claude-progress.txt
```

## Related Documentation

- `docs/harness-guide.md` - Comprehensive usage guide
- `AGENTS.md` - Agent architecture and collaboration patterns
- `CLAUDE.md` - Claude Code configuration and conventions
- `.claude/agents/initializer.md` - Initializer agent prompt
- `.claude/agents/coding-agent.md` - Coding agent prompt

## Examples

See `docs/harness-guide.md` for complete examples of:
- Simple web app initialization
- API service development
- CLI tool implementation
- Session-by-session feature development

## Questions?

For questions about:
- **Template usage**: See `docs/harness-guide.md`
- **Agent behavior**: See `.claude/agents/*.md` prompts
- **Architecture**: See `AGENTS.md`
- **Workspace conventions**: See workspace conventions documentation
