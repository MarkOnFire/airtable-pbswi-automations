/**
 * AirTable Scripting Extension - Content Calendar Task Generator
 *
 * Purpose: Create task entries in the All Tasks table for a selected SSOT record,
 * with platform-specific checklists. Also syncs dates when Digital Premiere changes.
 *
 * Setup in AirTable:
 * 1. Go to Extensions (or Apps) panel
 * 2. Add the "Scripting" extension
 * 3. Paste this entire script
 * 4. Run and select an SSOT record when prompted
 *
 * Tables:
 * - Source: ✔️Single Source of Truth (tblTKFOwTvK7xw1H5)
 * - Target: 📑 All Tasks (tblHjG4gyTLO8OeQd)
 *
 * =============================================================================
 * WRITE SCOPE - PROTECTED FIELDS
 * =============================================================================
 * This script has TWO write scopes to protect existing data:
 *
 * CREATE SCOPE (new records only):
 *   1. Task Details                  - Task title
 *   2. Publish Date                  - Digital premiere date (midnight default)
 *   3. Task Start Date               - 2 weeks before Publish Date
 *   4. Platform, Observance, or Note - Platform category
 *   5. Status for Content Calendaring - Workflow status (default: "In Production")
 *   6. Subtasks                      - Checklist content
 *   7. Featured Content (SST)        - Link back to SSOT record
 *
 * UPDATE SCOPE (date sync on existing records, requires confirmation):
 *   1. Publish Date                  - Synced from Digital Premiere
 *   2. Task Start Date               - Recalculated as 2 weeks before
 *
 * This script NEVER deletes records.
 * Date updates require explicit user confirmation via button prompt.
 * =============================================================================
 */

// =============================================================================
// WRITE SCOPE ENFORCEMENT
// =============================================================================

// Fields allowed when CREATING new records
const ALLOWED_CREATE_FIELDS = [
    'Task Details',
    'Publish Date',
    'Task Start Date',
    'Platform, Observance, or Note',
    'Status for Content Calendaring',
    'Subtasks',
    'Featured Content (SST)'
];

// Fields allowed when UPDATING existing records (date sync only)
const ALLOWED_UPDATE_FIELDS = [
    'Publish Date',
    'Task Start Date'
];

/**
 * Validates that record fields only contain allowed write fields.
 * Throws an error if any unauthorized field is detected.
 * @param {Object} recordFields - Fields to validate
 * @param {string} operation - 'create' or 'update'
 */
function enforceWriteScope(recordFields, operation = 'create') {
    const allowedFields = operation === 'update' ? ALLOWED_UPDATE_FIELDS : ALLOWED_CREATE_FIELDS;
    const fieldNames = Object.keys(recordFields);
    const unauthorizedFields = fieldNames.filter(f => !allowedFields.includes(f));

    if (unauthorizedFields.length > 0) {
        throw new Error(
            `WRITE SCOPE VIOLATION (${operation}): Attempted to write to unauthorized fields: ${unauthorizedFields.join(', ')}`
        );
    }
    return true;
}

// Get table references
let ssotTable = base.getTable('✔️Single Source of Truth');
let tasksTable = base.getTable('📑 All Tasks');

// Prompt user to select an SSOT record
output.markdown(`## 🎬 Content Calendar Task Generator

This tool creates checklist tasks for each platform a piece of content needs to be posted to.

**📋 How to use:**
1. Select the SSOT record for your content
2. Choose the platforms the content is scheduled for release on
3. The tool creates a task for each platform with the appropriate checklist

**🗓️ About dates:**
- **Publish Date** = When the content goes live (the Digital Premiere date)
- **Start Date** = 2 weeks before Publish Date — a reminder to get content into systems ahead of launch

**➕ Adding platforms later:** Run this tool again on the same SSOT record. Platforms with existing tasks will be skipped.

**🔄 If the premiere date changes:** Run this tool again — it will detect the date mismatch and offer to sync all tasks.

---

**🎯 Select an SSOT record:**`);

