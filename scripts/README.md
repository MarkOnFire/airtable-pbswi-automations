# AirTable Scripts

## content-calendar-automation.js

Creates task entries in the **📑 All Tasks** table for a selected **✔️Single Source of Truth** record, with platform-specific checklists.

### What It Does

1. Prompts you to select an SSOT record
2. Reads the selected platforms from that record
3. For each platform, creates a task in All Tasks with:
   - Task name: `{Release Title} — {Batch-Episode}`
   - Publish Date: Digital Premiere date
   - Platform mapping to All Tasks options
   - Checklist in Subtasks field
   - Link back to SSOT record
4. Skips platforms that already have tasks (prevents duplicates)

### Setup in AirTable (Scripting Extension)

1. Open your base in AirTable
2. Click **Extensions** (or **Apps**) in the top right
3. Click **+ Add an extension**
4. Search for and add **Scripting**
5. In the Scripting panel, delete any placeholder code
6. Copy/paste the entire contents of `content-calendar-automation.js`
7. Click **Run**

### How to Use

1. Click **Run** in the Scripting extension
2. A dropdown will appear — select the SSOT record you want to process
3. The script will create tasks for each platform and show a summary
4. Review the output to confirm what was created

### Converting to Automation (Future)

If automation slots become available, this script can be converted back:

1. Change the record selection back to `input.config()`:
   ```javascript
   let inputConfig = input.config();
   let recordId = inputConfig.recordId;
   let record = await ssotTable.selectRecordAsync(recordId);
   ```
2. Set up trigger: "When record matches conditions" → Digital Premiere is not empty
3. Configure input variable: `recordId` → Record ID from trigger

### Platform Mapping

| SSOT Platform | → | All Tasks Platform | Checklist |
|---------------|---|-------------------|-----------|
| YouTube | → | YouTube | YouTube |
| Facebook | → | Facebook | Facebook |
| GWQS Facebook | → | Quilt Show Facebook | Quilt Show Facebook |
| pbswisconsin.org/openbar | → | Media Manager | Media Manager |
| quiltshow.com | → | Program/Project Website | Website |
| Other - See Notes | → | Other Note | default |

### Customizing Checklists

Checklists are embedded in the script (lines ~55-105). To update:

1. Edit the `checklists` object in the script
2. Match the format of existing entries
3. Update the automation in AirTable with the new script

For the source templates, see: `templates/checklists/`

### Duplicate Prevention

The script checks for existing tasks linked to the same SSOT record before creating new ones. If a task already exists for a platform, it skips that platform and reports it in the output.

### Date Sync (When Premiere Changes)

If the Digital Premiere date changes after tasks are created, running the script again will:

1. Detect existing tasks with outdated Publish/Start dates
2. Show you which tasks need updating
3. Ask for confirmation before making changes
4. Update **only** the date fields (Publish Date, Task Start Date)

This uses a restricted "update scope" that only allows writing to the two date fields — no other data can be modified during an update.

### Write Scope Protection

The script enforces strict write scopes to protect existing data:

**CREATE Scope (7 fields for new records):**

| Field | Purpose |
|-------|---------|
| Task Details | Task title: `{Release Title} — {Batch-Episode}` |
| Publish Date | Digital premiere date (midnight default) |
| Task Start Date | 2 weeks before Publish Date |
| Platform, Observance, or Note | Platform category |
| Status for Content Calendaring | Default: "In Production" |
| Subtasks | Checklist content |
| Featured Content (SST) | Link back to SSOT |

**UPDATE Scope (2 fields for date sync, requires confirmation):**

| Field | Purpose |
|-------|---------|
| Publish Date | Synced from Digital Premiere |
| Task Start Date | Recalculated as 2 weeks before |

**Additional protections:**
- `enforceWriteScope(fields, operation)` validates fields before every write
- Updates require explicit user confirmation via button prompt
- Script never deletes records
- Any attempt to write to an unauthorized field throws an error and halts execution
- Duplicate prevention checks for existing linked tasks before creating

### Troubleshooting

**"Record not found"**
- Ensure the trigger is passing the correct Record ID

**"No platforms selected"**
- The SSOT record has no platforms checked

**Tasks not appearing**
- Check the All Tasks table for new records
- Verify the automation is enabled
- Check the automation run history for errors

**Wrong checklist content**
- Edit the `checklists` object in the script
- Ensure the `checklistMapping` points to the correct key

---

## sync_airtable_to_obsidian.py

Syncs PBS Wisconsin task and content data from AirTable to Obsidian project notes.

### Overview

