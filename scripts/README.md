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