let record = await input.recordAsync('Select SSOT record', ssotTable);

if (!record) {
    output.markdown('❌ No record selected. Exiting.');
    throw new Error('No record selected');
}

let recordId = record.id;
output.markdown(`\n✨ **Selected:** ${record.name || record.id}\n\n---\n`);

// Get field values from SSOT record
let releaseTitle = record.getCellValueAsString('Release Title');
let batchEpisode = record.getCellValueAsString('Batch-Episode');
let premiereDate = record.getCellValue('Digital Premiere');
let ssotPlatforms = record.getCellValue('Platform') || [];

// Use Release Title if available, fall back to Batch-Episode
let projectName = releaseTitle || batchEpisode || 'Untitled';

// Validate premiere date - prompt if not set
let updatedSSOTDate = false;

// Helper to format date as readable string
function formatDate(date) {
    if (typeof date === 'string') date = new Date(date);
    return date.toLocaleDateString('en-US', {weekday: 'long', month: 'long', day: 'numeric', year: 'numeric'});
}

if (!premiereDate) {
    output.markdown('📅 **No Digital Premiere date set on this record.**\n');
    output.markdown('_Note: AirTable scripting doesn\'t support calendar pickers, so please type the date._\n');

    let dateInput = await input.textAsync('Enter premiere date (YYYY-MM-DD, e.g., 2025-03-15):');

    // Also accept common formats and try to parse
    let selectedDate;

    // Try YYYY-MM-DD format first
    if (/^\d{4}-\d{2}-\d{2}$/.test(dateInput)) {
        selectedDate = new Date(dateInput + 'T00:00:00');
    }
    // Try MM/DD/YYYY format
    else if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(dateInput)) {
        selectedDate = new Date(dateInput);
    }
    // Try natural parsing as fallback
    else {
        selectedDate = new Date(dateInput);
    }

    if (isNaN(selectedDate.getTime())) {
        output.markdown('❌ Could not parse that date. Please use YYYY-MM-DD format (e.g., 2025-03-15)');
        throw new Error('Invalid date');
    }

    premiereDate = selectedDate.toISOString();

    // Update the SSOT record with this date (since it was empty)
    try {
        await ssotTable.updateRecordAsync(recordId, {
            'Digital Premiere': selectedDate
        });
        updatedSSOTDate = true;
        output.markdown(`✅ Premiere date set to **${formatDate(selectedDate)}** (updated on SSOT record)\n`);
    } catch (error) {
        output.markdown(`⚠️ Using **${formatDate(selectedDate)}** but couldn't update SSOT: ${error.message}\n`);
    }
}

// =============================================================================
// ALL AVAILABLE PLATFORMS
// =============================================================================

// Platforms with dedicated checklists (shown individually)
// 'name' = SSOT Platform field value (for pre-checking)
// 'target' = All Tasks "Platform, Observance, or Note" value
// 'display' = What shows in the UI
// 'checklist' = Key in checklists object
const PLATFORMS_WITH_CHECKLISTS = [
    {name: 'pbswisconsin.org/openbar', target: 'Media Manager', display: 'Media Manager', checklist: 'Media Manager'},
    {name: 'YouTube', target: 'YouTube', display: 'YouTube', checklist: 'YouTube'},
    {name: 'YouTube Shorts', target: 'YouTube Shorts', display: 'YouTube Shorts', checklist: 'YouTube Shorts'},
    {name: 'Facebook', target: 'Facebook', display: 'Facebook', checklist: 'Facebook'},
    {name: 'GWQS Facebook', target: 'Quilt Show Facebook', display: 'Quilt Show Facebook', checklist: 'Quilt Show Facebook'},
    {name: 'PBS LearningMedia', target: 'PBS LearningMedia', display: 'PBS LearningMedia', checklist: 'PBS LearningMedia'},
    {name: 'Education Website', target: 'Education Website', display: 'Education Website', checklist: 'Education Website'}
];