This script fetches tasks from AirTable (Mark's Calendar view) and SST (Single Source of Truth) content, then embeds the data into existing Obsidian project notes or creates new ones.

### Features

#### Task Sync
- Fetches tasks from the "Mark's Calendar" AirTable view
- Groups tasks by project and status
- Highlights blocked items (overdue > 30 days)
- Shows ongoing/milestone assignments separately
- Filters out terminal statuses (Complete, Cancelled, Denied, Published, Approved)

#### SST Content Sync
- Distributes SST content items to their related project notes
- Calculates due dates as 30 days before premiere date
- Filters out promotional content (FILL*, PNGV*, 4MBR* prefixes)
- Uses separate section markers from tasks to avoid conflicts

#### Smart Project Matching

The script uses multiple strategies to match SST content to the correct Obsidian note:

1. **Linked Project Record** - Primary method using AirTable's Project field
2. **Media ID Prefix** - Fallback using 4-character Media ID prefixes (e.g., `9UNP` → University Place)
3. **Project Aliases** - Maps AirTable names to Obsidian note names (e.g., "University Place" → "UPlace")
4. **Base Name Extraction** - Strips prefixes like "ED:" and suffixes like "| FY26"
5. **Fallback Note** - Unmatched items go to "WEEKLY — Content Posting"

#### Completed Items Preservation

When syncing, items already marked complete (`[x]`) in Obsidian are preserved and not re-added. This allows you to check off items in Obsidian without them reappearing on the next sync.

#### Section Markers

The script uses HTML comment markers to identify sync sections:

```markdown
<!-- AIRTABLE_SYNC_START -->
## AirTable Tasks
...
<!-- AIRTABLE_SYNC_END -->

<!-- AIRTABLE_SST_START -->
## Content Pipeline
...
<!-- AIRTABLE_SST_END -->
```

This allows sections to be updated without affecting manually-written content.

### Usage

```bash
# Normal sync (updates existing notes, creates new ones in inbox)
python3 scripts/sync_airtable_to_obsidian.py

# Preview without writing
python3 scripts/sync_airtable_to_obsidian.py --dry-run

# Legacy mode (single AIRTABLE.md file)
python3 scripts/sync_airtable_to_obsidian.py --mode legacy
```

### Configuration

#### Environment

The script reads the AirTable API key from:
1. `/Users/mriechers/Developer/airtable-mcp-server/.env` (AIRTABLE_API_KEY=...)
2. Environment variable `AIRTABLE_API_KEY`

#### AirTable IDs

| Resource | ID |
|----------|-----|
| Base | `appZ2HGwhiifQToB6` |
| Tasks Table | `tblHjG4gyTLO8OeQd` |
| SST Table | `tblTKFOwTvK7xw1H5` |
| Projects Table | `tblU9LfZeVNicdB5e` |
| Mark's Calendar View | `viwsCw3IFVehzcNxs` |
| Task Assignments Interface | `pagOoMi0UkplilONL` |
| SST Interface | `pagCh7J2dYzqPC3bH` |

#### Project Aliases

Edit `PROJECT_ALIASES` in the script to map AirTable project names to Obsidian note names:

```python
PROJECT_ALIASES = {
    "University Place": "UPlace",
    "The Great Wisconsin Quilt Show": "Quilt Show",
    "Wisconsin Life": "WI Life",
    "Wisconsin Foodie": "WI Foodie",
    "John McGivern's Main Streets": "Main Streets",
}
```

#### Media ID Prefix Map

The script includes a mapping of 4-character Media ID prefixes to project names (e.g., `9UNP` → University Place). This is used as a fallback when SST items don't have a linked Project record.

To add new prefixes, edit `MEDIA_ID_PREFIX_MAP` in the script. Reference: `knowledge/Media ID Prefixes.md`

### Output Locations

| Content | Location |
|---------|----------|
| New project notes | `0 - INBOX/LEAD — {name}.md` |
| Existing notes | Updated in place |
| Fallback content | `0 - INBOX/WEEKLY — Content Posting.md` |
| Dashboard | `0 - INBOX/AIRTABLE Dashboard.md` |

### Note Structure

New notes are created from a template with:
- YAML frontmatter (tags, created date, status, para location)
- Tasks query block for Obsidian Tasks plugin
- Resources section
- Notes section
- AirTable sync section (at bottom)

### Archive Handling

The script skips the "4 - ARCHIVE" folder when searching for existing notes, so archived projects won't be updated.

### Task Filtering

#### Included
- Tasks due within 2 weeks or overdue
- Ongoing/Milestone assignments (no due date required)
- Professional development tasks
- Time off entries

#### Excluded
- Tasks due more than 2 weeks out
- Terminal statuses: Complete, Cancelled, Denied, Published, Approved

#### SST Filtering
- Excludes promotional content: FILL*, PNGV*, 4MBR* prefixes
- Includes: Ready for Review, Recently Passed QC (last 30 days), Overdue items
