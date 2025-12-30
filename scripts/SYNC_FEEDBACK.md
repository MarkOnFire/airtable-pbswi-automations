# AirTable Sync Feedback

Notes on `sync_airtable_to_obsidian.py` output and behavior.

---

## Current Output

- **Blocked:** Tasks overdue >30 days, grouped by project (with ongoing merged in)
- **[Status-based sections]:** In Progress, In Planning, Awaiting Approval, etc. - grouped by project
- **Ongoing Assignments:** Orphan ongoing items (projects with no other active tasks)
- **Professional Development:** PMDP goals and training
- **Time Off:** Vacation/sick/holiday entries
- **Content Pipeline:** SST items (excludes FILL/PNGV/4MBR promotional content)
  - Ready for Review, Recently Passed QC, Overdue
- **Destination:** `1 - PROJECTS/PBSWI/AIRTABLE.md`

---

## Feedback

<!-- Add notes below about what needs to change -->


---

## Resolved

<!-- Move items here once addressed -->

### 2025-12-29 (Round 2)

- [x] Ongoing assignments merged into project headings (shown with `(ongoing)` marker)
- [x] Status-based headings (In Progress, In Planning, etc.) instead of generic "Active Tasks"
- [x] Filter promotional/Fill items from SST (FILL*, PNGV*, 4MBR* prefixes)

### 2025-12-29 (Round 1)

- [x] Filter to overdue items and things due in the next two weeks
- [x] Professional development and vacation/time off in their own sections
- [x] Overdue >30 days goes under BLOCKED heading
- [x] SST items use Batch-Episode + Media ID as title
- [x] SST links open in SST interface (`pagCh7J2dYzqPC3bH`)
- [x] Task links open in Task Assignments interface (`pagOoMi0UkplilONL`)
- [x] Links go directly from title (no separate "Open in AirTable" text)
- [x] Milestone/Ongoing status items grouped under "Ongoing Assignments" section