// Platforms without dedicated checklists (lumped under "Other Platforms")
const OTHER_PLATFORMS = [
    {name: 'quiltshow.com', target: 'Program/Project Website', display: 'quiltshow.com'},
    {name: 'Other - See Notes', target: 'Other Note', display: 'Other - See Notes'}
];

// Get names of platforms already on the SSOT record
let ssotPlatformNames = new Set(ssotPlatforms.map(p => p.name));

// =============================================================================
// CHECKLISTS
// Source: templates/checklists/
// =============================================================================

const checklists = {
    'Essentials': `# Essentials

## File Check
☐ 1080p video
☐ Caption files
☐ Pull stills — ideally three
☐ Post stills to AirTable
☐ Check for clips/digital shorts

## SSoT
☐ Confirm digital release date
☐ Initial draft
☐ Digital copy pass — SEO, headline rework, tags
☐ PR copy edit
☐ Confirm thumbnails with art director/producer
☐ Copy approved for use

## Data check
☐ IMDb entry
☐ EiDR entry
☐ Episode
☐ Edit (needed for sIX posting)
☐ Manifestation (needed for sIX posting)
☐ Confirm on schedule page

## Producer checkpoint
☐ Add embed, PBSWI links and YouTube links to SSoT
☐ Post embed and links in Slack`,

    'YouTube': `# YouTube

☐ Upload
☐ Copy/tags
☐ Thumbnail test (for shorts — set thumbnail via YouTube mobile app)
☐ Caption file
☐ Send collaborator request (where applicable)
☐ Timestamps (where applicable)
☐ Schedule Premiere
☐ (For UPlace) Mark any previous livestream version as "unlisted"`,

    'YouTube Shorts': `# YouTube Shorts

☐ Upload
☐ Copy/tags
☐ Set thumbnail via YouTube mobile app
☐ Caption file
☐ Send collaborator request (where applicable)
☐ Schedule Premiere`,

    'Media Manager': `# Media Manager

☐ Media manager container created
☐ Headline
☐ Copy
☐ Tags
☐ Captions
☐ Still
☐ Set availability
☐ Upload promo as teaser
☐ Upload promo as pre-roll
☐ Add transcript`,

    'Facebook': `# Facebook

☐ Post copy drafted
☐ Image/video selected
☐ Post scheduled
☐ Tags and mentions added
☐ Link preview verified (if applicable)`,

    'Quilt Show Facebook': `# Quilt Show Facebook (GWQS)

☐ Post copy drafted for quilting audience
☐ Relevant images/clips selected
☐ Hashtags prepared
☐ Post scheduled
☐ GWQS Facebook page selected
☐ Cross-tagging with main PBS WI page (if applicable)`,

    'Website': `# Website Publishing

☐ Content ready for website
☐ Page created/updated
☐ Links verified
☐ Cross-promotion scheduled`,

    'PBS LearningMedia': `# PBS LearningMedia

## Create Content Project
☐ Check if one already exists
☐ Outline objects and assets
☐ Create as needed

## Create Objects
☐ Title -> Animated Video | TITLE | Wisconsin Biographies
☐ Video source file -> MP4
☐ Poster image -> Slate
☐ Geo Restrictions -> Worldwide
☐ Related Objects -> Main version
☐ Caption file -> VTT only

## Create Assets
☐ Content Project -> Current collection or season
☐ Title -> Meet X, take a look, etc.
☐ Related objects -> Video, language versions
☐ Poster image -> 16x9
☐ Description -> Card Description
☐ Asset type -> Animation, Video Episode, etc.
☐ Media Type General -> Video
☐ Audience -> BE MINDFUL: For Educators/Teachers if explanatory, For Use with Students if part of lesson
☐ Credits -> Copy from landing page
☐ Ownership and Rights -> © WECB and UW System, Stream/Download/Share, Never Expires
☐ Accessibility Indicators -> Caption, Transcript`,

    'Education Website': `# Education Website

## Asset Check
☐ English Version
☐ Spanish Version (if applicable)
☐ English Captions
☐ Spanish Captions (if applicable)
☐ Thumbnail/slate
☐ Card Image
☐ Masthead Image

## Copy and Content
☐ Copy for story page
☐ Educator Guide
☐ Social Media Descriptions
☐ Project Credits
☐ Title SEO + Keyword report
☐ EiDR entry

## EDU Site Build
☐ Clone previous episode, hide from search
☐ Prep graphics to size, save as WebP
☐ Upload to Kaltura (Video, Captions)
☐ Flow content into web template
☐ Confirm sections: Masthead, Rich Text, Video, Card, Guides, Credits, Sponsor
☐ Yoast SEO Premium
☐ Metadata

## Finalize
☐ Unhide from website
☐ Site Search on sidebar
☐ Yoast -> Allow search engines
☐ Feature on website
☐ Un-feature previous episode
☐ Clear transients`,

    'default': `# Publishing Checklist

☐ Content prepared
☐ Metadata complete
☐ Scheduled for publish
☐ Cross-promotion planned`
};

