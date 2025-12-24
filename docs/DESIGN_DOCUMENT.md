# PBS Wisconsin AirTable Automation - Design Document

**Version:** 1.1
**Date:** December 23, 2025
**Status:** Schema Verified - Ready for Implementation

---

## Executive Summary

This document outlines the design for automating PBS Wisconsin's video content publishing workflow by synchronizing data between AirTable's "Single Source of Truth" (SSOT) and "📑 All Tasks" tables, with automatic generation of platform-specific checklists.

> **Schema Update (December 23, 2025)**: The original "Content Calendar" table has been deprecated (marked as SUNSET). The new content calendaring system uses the **📑 All Tasks** table with 18 platform options.

### Key Recommendation

**Use AirTable's native automation with scripting** for the core workflow. This approach:
- Meets all functional requirements without external services
- Minimizes complexity and maintenance burden
- Can be implemented in 1-2 days
- Requires no additional infrastructure costs

External scripting (Node.js/Python) should only be considered if future requirements demand external API integration (YouTube scheduling, Google Docs creation, etc.).

---

## Problem Statement

### Current Pain Points

1. **Manual Date Synchronization**: When a Digital Premiere Date is set in SSOT, corresponding All Tasks entries must be manually created
2. **Platform Duplication**: Each platform (YouTube, Facebook, PBS.org, etc.) requires a separate task entry with platform-specific tasks
3. **Checklist Management**: Platform-specific checklists must be manually copied into each task entry's Subtasks field
4. **Linking Overhead**: Task entries must be manually linked back to their SSOT source record

### Desired State

1. Setting a Digital Premiere Date in SSOT automatically creates All Tasks entries
2. One entry is created per designated platform
3. Each entry has the appropriate platform-specific checklist pre-populated
4. All entries are automatically linked to the source SSOT record

---

## Technical Architecture

### Recommended Approach: Native AirTable Automation

