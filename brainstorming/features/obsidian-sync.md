# Obsidian Vault Sync Feature

**Created:** 2025-12-23
**Status:** Prototype Complete - Testing in Claude Desktop Project
**Related:** See `docs/DESIGN_DOCUMENT.md` for core AirTable schema

---

## Vision

Create a pipeline that syncs PBS Wisconsin task and content data from AirTable into Obsidian PARA project notes, providing visibility into:
1. Web tickets and tasks assigned to Mark
2. Content ready for review and scheduling

### Why Obsidian?

- **Single pane of glass**: All work items visible in daily workflow
- **PARA structure**: Integrates with existing project organization
- **Offline access**: Works without network connectivity
- **Future bidirectional**: Potential to push status updates back to AirTable

---

## Current Implementation (Phase 1)

Two Obsidian notes are synced manually via Python scripts invoked through Claude Desktop:

### WEB TICKETS.md

| Property | Value |
|----------|-------|
| **Location** | `1 - PROJECTS/PBSWI/WEB TICKETS.md` |
| **Source** | All Tasks table via Mark's Calendar view |
| **Date Field** | Publish Date (falls back to Task Due Date) |
| **Window** | Next 60 days + undated items in "To Be Scheduled" |
| **Filters** | Excludes Complete, Cancelled statuses |
| **Links** | View-based URLs that open in Mark's Calendar interface |

### CONTENT POSTING.md

| Property | Value |
|----------|-------|
| **Location** | `1 - PROJECTS/PBSWI/CONTENT POSTING.md` |
| **Source** | Single Source of Truth table directly |
| **Sections** | Ready for Content Review, Recently Passed QC, Overdue |
| **Filters** | `Single Source Status (BETA)` = "Ready for Review" OR `QC` = "Passed" (last 30 days) |
| **Links** | Direct SST table record URLs |

---

## AirTable Schema Reference

> **Note:** This builds on the verified schema in `docs/DESIGN_DOCUMENT.md`. Only sync-specific details are included here.

### Base

- **Name:** PBS WI Project Management
- **ID:** `appZ2HGwhiifQToB6`

### Key Tables

| Table | ID | Obsidian Sync Role |
|-------|-----|-------------------|
| All Tasks | `tblHjG4gyTLO8OeQd` | Source for WEB TICKETS |
| Single Source of Truth | `tblTKFOwTvK7xw1H5` | Source for CONTENT POSTING |
| Content Calendar | `tblsppp3YH48ffLR7` | **SUNSET** - Do not use |

### Key Views

| View | ID | Table | Purpose |
|------|-----|-------|---------|
| Mark's Calendar | `viwsCw3IFVehzcNxs` | All Tasks | Mark's personal task dashboard |

### Key Interfaces

| Interface | ID | Purpose |
|-----------|-----|---------|
| Web Tickets | `pagOoMi0UkplilONL` | Web ticket management |
| Content Calendar | `pagyYMPikswWlFv4Q` | Content scheduling (within All Tasks) |

### Staff Reference

| Staff Member | Record ID |
|--------------|-----------|
| Mark Riechers | `recji4Uszj3Rl13A1` |

---

## URL Format Reference

### What Works

```
# View-based link (opens record in specific view) - PREFERRED for All Tasks
https://airtable.com/{baseId}/{tableId}/{viewId}/{recordId}

# Table link (opens record in table view) - WORKS for SST
https://airtable.com/{baseId}/{tableId}/{recordId}
```

**Examples:**
```
# Web Ticket (opens in Mark's Calendar view)
https://airtable.com/appZ2HGwhiifQToB6/tblHjG4gyTLO8OeQd/viwsCw3IFVehzcNxs/recVJ2EEKrG4NKueI

# SST Record (opens in table view)
https://airtable.com/appZ2HGwhiifQToB6/tblTKFOwTvK7xw1H5/recdzKm1PDXL01XYp
```

### What Doesn't Work

```
# Interface link with record - interface loads but record never displays
https://airtable.com/{baseId}/{interfaceId}/{recordId}
```

**Finding:** Interface URLs (pag...) do not reliably load specific records even when the record ID is appended. The interface opens but the record never populates.

---

## Date Handling

### QC Date Field (SST)

The `QC Date` field in Single Source of Truth is stored as `singleLineText`, not a date type.

| Format | Example |
|--------|---------|
| M/D/YYYY | 12/22/2025 |
| M/D/YY | 12/22/25 |

**Python parsing function:**
```python
import re
from datetime import datetime

def parse_date(date_str):
    """Parse QC Date string to date object."""
    if not date_str:
        return None
    patterns = [
        (r'(\d{1,2})/(\d{1,2})/(\d{4})', '%m/%d/%Y'),
        (r'(\d{1,2})/(\d{1,2})/(\d{2})', '%m/%d/%y'),
    ]
    for pattern, fmt in patterns:
        if re.match(pattern, date_str.strip()):
            return datetime.strptime(date_str.strip()[:10], fmt).date()
    return None
```

### Digital Premiere Field (SST)

Stored as `dateTime` in ISO format. Extract date with `[:10]`:

```python
premiere_date = record.get('Digital Premiere', '')
if premiere_date:
    date_only = premiere_date[:10]  # "2025-02-13"
```

### Publish Date / Task Due Date (All Tasks)

Both stored as `dateTime` in ISO format. Publish Date takes precedence when present.

---

## Obsidian Note Format

### Frontmatter

```yaml
---
tags:
  - all
  - pbswi
  - airtable-sync
created: 2025-12-22
para: projects
last_synced: 2025-12-23 16:18
---
```