// =============================================================================
// PLATFORM MAPPING
// Maps SSOT platform names → All Tasks "Platform, Observance, or Note" options
// =============================================================================

const platformMapping = {
    'YouTube': 'YouTube',
    'Facebook': 'Facebook',
    'GWQS Facebook': 'Quilt Show Facebook',
    'pbswisconsin.org/openbar': 'Media Manager',
    'quiltshow.com': 'Program/Project Website',
    'Other - See Notes': 'Other Note'
};

// Maps platforms to their checklist keys
const checklistMapping = {
    'YouTube': 'YouTube',
    'Facebook': 'Facebook',
    'GWQS Facebook': 'Quilt Show Facebook',
    'pbswisconsin.org/openbar': 'Media Manager',
    'quiltshow.com': 'Website',
    'Other - See Notes': 'default'
};

// =============================================================================
// CHECK FOR EXISTING ENTRIES
// Prevent duplicate task creation
// =============================================================================

// Query existing tasks linked to this SSOT record
let existingTasks = await tasksTable.selectRecordsAsync({
    fields: ['Task Details', 'Platform, Observance, or Note', 'Featured Content (SST)', 'Publish Date', 'Task Start Date']
});

let existingPlatforms = new Set();
let existingTasksMap = new Map(); // Maps platform name → {recordId, currentPublishDate, currentStartDate}

// Track potential issues for later warning
let duplicateTasks = []; // Multiple tasks for same platform
let multiLinkedTasks = []; // Tasks linked to multiple SSOT records

for (let task of existingTasks.records) {
    let linkedRecords = task.getCellValue('Featured Content (SST)');
    if (linkedRecords && linkedRecords.some(lr => lr.id === recordId)) {
        let platform = task.getCellValue('Platform, Observance, or Note');

        // Check if this task is linked to multiple SSOT records
        if (linkedRecords.length > 1) {
            multiLinkedTasks.push({
                taskId: task.id,
                taskName: task.getCellValueAsString('Task Details'),
                linkedCount: linkedRecords.length,
                linkedNames: linkedRecords.map(lr => lr.name).join(', ')
            });
        }

        if (platform) {
            // Check for duplicate tasks (same platform, same SSOT)
            if (existingPlatforms.has(platform.name)) {
                duplicateTasks.push({
                    platform: platform.name,
                    taskId: task.id,
                    taskName: task.getCellValueAsString('Task Details')
                });
            }

            existingPlatforms.add(platform.name);
            existingTasksMap.set(platform.name, {
                recordId: task.id,
                taskName: task.getCellValueAsString('Task Details'),
                currentPublishDate: task.getCellValue('Publish Date'),
                currentStartDate: task.getCellValue('Task Start Date')
            });
        }
    }
}

// =============================================================================
// DATA INTEGRITY WARNINGS
// =============================================================================