```
┌─────────────────────────────────────────────────────────────────┐
│                        AIRTABLE BASE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────┐       ┌─────────────────────────────┐  │
│  │ Single Source of    │       │      📑 All Tasks           │  │
│  │ Truth (SSOT)        │       │   (Content Calendaring)     │  │
│  │                     │       │  ┌──────────────────────┐   │  │
│  │ • Project Name      │       │  │ YouTube Task         │   │  │
│  │ • Digital Premiere  │──────▶│  │ Publish Date: [Date] │   │  │
│  │ • Platforms []      │       │  │ Subtasks: [Checklist]│   │  │
│  │ • Other metadata    │       │  │ Link: [SSOT Record]  │   │  │
│  │                     │       │  └──────────────────────┘   │  │
│  │                     │       │                             │  │
│  │                     │       │  ┌──────────────────────┐   │  │
│  │                     │──────▶│  │ Facebook Task        │   │  │
│  │                     │       │  │ Publish Date: [Date] │   │  │
│  │                     │       │  │ Subtasks: [Checklist]│   │  │
│  │                     │       │  │ Link: [SSOT Record]  │   │  │
│  │                     │       │  └──────────────────────┘   │  │
│  └─────────────────────┘       │                             │  │
│           │                    │  ┌──────────────────────┐   │  │
│           │                    │  │ PBS.org Task         │   │  │
│           ▼                    │  │ Publish Date: [Date] │   │  │
│  ┌─────────────────────┐       │  │ Subtasks: [Checklist]│   │  │
│  │    AUTOMATION       │       │  │ Link: [SSOT Record]  │   │  │
│  │                     │       │  └──────────────────────┘   │  │
│  │ Trigger: Digital    │       │                             │  │
│  │ Premiere Date set   │       └─────────────────────────────┘  │
│  │                     │                                        │
│  │ Action: Run Script  │                                        │
│  │ • Read platforms    │                                        │
│  │ • For each platform │                                        │
│  │   - Create task     │                                        │
│  │   - Add checklist   │                                        │
│  │   - Link to source  │                                        │
│  └─────────────────────┘                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Why Native AirTable?

| Criterion | Native AirTable | External Script | Winner |
|-----------|-----------------|-----------------|--------|
| Setup Time | Hours | Days | Native |
| Infrastructure | None | Hosting required | Native |
| Maintenance | Low | Medium | Native |
| Cost | $0 additional | ~$5-20/month | Native |
| External APIs | Not possible | Full access | External |
| Credential Security | Limited | Full control | External |
| Non-dev Modifications | Easy | Impossible | Native |

**Verdict**: Since the core workflow doesn't require external API calls, native automation is the clear choice.

---

## Data Model

### Table: ✔️Single Source of Truth (SSOT) - `tblTKFOwTvK7xw1H5`

> **Schema verified via AirTable MCP on December 23, 2025**

| Field Name | Field ID | Type | Purpose |
|------------|----------|------|---------|
| Batch-Episode | `fldyNLTitzM2qV1wQ` | singleLineText | Working title of program |
| Release Title | `fldXqxjjxR4z5IJv6` | singleLineText | Official release title |
| Digital Premiere | `fldxIBOo7vNdy2qWY` | dateTime | **AUTOMATION TRIGGER** |
| Platform | `fldCtnirVhuL7J4D9` | multipleSelects | Platforms for publishing |
| Status | `fld26Z19WJULN7n3U` | singleSelect | Workflow status |
| Associated Content Calendar Task | `flde0igdMEhE8Pjai` | multipleRecordLinks | **Link to All Tasks** (NEW) |
| Content Calendar (SUNSET) | `fldVBFkjosBLcZM9k` | multipleRecordLinks | ~~Link to Content Calendar~~ (DEPRECATED) |
| Project | `fld3su0x59DeTog76` | multipleRecordLinks | Link to Projects table |

**Platform Options (SSOT)**: pbswisconsin.org/openbar, Facebook, YouTube, quiltshow.com, GWQS Facebook, Other - See Notes

### Table: 📑 All Tasks - `tblHjG4gyTLO8OeQd` (Content Calendaring)

> **This is the NEW content calendar system**, replacing the deprecated Content Calendar table.

| Field Name | Field ID | Type | Purpose |
|------------|----------|------|---------|
| Task Details | `fldcyAdxUrrYE6yGx` | multilineText | Task name/title |
| Publish Date | `fldzTnbRToZ2opEq3` | dateTime | Publishing date |
| Platform, Observance, or Note | `fldyYCFc9qoYAtxPu` | singleSelect | Platform (18 options) |
| Content Type | `fldJFp2KuSaIKqB4U` | singleSelect | Episode, Digital Short, etc. |
| Status for Content Calendaring | `fldVTNga9dB6SV2z1` | singleSelect | Workflow status |
| Featured Content (SST) | `fldvB7Lu5YAhZ51Vi` | multipleRecordLinks | **Link back to SSOT** |
| Subtasks | `fldyKn5kdJeDwEGti` | richText | **CHECKLIST CONTENT** |
| Notes | `fldwi7UC52TeIqAFE` | richText | Additional notes |

**Platform Options (All Tasks - 18 total)**:
- **Social**: Facebook, Education Facebook, Instagram, Instagram Story, Quilt Show Facebook, Quilt Show Instagram, Wisconsin Life Instagram
- **YouTube**: YouTube, YouTube Shorts, Education YouTube
- **Websites**: Program/Project Website, Education Website
- **PBS Platforms**: Media Manager, PBS LearningMedia, sIX
- **Other**: Podcast Apps, Observance Day, Other Note

> **Bidirectional Link**: SSOT (`Associated Content Calendar Task`) ↔ All Tasks (`Featured Content (SST)`)

### DEPRECATED: Content Calendar - `tblsppp3YH48ffLR7`

> ⚠️ **This table is deprecated** (indicated by "(SUNSET)" suffix in SSOT link field). Do not use for new automations.

The old Content Calendar only had 3 platform options (YouTube, Facebook, Instagram) vs. 18 in All Tasks.

---

## Checklist Template Strategy

### Recommendation: Markdown Files in Repository

Based on our evaluation, storing checklists as Markdown files in this repository provides the best balance of:
- **Simple parsing** for automation scripts
- **Version control** for change tracking
- **Template variables** for dynamic content

### Proposed Directory Structure

```
templates/
  checklists/
    youtube.md
    youtube-shorts.md
    facebook.md
    instagram.md
    pbs-website.md           # pbswisconsin.org/openbar
    quiltshow-website.md     # quiltshow.com
    quilt-show-facebook.md   # GWQS Facebook
    media-manager.md
    pbs-learningmedia.md
    education-platforms.md   # Education Facebook, YouTube, Website