### Header Block

```markdown
# Web Tickets

> **Last synced from AirTable:** 2025-12-23 16:18
> **Source:** Mark's Calendar | Next 60 days

---
```

### Task Format (Web Tickets)

```markdown
## In Progress

- [ ] Task Title
  - **Due:** 2025-01-30
  - Task details here...
  - [Open in AirTable](https://airtable.com/appZ2HGwhiifQToB6/tblHjG4gyTLO8OeQd/viwsCw3IFVehzcNxs/{recordId})

---
## To Be Scheduled

- [ ] Undated Task `Status Badge`
  - Task details
  - [Open in AirTable](...)
```

### Task Format (Content Posting)

```markdown
## Overdue (12 items)

- [x] Content Title | Content Type `Status` ✅ 2025-12-23
  - **Digital Premiere:** 2025-03-20
  - [Open SST Record](https://airtable.com/appZ2HGwhiifQToB6/tblTKFOwTvK7xw1H5/{recordId})

---
## Ready for Content Review (10 items)

*Copy status: Ready for Review*

- [ ] Content Title
  - **Media ID:** 2WLI...
  - [Open SST Record](...)

---
## Recently Passed QC (29 items)

*QC Passed in last 30 days - ready for scheduling*

- [ ] Content Title
  - **QC Date:** 12/22/2025
  - **Digital Premiere:** 2025-01-15
  - [Open SST Record](...)
```

### Section Grouping

| Note | Grouping Strategy |
|------|-------------------|
| WEB TICKETS | By status (In Progress, Not Started, No Status, To Be Scheduled) |
| CONTENT POSTING | By workflow stage (Overdue, Ready for Review, Recently Passed QC, To Be Scheduled) |

Overdue items sort to top. Undated items go in "To Be Scheduled" section.

---

## API Query Patterns

### Web Tickets Query

```python
# Filter: Next 60 days OR no date, exclude Complete/Cancelled
from datetime import datetime, timedelta

today = datetime.now().date()
cutoff = today + timedelta(days=60)

# Using Mark's Calendar view automatically filters to Mark's tasks
view_id = 'viwsCw3IFVehzcNxs'

# Post-filter in Python:
# - Publish Date OR Task Due Date within window
# - Exclude status: Complete, Cancelled
```

### Content Posting Query

```python
# Query 1: Ready for Review
filter_formula = "{Single Source Status (BETA)} = 'Ready for Review'"

# Query 2: Recently Passed QC (requires date parsing)
filter_formula = "{QC} = 'Passed'"
# Then filter in Python for QC Date within last 30 days
```

---

## Authentication

### Token Location

- **File:** `/Users/mriechers/Developer/airtable-mcp-server/.env`
- **Format:** `AIRTABLE_API_KEY=pat...`
- **Required scopes:** `data.records:read`, `schema.bases:read`

### MCP Server Notes

- MCP server caches authentication token at startup
- After updating token in `.env`, Claude Code must be restarted for MCP to pick up changes
- Direct API calls work immediately with new token (useful for testing)

---

## Implementation Notes

### Current Approach (Claude Desktop Project)

1. Python scripts executed via Claude Desktop conversation
2. Direct urllib calls to AirTable API (MCP was unreliable during development)
3. Obsidian MCP server's `obsidian_update_note` tool for writing notes
4. Manual sync triggered via conversation

### Known Issues

1. **MCP token caching:** Requires restart after token refresh
2. **Interface links:** Don't load records reliably
3. **QC Date format:** String field requires parsing
4. **Large result sets:** May need pagination for SST queries

---

## Future Enhancements

### Phase 2: Obsidian Plugin

- Native TypeScript plugin for automated sync
- Configurable sync interval (hourly, daily)
- Ribbon icon or command palette trigger
- Settings UI for table/view/field configuration
- Status indicators in note frontmatter

### Phase 3: Bidirectional Sync

- Track AirTable record IDs in note frontmatter
- Parse checkbox state changes on note save
- Push status updates back to AirTable
- Conflict resolution strategy (AirTable wins? Last-write wins?)
- Prevent overwrite of manual checkbox changes

### Phase 4: Expanded Data Sources

- Filter SST by project/show type
- Include more workflow stages
- Pull from additional views (Design Tasks, Video Edit Tasks)
- Digital Premiere countdown in note display
- Integration with Obsidian Daily Notes

---

## Session Log

### 2025-12-23 - Full Implementation

- Fixed AirTable authentication (token refresh, discovered MCP restart requirement)
- Explored full base structure (50+ tables, 150+ views)
- Built WEB TICKETS sync from Mark's Calendar view
- Built CONTENT POSTING sync from Single Source of Truth
- Discovered Content Calendar table is sunset, replaced by Interface in All Tasks
- Resolved link format issues (Interface links don't load records reliably)
- Implemented QC date parsing for M/D/YYYY format
- Final format: checkboxes, due dates, details, AirTable links
- Moved learnings from the-lodge to this repo

---

## Related Resources

- **This Repo:** `docs/DESIGN_DOCUMENT.md` - Core AirTable schema and automation design
- **Obsidian Vault MCP:** `/Users/mriechers/Developer/obsidian-vault-mcp`
- **AirTable MCP:** `/Users/mriechers/Developer/airtable-mcp-server`
- **Original Brainstorm:** `/Users/mriechers/Developer/the-lodge/brainstorming/airtable-obsidian-sync.md`
- **AirTable API Docs:** https://airtable.com/developers/web/api/introduction