if (duplicateTasks.length > 0 || multiLinkedTasks.length > 0) {
    output.markdown(`\n### ⚠️ Data Integrity Issues Detected\n`);

    if (duplicateTasks.length > 0) {
        output.markdown(`**🔄 Duplicate tasks found** (multiple tasks for same platform):\n`);
        for (let dup of duplicateTasks) {
            output.markdown(`- ${dup.platform}: "${dup.taskName}"\n`);
        }
        output.markdown(`\n_This usually means tasks were created twice by mistake._\n`);
    }

    if (multiLinkedTasks.length > 0) {
        output.markdown(`**🔗 Tasks linked to multiple SSOT records:**\n`);
        for (let multi of multiLinkedTasks) {
            output.markdown(`- "${multi.taskName}" → linked to ${multi.linkedCount} records (${multi.linkedNames})\n`);
        }
        output.markdown(`\n_This usually means a task was incorrectly linked to multiple content items._\n`);
    }

    output.markdown(`\n**Recommendation:** Review these records in AirTable and clean up duplicates manually before proceeding.\n`);

    let continueChoice = await input.buttonsAsync('How would you like to proceed?', [
        {label: '⚠️ Continue anyway', value: 'continue'},
        {label: '🛑 Stop and fix manually', value: 'stop'}
    ]);

    if (continueChoice === 'stop') {
        output.markdown('\n🛑 Stopped. Please clean up the duplicate/multi-linked records in AirTable, then run this tool again.');
        throw new Error('User chose to stop and fix data issues');
    }

    output.markdown('\n_Continuing with task creation..._\n');
}

// =============================================================================
// PLATFORM SELECTION UI
// =============================================================================

output.markdown(`### 📺 Select platforms to create tasks for:\n\n**Platforms with dedicated checklists:**\n`);

let platformsToCreate = [];

// First, show platforms with dedicated checklists
for (let platform of PLATFORMS_WITH_CHECKLISTS) {
    let targetPlatform = platform.target;
    let hasExistingTask = existingPlatforms.has(targetPlatform);
    let isOnSSOT = ssotPlatformNames.has(platform.name);

    if (hasExistingTask) {
        output.markdown(`- ✅ **${platform.display}** — task exists`);
        continue;
    }

    let prompt = isOnSSOT
        ? `Create task for **${platform.display}**? (on SSOT)`
        : `Create task for **${platform.display}**?`;

    let createTask = await input.buttonsAsync(prompt, [
        {label: 'Yes', value: true, variant: isOnSSOT ? 'primary' : 'default'},
        {label: 'No', value: false}
    ]);

    if (createTask) {
        platformsToCreate.push({
            name: platform.name,
            target: platform.target,
            display: platform.display,
            checklist: platform.checklist
        });
    }
}

// Then, check if any "Other" platforms are on the SSOT or if user wants to add them
let hasOtherOnSSOT = OTHER_PLATFORMS.some(p => ssotPlatformNames.has(p.name));
let otherPlatformNames = OTHER_PLATFORMS.map(p => p.display).join(', ');

// Check if "Other" already has a task
let hasOtherTask = existingPlatforms.has('Other Note') || existingPlatforms.has('Program/Project Website');

output.markdown(`\n**📦 Other platforms** (${otherPlatformNames}):\n`);

if (hasOtherTask) {
    output.markdown(`- ✅ **Other Platforms** — task exists`);
} else {
    let otherPrompt = hasOtherOnSSOT
        ? `Create task for **Other Platforms**? (on SSOT)`
        : `Create task for **Other Platforms**?`;

    let createOther = await input.buttonsAsync(otherPrompt, [
        {label: 'Yes', value: true, variant: hasOtherOnSSOT ? 'primary' : 'default'},
        {label: 'No', value: false}
    ]);

    if (createOther) {
        // Find which specific "other" platform to use (prefer one on SSOT)
        let otherPlatform = OTHER_PLATFORMS.find(p => ssotPlatformNames.has(p.name)) || OTHER_PLATFORMS[0];
        platformsToCreate.push({
            name: otherPlatform.name,
            target: otherPlatform.target,
            display: 'Other Platforms',
            checklist: 'default'
        });
    }
}