```

### Template Format

Each checklist file uses Markdown with optional template variables:

```markdown
# YouTube Publishing Checklist

## Pre-Upload
- [ ] Video file exported (1080p MP4)
- [ ] Closed captions (SRT) prepared
- [ ] Thumbnail created (1280x720)

## Upload & Metadata
- [ ] Video uploaded
- [ ] Title: "{project_name}"
- [ ] Description with PBS Wisconsin branding
- [ ] Tags added (minimum 5)
- [ ] Category selected

## Publishing Settings
- [ ] Premiere scheduled for {premiere_date}
- [ ] End screen configured
- [ ] Cards added
- [ ] Notify subscribers enabled

## Post-Publish
- [ ] Added to playlist
- [ ] Pinned comment added
- [ ] Social media cross-post scheduled
```

### Migration from Google Docs

The current checklist templates in Google Docs should be:
1. Exported to Markdown format
2. Added as template variables where video-specific data appears
3. Stored in `templates/checklists/`
4. Version controlled via git

**Hybrid Option**: If non-technical users need to edit checklists frequently, maintain Google Doc as "human-readable reference" and sync changes to Markdown manually.

---

## Implementation Plan

### Phase 1: Schema Validation ✅ COMPLETE

**Prerequisites:**
- [x] Fix AirTable MCP authentication (restart Claude Code after token update)
- [x] Verify SSOT table exists with required fields
- [x] Verify All Tasks table exists with required fields
- [x] Document exact field names

**Tasks:**
1. ✅ Explore SSOT table schema
2. ✅ Explore All Tasks table schema (discovered Content Calendar is deprecated)
3. ✅ Identify linked record field names
4. ✅ Update this document with actual field names

### Phase 2: Checklist Migration (Day 1-2)

**Tasks:**
1. Access Google Doc checklist templates
2. Create `templates/checklists/` directory
3. Convert each platform checklist to Markdown
4. Test variable substitution logic

### Phase 3: Automation Development (Day 2-3)

**Tasks:**
1. Create AirTable automation:
   - Trigger: "When record matches conditions" on SSOT
   - Condition: Digital Premiere Date is not empty
2. Add "Run script" action with logic:
   - Read triggering record
   - Get selected platforms
   - For each platform, create All Tasks entry
   - Populate checklist in Subtasks field (hardcoded in script initially)
   - Link back to source record via `Featured Content (SST)`

### Phase 4: Testing (Day 3-4)

**Tasks:**
1. Test with single platform selection
2. Test with multiple platform selection
3. Test edge cases:
   - No platforms selected
   - Date changed (not just set)
   - Duplicate prevention
4. Verify links work bidirectionally

### Phase 5: Refinement (Day 4-5)

**Tasks:**
1. Refine checklists with PBS Wisconsin team input
2. Add error handling and notifications
3. Consider moving checklists to config table for easier updates
4. Document automation behavior for team

### Phase 6: Deployment & Training (Day 5+)

**Tasks:**
1. Enable automation in production
2. Monitor first 10-20 automated entries
3. Train team on expected workflow
4. Establish process for checklist updates

---

## Automation Script (Draft)

> **Schema verified December 23, 2025 - Updated to use 📑 All Tasks table**

```javascript
// AirTable Automation Script - Content Calendar Task Generator
// Trigger: When SSOT record matches conditions (Digital Premiere is not empty)
// Table: ✔️Single Source of Truth (tblTKFOwTvK7xw1H5)
// Target: 📑 All Tasks (tblHjG4gyTLO8OeQd)

// Get input configuration from automation
let inputConfig = input.config();
let recordId = inputConfig.recordId;

// Get table references - VERIFIED TABLE NAMES
let ssotTable = base.getTable('✔️Single Source of Truth');
let tasksTable = base.getTable('📑 All Tasks');

// Fetch the triggering record
let record = await ssotTable.selectRecordAsync(recordId);

if (!record) {
    output.markdown('❌ Record not found');
    return;
}

// Get field values - VERIFIED FIELD NAMES
let releaseTitle = record.getCellValue('Release Title');     // fldXqxjjxR4z5IJv6
let batchEpisode = record.getCellValue('Batch-Episode');     // fldyNLTitzM2qV1wQ
let premiereDate = record.getCellValue('Digital Premiere');  // fldxIBOo7vNdy2qWY
let platforms = record.getCellValue('Platform');             // fldCtnirVhuL7J4D9 (multipleSelects)

// Use Release Title if available, fall back to Batch-Episode
let projectName = releaseTitle || batchEpisode || 'Untitled';

// Validate required fields
if (!premiereDate) {
    output.markdown('⚠️ No Digital Premiere date set - skipping');
    return;
}

if (!platforms || platforms.length === 0) {
    output.markdown('⚠️ No platforms selected - skipping');
    return;
}

// Platform-specific checklists
// SSOT Platform options: pbswisconsin.org/openbar, Facebook, YouTube,
//                        quiltshow.com, GWQS Facebook, Other - See Notes
const checklists = {
    'YouTube': `## YouTube Publishing Checklist

### Pre-Upload
- [ ] Video file exported (1080p MP4)
- [ ] Closed captions (SRT) prepared
- [ ] Thumbnail created (1280x720)

### Upload & Metadata
- [ ] Video uploaded to YouTube
- [ ] Title: "${projectName}"
- [ ] Description with PBS Wisconsin branding
- [ ] Tags added (minimum 5)

### Publishing Settings
- [ ] Premiere scheduled
- [ ] End screen configured
- [ ] Cards added
- [ ] Notify subscribers enabled

### Post-Publish
- [ ] Added to appropriate playlist
- [ ] Pinned comment added
- [ ] Social media cross-post scheduled`,

    'Facebook': `## Facebook Publishing Checklist

### Preparation
- [ ] Preview clip prepared (if applicable)
- [ ] Post copy drafted
- [ ] Thumbnail/image selected

### Posting
- [ ] Post scheduled for premiere date
- [ ] Correct page selected (PBS Wisconsin)
- [ ] Tags and mentions added
- [ ] Link preview verified

### Engagement
- [ ] Comment monitoring scheduled
- [ ] Response templates ready`,

    'pbswisconsin.org/openbar': `## PBS Wisconsin Website Publishing Checklist

### Pre-Publish
- [ ] Rights clearance verified
- [ ] Metadata entered in Media Manager
- [ ] Correct availability window set
- [ ] Geo-restrictions configured (if applicable)

### Publishing
- [ ] Content published to pbswisconsin.org
- [ ] Show page updated
- [ ] Series links verified

### Verification
- [ ] Playback tested
- [ ] Captions verified
- [ ] Mobile playback tested`,

    'quiltshow.com': `## Quilt Show Website Publishing Checklist

### Content Preparation
- [ ] Video/content ready for quiltshow.com
- [ ] Description and metadata prepared
- [ ] Images selected

### Publishing
- [ ] Content uploaded to quiltshow.com
- [ ] Page links verified
- [ ] Cross-promotion prepared`,

    'GWQS Facebook': `## Garden & Wisconsin Quilt Show Facebook Checklist

### Preparation
- [ ] Post copy drafted for GWQS audience
- [ ] Relevant images/clips selected
- [ ] Hashtags prepared

### Posting
- [ ] Post scheduled
- [ ] GWQS Facebook page selected
- [ ] Cross-tagging with main PBS WI page (if applicable)

### Engagement
- [ ] Comment monitoring scheduled`
};

// Map SSOT platform names to All Tasks "Platform, Observance, or Note" options
// All Tasks options: Facebook, Education Facebook, Instagram, Instagram Story,
//   YouTube, YouTube Shorts, Education YouTube, Program/Project Website,
//   Education Website, Quilt Show Facebook, Quilt Show Instagram,
//   Wisconsin Life Instagram, Media Manager, PBS LearningMedia, sIX,
//   Podcast Apps, Observance Day, Other Note
const platformMapping = {
    'YouTube': 'YouTube',
    'Facebook': 'Facebook',
    'GWQS Facebook': 'Quilt Show Facebook',
    'pbswisconsin.org/openbar': 'Program/Project Website',
    'quiltshow.com': 'Program/Project Website',  // Or could create custom handling
    'Other - See Notes': 'Other Note'
};