// Validate at least one platform selected
if (platformsToCreate.length === 0 && existingTasksMap.size === 0) {
    output.markdown('\n⚠️ No platforms selected. Please select at least one platform.');
    throw new Error('No platforms selected');
}

let platformDisplayNames = platformsToCreate.map(p => p.display);
output.markdown(`\n---\n\n🚀 **Creating tasks for:** ${platformDisplayNames.length > 0 ? platformDisplayNames.join(', ') : '(none)'}\n\n_Each task will include the Essentials checklist plus the platform-specific checklist._\n`);

// Convert to the format expected by the task creation loop
let platforms = platformsToCreate;

// =============================================================================
// CREATE TASK ENTRIES
// =============================================================================

let createdRecords = [];
let skippedRecords = [];
let errors = [];

for (let platform of platforms) {
    let platformName = platform.name;
    let platformDisplay = platform.display || platformName;
    let targetPlatform = platform.target || platformMapping[platformName] || 'Other Note';

    // Skip if task already exists for this platform
    if (existingPlatforms.has(targetPlatform)) {
        skippedRecords.push({
            platform: platformDisplay,
            reason: 'Task already exists'
        });
        continue;
    }

    try {
        // Get platform-specific checklist (use the checklist property from the platform object)
        let checklistKey = platform.checklist || checklistMapping[platformName] || 'default';
        let platformChecklist = checklists[checklistKey] || checklists['default'];

        // Always include Essentials checklist + platform-specific checklist
        let essentialsChecklist = checklists['Essentials'];
        let fullChecklist = `**Project:** ${projectName}\n**Premiere:** ${premiereDate}\n\n---\n\n${essentialsChecklist}\n\n---\n\n${platformChecklist}`;

        // Calculate Task Start Date (2 weeks before Publish Date)
        let publishDate = new Date(premiereDate);
        // Set to midnight for consistent timing
        publishDate.setHours(0, 0, 0, 0);

        let startDate = new Date(publishDate);
        startDate.setDate(startDate.getDate() - 14); // 2 weeks before

        // Build the record fields for All Tasks table
        // ONLY the 7 allowed fields are included here
        let recordFields = {
            'Task Details': releaseTitle && batchEpisode
                ? `${releaseTitle} - ${batchEpisode}`
                : releaseTitle || batchEpisode || 'Untitled',
            'Publish Date': publishDate.toISOString(),
            'Task Start Date': startDate.toISOString().split('T')[0], // Date only (no time)
            'Status for Content Calendaring': {name: 'In Production'},
            'Subtasks': fullChecklist,
            'Featured Content (SST)': [{id: recordId}]
        };

        // Set Platform if there's a valid mapping
        if (targetPlatform) {
            recordFields['Platform, Observance, or Note'] = {name: targetPlatform};
        }

        // ENFORCE WRITE SCOPE - Validates only allowed fields are being written
        // This will throw an error if any unauthorized field is detected
        enforceWriteScope(recordFields);

        // Create the task entry (create only, never update/delete)
        let newRecordId = await tasksTable.createRecordAsync(recordFields);

        createdRecords.push({
            id: newRecordId,
            platform: platformDisplay,
            targetPlatform: targetPlatform
        });

    } catch (error) {
        errors.push({
            platform: platformDisplay,
            error: error.message
        });
    }
}

// =============================================================================
// DATE SYNC FOR EXISTING TASKS
// =============================================================================

let updatedRecords = [];