// Create task entries for each platform
let createdRecords = [];
let errors = [];

for (let platform of platforms) {
    let platformName = platform.name;

    try {
        // Get checklist for this platform
        let checklist = checklists[platformName] ||
            `## ${platformName} Publishing Checklist\n\n- [ ] Complete platform-specific tasks`;

        // Add project context to checklist
        let fullChecklist = `# ${projectName}\n\n${checklist}`;

        // Build the record fields for All Tasks table
        let recordFields = {
            'Task Details': `${projectName} - ${platformName}`,      // fldcyAdxUrrYE6yGx
            'Publish Date': premiereDate,                             // fldzTnbRToZ2opEq3
            'Subtasks': fullChecklist,                                // fldyKn5kdJeDwEGti (CHECKLIST)
            'Featured Content (SST)': [{id: recordId}]                // fldvB7Lu5YAhZ51Vi (link to SSOT)
        };

        // Set Platform if there's a valid mapping
        let taskPlatform = platformMapping[platformName];
        if (taskPlatform) {
            recordFields['Platform, Observance, or Note'] = {name: taskPlatform};  // fldyYCFc9qoYAtxPu
        }

        // Create the task entry
        let newRecordId = await tasksTable.createRecordAsync(recordFields);

        createdRecords.push({
            id: newRecordId,
            platform: platformName
        });

    } catch (error) {
        errors.push({
            platform: platformName,
            error: error.message
        });
    }
}

// Report results
let summary = `## Automation Complete\n\n`;
summary += `**Project:** ${projectName}\n`;
summary += `**Digital Premiere:** ${premiereDate}\n\n`;

if (createdRecords.length > 0) {
    summary += `### ✅ Created ${createdRecords.length} Task Entries\n`;
    for (let rec of createdRecords) {
        summary += `- ${rec.platform}\n`;
    }
}

if (errors.length > 0) {
    summary += `\n### ❌ Errors (${errors.length})\n`;
    for (let err of errors) {
        summary += `- ${err.platform}: ${err.error}\n`;
    }
}