// Check if there are existing tasks that might need date updates
if (existingTasksMap.size > 0) {
    // Calculate what the dates should be
    let publishDate = new Date(premiereDate);
    publishDate.setHours(0, 0, 0, 0);
    let expectedPublishISO = publishDate.toISOString();

    let startDate = new Date(publishDate);
    startDate.setDate(startDate.getDate() - 14);
    let expectedStartDate = startDate.toISOString().split('T')[0];

    // Find tasks with outdated dates
    let tasksNeedingUpdate = [];
    for (let [platformName, taskInfo] of existingTasksMap) {
        let currentPublish = taskInfo.currentPublishDate ? new Date(taskInfo.currentPublishDate).toISOString() : null;
        let currentStart = taskInfo.currentStartDate;

        if (currentPublish !== expectedPublishISO || currentStart !== expectedStartDate) {
            tasksNeedingUpdate.push({
                platformName,
                ...taskInfo,
                newPublishDate: expectedPublishISO,
                newStartDate: expectedStartDate
            });
        }
    }

    // If there are tasks needing updates, ask user for confirmation
    if (tasksNeedingUpdate.length > 0) {
        output.markdown(`\n---\n\n### 📅 Date Sync Available\n\n**SSOT Digital Premiere:** ${formatDate(premiereDate)}\n`);
        output.markdown(`\nThe following **${tasksNeedingUpdate.length} task(s)** have different dates:\n`);

        for (let task of tasksNeedingUpdate) {
            let currentPub = task.currentPublishDate ? formatDate(task.currentPublishDate) : '(not set)';
            let currentStart = task.currentStartDate || '(not set)';
            output.markdown(`\n**${task.taskName}**`);
            output.markdown(`- Current Publish Date: ${currentPub}`);
            output.markdown(`- Current Start Date: ${currentStart}`);
        }

        output.markdown(`\n**📆 New dates (from SSOT):**`);
        output.markdown(`- Publish Date: **${formatDate(publishDate)}**`);
        output.markdown(`- Start Date: **${formatDate(startDate)}** (2 weeks before)\n`);

        let confirmUpdate = await input.buttonsAsync('Update dates on these existing tasks?', [
            {label: 'Yes, update dates', value: true, variant: 'primary'},
            {label: 'No, skip updates', value: false, variant: 'default'}
        ]);

        if (confirmUpdate) {
            for (let task of tasksNeedingUpdate) {
                try {
                    let updateFields = {
                        'Publish Date': task.newPublishDate,
                        'Task Start Date': task.newStartDate
                    };

                    // ENFORCE UPDATE WRITE SCOPE - Only date fields allowed
                    enforceWriteScope(updateFields, 'update');

                    await tasksTable.updateRecordAsync(task.recordId, updateFields);

                    updatedRecords.push({
                        id: task.recordId,
                        platform: task.platformName,
                        taskName: task.taskName
                    });
                } catch (error) {
                    errors.push({
                        platform: task.platformName,
                        error: `Update failed: ${error.message}`
                    });
                }
            }
        }
    }
}

// =============================================================================
// REPORT RESULTS
// =============================================================================

let summary = `## 🎉 Content Calendar Tasks Created!\n\n`;
summary += `**🎬 Project:** ${projectName}\n`;
summary += `**📅 Digital Premiere:** ${new Date(premiereDate).toLocaleDateString('en-US', {weekday: 'long', month: 'long', day: 'numeric', year: 'numeric'})}\n\n`;

if (createdRecords.length > 0) {
    summary += `### ✅ Created ${createdRecords.length} Task(s)\n`;
    summary += `_Find these in the Content Calendar view:_\n`;
    for (let rec of createdRecords) {
        summary += `• ${rec.platform}\n`;
    }
    summary += '\n';
}

if (updatedRecords.length > 0) {
    summary += `### 📅 Updated ${updatedRecords.length} Task(s) (dates synced)\n`;
    for (let rec of updatedRecords) {
        summary += `• ${rec.taskName}\n`;
    }
    summary += '\n';
}

if (skippedRecords.length > 0) {
    summary += `### ⏭️ Skipped ${skippedRecords.length} (already exist, dates current)\n`;
    for (let rec of skippedRecords) {
        summary += `- ${rec.platform}\n`;
    }
    summary += '\n';
}

if (errors.length > 0) {
    summary += `### ❌ Errors (${errors.length})\n`;
    for (let err of errors) {
        summary += `- ${err.platform}: ${err.error}\n`;
    }
}

if (createdRecords.length === 0 && updatedRecords.length === 0 && skippedRecords.length === 0 && errors.length === 0) {
    summary += `_No platforms to process._\n`;
}

output.markdown(summary);