output.markdown(summary);
```

---

## Future Considerations

### Future: PBS LearningMedia & EDU Integration

The PBS LearningMedia and Education website checklists require deeper integration with external Google Docs workflows used by those teams. This is out of scope for the initial automation but should be considered for a future phase:

- Integrate with existing team Google Docs for asset tracking
- Potentially automate Google Doc creation from templates
- Sync checklist status between AirTable and Google Docs

### When to Move to External Scripting

Consider migrating to an external script (Node.js/Python on AWS Lambda or similar) if:

1. **External API Integration Required**
   - Auto-scheduling YouTube premieres via YouTube API
   - Creating Google Docs for content briefs
   - Syncing with external project management tools
   - Sending notifications via custom services

2. **Security Requirements**
   - API credentials must be completely hidden from AirTable users
   - Compliance requires external credential management

3. **Scale Issues**
   - Automation runs exceed AirTable plan limits
   - Processing time exceeds 30-second timeout

### Alternative Architecture (If Needed Later)

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│    AirTable     │────▶│   AWS Lambda     │────▶│  Google Docs    │
│   (Webhook)     │     │   (Node.js)      │     │  YouTube API    │
│                 │◀────│                  │     │  Other Services │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

**Estimated Cost**: $0-10/month on AWS Lambda free tier

---

## Open Questions

### ✅ Base Exploration (COMPLETED December 23, 2025)

1. **Exact field names** - ✅ Documented in Data Model section above
2. **Platform field type** - ✅ SSOT uses `multipleSelects`, All Tasks uses `singleSelect`
3. **Existing linked record relationships** - ✅ Bidirectional link: SSOT (`Associated Content Calendar Task`) ↔ All Tasks (`Featured Content (SST)`)
4. **Current views and filters** - ⚠️ Multiple views exist; automation trigger should use a filtered view
5. **Existing automations** - ⚠️ Need to check in AirTable UI before deploying
6. **Content Calendar migration** - ✅ Confirmed: Old Content Calendar deprecated, All Tasks is the new system

### Business Logic Clarifications (Need Team Input)

1. **Duplicate Handling**: What should happen if automation runs twice for same record?
   - Suggestion: Check if task entries already exist for this SSOT record before creating new ones
2. **Date Changes**: Should updating the premiere date update existing task entries or create new ones?
   - Suggestion: Update existing entries rather than creating duplicates
3. **Platform Changes**: If platforms are added/removed after initial creation, how to handle?
   - Suggestion: Only add entries for newly-added platforms; don't delete existing ones
4. **Manual Overrides**: Can users modify automated task entries? How to track changes?
   - Consider: Add a "Created by Automation" checkbox field to All Tasks schema

### Checklist Questions (Need Team Input)

1. **Update Frequency**: How often do checklists change?
2. **Platform List**: ✅ SSOT has 6 options; All Tasks has 18 platform options (see Data Model)
3. **Variable Content**: What video-specific information should be included in checklists?
4. **Completion Tracking**: Do we need to track checklist completion back in SSOT?
5. **Subtasks vs Notes**: Should checklists go in `Subtasks` field or `Notes` field in All Tasks?

### Schema Observations (Updated December 23, 2025)

1. **Schema Migration Complete**: Confirmed that `Content Calendar (SUNSET)` field indicates the old table is deprecated
2. **New System**: `📑 All Tasks` table with `Associated Content Calendar Task` link is the current content calendaring system
3. **Platform expansion**: All Tasks has 18 platform options vs. old Content Calendar's 3 - much more comprehensive
4. **Better platform mapping**: SSOT's 6 platforms now map cleanly to All Tasks' 18 options (e.g., "GWQS Facebook" → "Quilt Show Facebook")
5. **Checklist field**: All Tasks uses `Subtasks` (richText) for checklist content instead of `Notes`

---

## Next Steps

1. ~~**Immediate**: Restart Claude Code to pick up new AirTable token~~ ✅ Done
2. ~~**Then**: Explore AirTable base schema using MCP tools~~ ✅ Done
3. ~~**Update**: Revise this document with actual field names~~ ✅ Done
4. ~~**Schema Fix**: Update to use All Tasks instead of deprecated Content Calendar~~ ✅ Done
5. **Now**: Review updated script with PBS Wisconsin team
6. **Next**: Create checklist templates in `templates/checklists/` directory
7. **Then**: Create test automation in AirTable with the draft script
8. **After**: Test with sample SSOT records
9. **Finally**: Refine checklists based on team feedback

---

## Appendix

### A. Agent Research Summaries

#### Documentation Scraper Agent
- Gathered comprehensive API documentation for AirTable, Google Docs, and YouTube APIs
- Key finding: AirTable webhooks can trigger external services, but native scripts cannot make external API calls

#### AirTable Base Explorer Agent
- ✅ Schema exploration completed December 23, 2025
- Discovered all relevant field names and IDs for SSOT and All Tasks tables
- Identified bidirectional linked record relationship: SSOT ↔ All Tasks via `Featured Content (SST)`
- Discovered deprecated Content Calendar table (indicated by "(SUNSET)" suffix)
- Confirmed migration to 📑 All Tasks with 18 platform options (vs. old 3 options)

#### Checklist Template Evaluator Agent
- **Recommendation**: Use Markdown files in repository over Google Docs
- Rationale: Simpler parsing, version control, template variables
- Migration: Convert existing Google Doc checklists to Markdown format

#### AirTable Automation Capabilities Agent
- **Recommendation**: Native AirTable automation with script action
- All core requirements achievable without external services
- Script can create multiple records, populate checklists, and manage links
- 30-second timeout and monthly run limits are sufficient for expected volume

### B. Reference Documentation

- **AirTable API**: https://airtable.com/developers/web/api/introduction
- **AirTable Automations**: https://support.airtable.com/docs/getting-started-with-airtable-automations
- **AirTable Scripting**: https://airtable.com/developers/scripting/api
- **Google Docs API**: https://developers.google.com/workspace/docs/api/reference/rest
- **YouTube Data API**: https://developers.google.com/youtube/v3/docs

### C. Files Created

- `/docs/DESIGN_DOCUMENT.md` - This document
- `/.gitignore` - Excludes .env and other sensitive files
- `/.env` - Contains AirTable Personal Access Token (not committed)

---

**Document Maintainer**: PBS Wisconsin Development Team
**Last Updated**: December 23, 2025
