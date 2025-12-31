#!/usr/bin/env python3
"""
Sync PBS Wisconsin AirTable data to Obsidian vault.

This script fetches tasks from AirTable (Mark's Calendar view) and SST content,
then embeds the data into existing Obsidian project notes or creates new ones.

BEHAVIOR:
---------
For each AirTable project:
1. Extracts the base project name (e.g., "ED: Whoopensocker | FY26" → "Whoopensocker")
2. Searches the vault for an existing note with matching name, checking:
   - LEAD — {name}.md
   - QUICK — {name}.md
   - WEEKLY — {name}.md
   - {name}.md (exact match)
3. If found: Appends/updates an "## AirTable Tasks" section at the bottom
4. If not found: Creates a new "LEAD — {name}.md" note in the inbox

The AirTable section is wrapped in HTML comments (<!-- AIRTABLE_SYNC_START --> /
<!-- AIRTABLE_SYNC_END -->) so it can be cleanly replaced on subsequent syncs
without affecting manually-written content in the note.

TASK FILTERING:
---------------
- Skips terminal statuses: Complete, Cancelled, Denied, Published, Approved
- Groups tasks by status: In Progress, In Planning, Awaiting Approval, etc.
- Highlights blocked items (overdue > 30 days)
- Shows ongoing/milestone assignments separately
- Filters out promotional SST content (FILL*, PNGV*, 4MBR* prefixes)

ARCHIVE HANDLING:
-----------------
The script skips the "4 - ARCHIVE" folder when searching for existing notes,
so archived projects won't be updated.

USAGE:
------
    # Normal sync (updates existing notes, creates new ones in inbox)
    python3 scripts/sync_airtable_to_obsidian.py

    # Preview without writing
    python3 scripts/sync_airtable_to_obsidian.py --dry-run

    # Legacy mode (single AIRTABLE.md file, overwrites entirely)
    python3 scripts/sync_airtable_to_obsidian.py --mode legacy

    # Via shell alias (after sourcing workspace_ops aliases)
    airtable-sync
    airtable-sync --dry-run

ENVIRONMENT:
------------
    AIRTABLE_API_KEY: Personal access token
                      Reads from /Users/mriechers/Developer/airtable-mcp-server/.env
                      or falls back to environment variable

SST CONTENT HANDLING:
---------------------
SST (Single Source of Truth) content items are distributed to their related
project notes rather than a single consolidated note:

1. SST items with a linked Project → added to matching project note
2. SST items without a project link → go to "WEEKLY — Content Posting" fallback
3. Due dates are calculated as 30 days before Digital Premiere date

SST sections use separate markers (<!-- AIRTABLE_SST_START/END -->) from
the Tasks section, so both can be updated independently without conflict.

OUTPUT LOCATIONS:
-----------------
    New notes: 0 - INBOX/
    Existing notes: Updated in place wherever found
    Dashboard: 0 - INBOX/AIRTABLE Dashboard.md (or existing location)
    Fallback content: 0 - INBOX/WEEKLY — Content Posting.md

AIRTABLE CONFIGURATION:
-----------------------
    Base ID: appZ2HGwhiifQToB6
    Tasks Table: tblHjG4gyTLO8OeQd (All Tasks)
    SST Table: tblTKFOwTvK7xw1H5
    View: Mark's Calendar (viwsCw3IFVehzcNxs)
"""

import argparse
import json
import os
import re
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict


# Configuration
AIRTABLE_BASE_ID = "appZ2HGwhiifQToB6"
ALL_TASKS_TABLE_ID = "tblHjG4gyTLO8OeQd"
SST_TABLE_ID = "tblTKFOwTvK7xw1H5"
MARKS_CALENDAR_VIEW_ID = "viwsCw3IFVehzcNxs"

# Interface IDs for deep links
TASK_ASSIGNMENTS_INTERFACE = "pagOoMi0UkplilONL"
SST_INTERFACE = "pagCh7J2dYzqPC3bH"

# Special project categories
TIME_OFF_PROJECTS = ["Personal Time Off (Vac/Sick/Legal Holiday)"]
PROFESSIONAL_DEV_PROJECTS = ["Digital FY26 PMDP Goals", "SEMrush | Digital FY26 PMDP Goals"]

# Project name aliases (AirTable name → Obsidian note name)
# Used when the base project name doesn't match the Obsidian note title
PROJECT_ALIASES = {
    "University Place": "UPlace",
    "The Great Wisconsin Quilt Show": "Quilt Show",
    "Wisconsin Life": "WI Life",
    "Wisconsin Foodie": "WI Foodie",
    "John McGivern's Main Streets": "Main Streets",
}

# Statuses for ongoing assignments (not due-date driven)
ONGOING_STATUSES = ["Milestone", "Ongoing"]

# Statuses to skip (terminal states)
SKIP_STATUSES = ["Complete", "Cancelled", "Denied", "Published", "Approved"]

# Order for status-based grouping (most actionable first)
STATUS_ORDER = [
    "In Progress",
    "In Planning",
    "Awaiting Approval",
    "Awaiting Assets",
    "Needs Review",
    "Not Started",
    "On Hold",
    "Delayed",
]

# SST Media ID prefixes to filter out (promotional content)
# FILL = filler/interstitial, PNGV = planned giving, 4MBR = membership spots
SST_PROMO_PREFIXES = ["FILL", "PNGV", "4MBR"]

# Media ID prefix to project name mapping (for fallback matching)
# Prefixes ending with * have variable suffixes
MEDIA_ID_PREFIX_MAP = {
    "9TMM": "30-Minute Music Hour",
    "6AKA": "aka Teacher",
    "6AMT": "American Players Theater",
    "9FTB": "Around the Farm Table",
    "BSWN": "Best of Sewing with Nancy",
    "2CSS": "Candidate Statements",
    "6CWI": "Climate Wisconsin",
    "2CSQ": "Concerts on the Square",
    "9DCU": "Director's Cut",
    "2DCP": "Director's Cut Presents",
    "9DCF": "Director's Cut Wisconsin Film Festival Edition",
    "6DDD": "Dreaming Decolonizing Dinner",
    "6EDP": "Education Promos",
    "6GLE": "Garden Expo",
    "2KGG": "Get Up and Go",
    "6GWQ": "Great Wisconsin Quilt Show",
    "2HNW": "Here and Now",
    "6HNS": "Here and Now Digital Shorts",
    "6DNC": "Here and Now DNC",
    "6HNP": "Here and Now Packages",
    "6RNC": "Here and Now RNC",
    "6HYM": "Hometown Stories Youth Media",
    "6INF": "In Focus with Murv Seymour",
    "6IFT": "Indigenous Food Traditions",
    "2JRY": "Jerry Awards",
    "6JWT": "Judy Woodruff Talk",
    "6LGS": "Let's Grow Stuff",
    "6LSM": "Live from Mead Witter School of Music",
    "2MLK": "Martin Luther King Jr. Day Celebration",
    "6MST": "Matterport Studio Tour",
    "6MTL": "Meet the Lab",
    "6HHA": "Michael Ford: Hip Hop Architect",
    "6NWD": "Noon Wednesday",
    "OUCC": "Once Upon A Christmas Cheery in the Lab of Shakhashiri",
    "6NHB": "PBS Newshour Breaks",
    "6PFP": "Programming Fall Preview",
    "6PRO": "Promos [Captioned]",
    "6PPW": "Promoting PBS Wisconsin",
    "6QFI": "Quick Fit with Cassy",
    "6RES": "Re/sound: Songs of Wisconsin",
    "SCIF": "Science is Fun",
    "6SIF": "Science is Fun Presentations",
    "6SWF": "Sifting, Winnowing and Film Burning",
    "6JSC": "SJMC Journalism Class",
    "2SHC": "State Honors Concert",
    "2SOS": "State of the State",
    "9SOT": "State of the Tribes",
    "6STG": "Style and Grace",
    "6TLB": "The Look Back",
    "6TWS": "The Ways",
    "9UNP": "University Place",
    "2VB2": "UW Varsity Band Spring Concert",
    "6WPS": "Welcome Poets",
    "6WSR": "Whoopensocker",
    "6WRM": "Why Race Matters",
    "6WIB": "Wisconsin Biographies",
    "2GBA": "Wisconsin Budget Address",
    "6WFN": "Wisconsin First Nations",
    "2WIF": "Wisconsin Foodie",
    "2WLI": "Wisconsin Life",
    "6WLI": "Wisconsin Life Digital Shorts",
    "6LIT": "Wisconsin Lighthouses",
    "6IOO": "Wisconsin School of the Air: Instruments of the Orchestra",
    "6KNG": "Wisconsin School of the Air: Kindergarten",
    "6LTD": "Wisconsin School of the Air: Let's Draw",
    "6PWI": "Wisconsin School of the Air: Pioneer Wisconsin",
    "6RMC": "Wisconsin School of the Air: Ranger Mac",
    "6WWN": "Wisconsin School of the Air: Wonderful World of Nature",
    "6YEX": "Wisconsin School of the Air: Young Experimenters",
    "2YAC": "Wisconsin Young Artists Compete: The Final Forte",
    "6WPR": "WPR",
    "6CEN": "WPR Centennial",
    "2BUC": "Bucky!",
}

OBSIDIAN_VAULT_PATH = Path(
    "/Users/mriechers/Library/Mobile Documents/iCloud~md~obsidian/Documents/MarkBrain"
)
INBOX_FOLDER = OBSIDIAN_VAULT_PATH / "0 - INBOX"
PBSWI_FOLDER = OBSIDIAN_VAULT_PATH / "1 - PROJECTS" / "PBSWI"  # For reference
OUTPUT_NOTE_PATH = PBSWI_FOLDER / "AIRTABLE.md"  # Legacy, kept for reference

# Special project names for consolidated notes
CONTENT_PIPELINE_PROJECT = "General Content Planning and Posting"
PROFESSIONAL_DEV_PROJECT = "Professional Development"
TIME_OFF_PROJECT = "Time Off"
CONTENT_FALLBACK_PROJECT = "Content Posting"  # Fallback for unmatched SST items

# Projects table ID (for resolving SST project links)
PROJECTS_TABLE_ID = "tblU9LfZeVNicdB5e"

# Load API key from airtable-mcp-server .env
ENV_FILE = Path("/Users/mriechers/Developer/airtable-mcp-server/.env")

# AirTable section markers for embedding in existing notes
# Tasks section (original)
AIRTABLE_SECTION_START = "<!-- AIRTABLE_SYNC_START -->"
AIRTABLE_SECTION_END = "<!-- AIRTABLE_SYNC_END -->"
# SST Content section (separate, always appended after tasks)
SST_SECTION_START = "<!-- AIRTABLE_SST_START -->"
SST_SECTION_END = "<!-- AIRTABLE_SST_END -->"

# Template for new project notes (matches Obsidian projects-template.md)
NEW_PROJECT_TEMPLATE = """---
tags:
  - all
  - pbswi
  - airtable-sync
created: {created}
status: active
para: projects
---

# {title}

## 🗒 Tasks in this note
```tasks
path includes {{{{query.file.path}}}}
not done
sort by due
sort by priority
```

---

## Resources
*Add links to frequent reference or working documents*


---

## Notes
*To do items will all be collected at the top of the note.*


---

{airtable_section}
"""


def load_api_key() -> str:
    """Load AirTable API key from .env file."""
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                if line.startswith("AIRTABLE_API_KEY="):
                    return line.strip().split("=", 1)[1]

    # Fallback to environment variable
    key = os.environ.get("AIRTABLE_API_KEY")
    if not key:
        raise RuntimeError(
            f"AIRTABLE_API_KEY not found in {ENV_FILE} or environment"
        )
    return key


def airtable_request(endpoint: str, api_key: str, params: dict = None) -> dict:
    """Make authenticated request to AirTable API."""
    base_url = "https://api.airtable.com/v0"
    url = f"{base_url}/{endpoint}"

    if params:
        query_parts = []
        for key, value in params.items():
            if isinstance(value, list):
                for v in value:
                    query_parts.append(f"{key}={urllib.parse.quote(str(v))}")
            else:
                query_parts.append(f"{key}={urllib.parse.quote(str(value))}")
        if query_parts:
            url += "?" + "&".join(query_parts)

    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        raise RuntimeError(f"AirTable API error {e.code}: {error_body}")


def fetch_all_records(table_id: str, api_key: str, view: str = None,
                      formula: str = None) -> list:
    """Fetch all records from a table, handling pagination."""
    records = []
    offset = None

    while True:
        params = {}
        if view:
            params["view"] = view
        if formula:
            params["filterByFormula"] = formula
        if offset:
            params["offset"] = offset

        endpoint = f"{AIRTABLE_BASE_ID}/{table_id}"
        result = airtable_request(endpoint, api_key, params)

        records.extend(result.get("records", []))
        offset = result.get("offset")

        if not offset:
            break

    return records


def fetch_project_names(project_ids: list[str], api_key: str) -> dict[str, str]:
    """
    Fetch project names for a list of project record IDs.

    Returns dict mapping record_id -> project_name
    """
    if not project_ids:
        return {}

    project_map = {}

    # Fetch in batches to avoid formula length limits
    batch_size = 50
    for i in range(0, len(project_ids), batch_size):
        batch_ids = project_ids[i:i + batch_size]

        # Build OR formula for batch
        or_conditions = [f"RECORD_ID() = '{rid}'" for rid in batch_ids]
        formula = f"OR({', '.join(or_conditions)})"

        records = fetch_all_records(
            PROJECTS_TABLE_ID,
            api_key,
            formula=formula
        )

        for record in records:
            project_map[record["id"]] = record.get("fields", {}).get("Project Name", "Unknown Project")

    return project_map


def parse_project_from_task(task_name: str) -> tuple[str, str]:
    """
    Parse task name and project from the Task field.

    Task field format: "Task Details | Project Name"
    Returns: (task_details, project_name)
    """
    if " | " in task_name:
        parts = task_name.split(" | ", 1)
        return parts[0].strip(), parts[1].strip()
    return task_name.strip(), "Uncategorized"


def parse_date(date_str: str) -> datetime.date | None:
    """Parse various date formats to date object."""
    if not date_str:
        return None

    # ISO format (from AirTable dateTime)
    if "T" in date_str or len(date_str) == 10:
        try:
            return datetime.fromisoformat(date_str[:10]).date()
        except ValueError:
            pass

    # M/D/YYYY or M/D/YY format (from QC Date text field)
    patterns = [
        (r"(\d{1,2})/(\d{1,2})/(\d{4})", "%m/%d/%Y"),
        (r"(\d{1,2})/(\d{1,2})/(\d{2})", "%m/%d/%y"),
    ]
    for pattern, fmt in patterns:
        if re.match(pattern, date_str.strip()):
            try:
                return datetime.strptime(date_str.strip()[:10], fmt).date()
            except ValueError:
                pass

    return None


def format_task_link(record_id: str) -> str:
    """Generate AirTable link for a task in Task Assignments interface."""
    return f"https://airtable.com/{AIRTABLE_BASE_ID}/{TASK_ASSIGNMENTS_INTERFACE}/{record_id}"


def format_sst_link(record_id: str) -> str:
    """Generate AirTable link for an SST record in SST interface."""
    return f"https://airtable.com/{AIRTABLE_BASE_ID}/{SST_INTERFACE}/{record_id}"


def is_promotional_content(media_id: str) -> bool:
    """Check if a Media ID indicates promotional/fill content."""
    if not media_id:
        return False

    media_id_upper = media_id.upper()

    # Check explicit prefixes (FILL, PNGV, 4MBR)
    for prefix in SST_PROMO_PREFIXES:
        if media_id_upper.startswith(prefix):
            return True

    return False


def get_project_from_media_id(media_id: str) -> str | None:
    """
    Look up project name from Media ID prefix.

    Media IDs are typically 4-character prefixes (e.g., "2WLI" for Wisconsin Life)
    followed by episode identifiers. This function extracts the prefix and
    returns the associated project name if known.

    Returns None if no match found.
    """
    if not media_id or len(media_id) < 4:
        return None

    # Extract first 4 characters as prefix
    prefix = media_id[:4].upper()

    return MEDIA_ID_PREFIX_MAP.get(prefix)


def extract_completed_record_ids(content: str, section_start: str, section_end: str) -> set[str]:
    """
    Extract AirTable record IDs from completed tasks in an existing section.

    Looks for patterns like:
    - [x] [Title](https://airtable.com/.../recXXX)
    - [X] [Title](https://airtable.com/.../recXXX)

    Returns a set of record IDs (e.g., {"recXXX", "recYYY"})
    """
    completed_ids = set()

    # Check if section exists
    if section_start not in content or section_end not in content:
        return completed_ids

    # Extract section content
    start_idx = content.index(section_start)
    end_idx = content.index(section_end)
    section_content = content[start_idx:end_idx]

    # Pattern to match completed tasks with AirTable links
    # Matches: - [x] or - [X] followed by markdown link to AirTable
    pattern = r'-\s*\[[xX]\]\s*\[[^\]]+\]\(https://airtable\.com/[^/]+/[^/]+/(rec[a-zA-Z0-9]+)\)'

    for match in re.finditer(pattern, section_content):
        record_id = match.group(1)
        completed_ids.add(record_id)

    return completed_ids


def sanitize_filename(name: str) -> str:
    """Convert a project name to a valid filename."""
    # Replace characters that are problematic in filenames
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    result = name
    for char in invalid_chars:
        result = result.replace(char, '-')
    # Collapse multiple dashes/spaces
    result = re.sub(r'[-\s]+', ' ', result).strip()
    # Limit length
    if len(result) > 100:
        result = result[:100].rsplit(' ', 1)[0]
    return result


def find_existing_note(filename: str, vault_path: Path) -> Path | None:
    """
    Search the vault for an existing note with the given filename.
    Returns the path if found, None otherwise.
    Skips the archive folder.
    """
    # Search recursively for the file
    for path in vault_path.rglob(filename):
        if path.is_file():
            # Skip archive folder
            if "/4 - ARCHIVE/" in str(path):
                continue
            return path
    return None


def extract_base_project_name(airtable_project: str) -> str:
    """
    Extract the base project name from an AirTable project string.

    Examples:
    - "ED: Whoopensocker | FY26" → "Whoopensocker"
    - "ED: The Look Back | Season 3 | FY26" → "The Look Back"
    - "Web General Activity" → "Web General Activity"
    - "Final Forte | 2026" → "Final Forte"
    """
    name = airtable_project

    # Remove common prefixes
    prefixes = ["ED: ", "LEAD: ", "WEB: "]
    for prefix in prefixes:
        if name.startswith(prefix):
            name = name[len(prefix):]
            break

    # Take the first segment before " | "
    if " | " in name:
        name = name.split(" | ")[0]

    return name.strip()


def find_project_note(base_name: str, vault_path: Path) -> Path | None:
    """
    Search the vault for an existing project note matching the base name.

    Looks for notes with titles like:
    - "LEAD — {base_name}"
    - "LEAD - {base_name}"
    - "{base_name}"

    Also tries PROJECT_ALIASES if the base name doesn't match directly.

    Returns the path if found, None otherwise.
    Skips the archive folder.
    """
    # Try both the base name and any alias
    names_to_try = [base_name]
    if base_name in PROJECT_ALIASES:
        names_to_try.append(PROJECT_ALIASES[base_name])

    for name in names_to_try:
        # Search for any file containing the name
        # Use a broader search pattern then filter
        search_pattern = f"*{name}*.md"

        # Prioritize exact matches and LEAD-prefixed versions
        exact_matches = []
        lead_matches = []

        for path in vault_path.rglob(search_pattern):
            if not path.is_file():
                continue
            # Skip archive folder
            if "/4 - ARCHIVE/" in str(path):
                continue
            # Skip .obsidian folder
            if "/.obsidian/" in str(path):
                continue

            filename = path.stem  # filename without .md

            # Exact match (just the name)
            if filename == name:
                exact_matches.append(path)
            # Prefixed match (LEAD, QUICK, WEEKLY, etc.)
            elif filename in [
                f"LEAD — {name}",
                f"LEAD - {name}",
                f"QUICK — {name}",
                f"QUICK - {name}",
                f"WEEKLY — {name}",
                f"WEEKLY - {name}",
            ]:
                lead_matches.append(path)
            # Skip other matches to avoid false positives

        # Return in priority order: prefixed first, then exact
        if lead_matches:
            return lead_matches[0]
        if exact_matches:
            return exact_matches[0]

    return None


def generate_airtable_section(
    project_name: str,
    project_data: dict,
    today: datetime.date,
    now: str,
    completed_ids: set[str] = None
) -> str:
    """
    Generate just the AirTable tasks section for embedding in an existing note.

    This creates a marked section that can be replaced on subsequent syncs.
    Items with IDs in completed_ids will be skipped (already marked complete in Obsidian).
    """
    if completed_ids is None:
        completed_ids = set()

    lines = [
        AIRTABLE_SECTION_START,
        "## AirTable Tasks",
        "",
        f"> **Last synced:** {now}",
        "",
    ]

    has_content = False

    # Ongoing assignments (not checkboxes, so don't filter by completed_ids)
    if project_data["ongoing"]:
        has_content = True
        lines.append("### Ongoing Assignments")
        lines.append("")
        for task in project_data["ongoing"]:
            lines.append(f"- [{task['task']}]({task['link']})")
        lines.append("")

    # Blocked tasks (overdue > 30 days)
    blocked_tasks = [t for t in project_data["blocked"] if t["id"] not in completed_ids]
    if blocked_tasks:
        has_content = True
        lines.append("### ⚠️ Blocked")
        lines.append("*Overdue more than 30 days*")
        lines.append("")
        for task in blocked_tasks:
            days_overdue = (today - task["due_date"]).days if task["due_date"] else 0
            lines.append(f"- [ ] [{task['task']}]({task['link']}) *(due {task['due_date']}, {days_overdue}d overdue)*")
        lines.append("")

    # Tasks by status
    status_keys = list(project_data["by_status"].keys())
    ordered_statuses = [s for s in STATUS_ORDER if s in status_keys]
    remaining_statuses = [s for s in status_keys if s not in STATUS_ORDER]
    ordered_statuses.extend(sorted(remaining_statuses))

    for status in ordered_statuses:
        status_tasks = [t for t in project_data["by_status"][status] if t["id"] not in completed_ids]
        if not status_tasks:
            continue

        has_content = True
        lines.append(f"### {status}")
        lines.append("")

        for task in status_tasks:
            if task["due_date"] and task["due_date"] < today:
                days_overdue = (today - task["due_date"]).days
                lines.append(f"- [ ] [{task['task']}]({task['link']}) *(due {task['due_date']}, {days_overdue}d overdue)*")
            elif task["due_date"]:
                lines.append(f"- [ ] [{task['task']}]({task['link']}) *(due {task['due_date']})*")
            else:
                lines.append(f"- [ ] [{task['task']}]({task['link']})")
        lines.append("")

    if not has_content:
        lines.append("*No active tasks from AirTable.*")
        lines.append("")

    lines.append("*This section is automatically synced from AirTable.*")
    lines.append(AIRTABLE_SECTION_END)

    return "\n".join(lines)


def generate_sst_section(
    sst_items: list[dict],
    today: datetime.date,
    now: str,
    completed_ids: set[str] = None
) -> str:
    """
    Generate a separate SST Content section for embedding in a project note.

    Uses distinct markers (SST_SECTION_START/END) so it can be updated
    independently from the AirTable Tasks section.

    Args:
        sst_items: List of SST items for this project
        today: Current date for overdue calculations
        now: Timestamp string for "last synced"
        completed_ids: Set of record IDs already marked complete in Obsidian (to skip)

    Returns:
        Markdown string with the SST section
    """
    if completed_ids is None:
        completed_ids = set()

    # Filter out completed items
    active_items = [item for item in sst_items if item.get("id") not in completed_ids]

    if not active_items:
        return ""

    lines = [
        SST_SECTION_START,
        "## Content Pipeline",
        "",
        f"> **Last synced:** {now}",
        "",
    ]

    # Group by category for cleaner display
    by_category = defaultdict(list)
    for item in active_items:
        by_category[item.get("category", "other")].append(item)

    # Category display order and labels
    category_labels = {
        "ready_for_review": "Ready for Review",
        "recently_passed_qc": "Recently Passed QC",
        "overdue": "Overdue",
    }

    for category in ["overdue", "ready_for_review", "recently_passed_qc"]:
        items = by_category.get(category, [])
        if not items:
            continue

        label = category_labels.get(category, category.replace("_", " ").title())
        if category == "overdue":
            lines.append(f"### ⚠️ {label}")
        else:
            lines.append(f"### {label}")
        lines.append("")

        for item in items:
            title = item.get("title", "Untitled")
            link = item.get("link", "")
            due_date = item.get("due_date")
            premiere = item.get("premiere_date") or item.get("digital_premiere")
            content_type = item.get("content_type", "")

            # Build task line with Obsidian Tasks plugin format
            task_parts = [f"- [ ] [{title}]({link})"]

            # Add due date in Obsidian Tasks format if available
            if due_date:
                task_parts.append(f" 📅 {due_date}")

            lines.append("".join(task_parts))

            # Add metadata on next line
            meta_parts = []
            if premiere:
                meta_parts.append(f"Premiere: {premiere}")
            if content_type:
                meta_parts.append(content_type)
            if item.get("status"):
                meta_parts.append(f"Status: {item['status']}")

            if meta_parts:
                lines.append(f"  - *{' | '.join(meta_parts)}*")

        lines.append("")

    lines.append("*This section is automatically synced from AirTable SST.*")
    lines.append(SST_SECTION_END)

    return "\n".join(lines)


def update_note_with_airtable_section(note_path: Path, airtable_section: str) -> None:
    """
    Update an existing note by replacing or appending the AirTable section.

    If the note already has an AirTable section (marked by comments), replace it.
    Otherwise, append the section at the end of the note.
    """
    content = note_path.read_text()

    # Check if note already has an AirTable section
    if AIRTABLE_SECTION_START in content and AIRTABLE_SECTION_END in content:
        # Replace existing section
        start_idx = content.index(AIRTABLE_SECTION_START)
        end_idx = content.index(AIRTABLE_SECTION_END) + len(AIRTABLE_SECTION_END)
        new_content = content[:start_idx] + airtable_section + content[end_idx:]
    else:
        # Append section at end
        # Ensure there's a separator before the new section
        if not content.endswith("\n\n"):
            if content.endswith("\n"):
                content += "\n"
            else:
                content += "\n\n"
        new_content = content + "---\n\n" + airtable_section + "\n"

    note_path.write_text(new_content)


def update_note_with_sst_section(note_path: Path, sst_section: str) -> None:
    """
    Update an existing note by replacing or appending the SST Content section.

    Uses separate markers (SST_SECTION_START/END) from the Tasks section.
    Always appends at the very end of the note if not already present.
    """
    if not sst_section:
        return

    content = note_path.read_text()

    # Check if note already has an SST section
    if SST_SECTION_START in content and SST_SECTION_END in content:
        # Replace existing section
        start_idx = content.index(SST_SECTION_START)
        end_idx = content.index(SST_SECTION_END) + len(SST_SECTION_END)
        new_content = content[:start_idx] + sst_section + content[end_idx:]
    else:
        # Append section at end (after any existing AirTable Tasks section)
        # Ensure there's a separator before the new section
        if not content.endswith("\n\n"):
            if content.endswith("\n"):
                content += "\n"
            else:
                content += "\n\n"
        new_content = content + "---\n\n" + sst_section + "\n"

    note_path.write_text(new_content)


def create_new_project_note(
    filepath: Path,
    title: str,
    airtable_section: str
) -> None:
    """
    Create a new project note from template with the AirTable section.
    """
    now = datetime.now()
    content = NEW_PROJECT_TEMPLATE.format(
        title=title,
        created=now.strftime("%Y-%m-%d"),
        airtable_section=airtable_section,
    )
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content)


def group_tasks_by_project(tasks: dict) -> dict[str, dict]:
    """
    Reorganize tasks from status-first to project-first grouping.

    Returns dict of project_name -> {
        "blocked": list of tasks,
        "by_status": dict of status -> list of tasks,
        "ongoing": list of tasks,
        "is_special": bool (True for time_off, professional_dev)
    }
    """
    projects = defaultdict(lambda: {
        "blocked": [],
        "by_status": defaultdict(list),
        "ongoing": [],
        "is_special": False,
    })

    # Process blocked tasks
    for task in tasks["blocked"]:
        projects[task["project"]]["blocked"].append(task)

    # Process status-grouped tasks
    for status, status_tasks in tasks["by_status"].items():
        for task in status_tasks:
            projects[task["project"]]["by_status"][status].append(task)

    # Process ongoing tasks
    for project, ongoing_tasks in tasks["ongoing_by_project"].items():
        projects[project]["ongoing"].extend(ongoing_tasks)

    # Handle special categories - merge into their dedicated project notes
    for task in tasks["time_off"]:
        task["project"] = TIME_OFF_PROJECT
        projects[TIME_OFF_PROJECT]["by_status"][task["status"]].append(task)
        projects[TIME_OFF_PROJECT]["is_special"] = True

    for task in tasks["professional_dev"]:
        task["project"] = PROFESSIONAL_DEV_PROJECT
        projects[PROFESSIONAL_DEV_PROJECT]["by_status"][task["status"]].append(task)
        projects[PROFESSIONAL_DEV_PROJECT]["is_special"] = True

    return dict(projects)


def group_sst_by_project(
    sst: dict[str, list[dict]],
    project_id_map: dict[str, str]
) -> dict[str, list[dict]]:
    """
    Reorganize SST content from category-first to project-first grouping.

    Project matching priority:
    1. Linked Project record ID (if present and in project_id_map)
    2. Media ID prefix matching (using MEDIA_ID_PREFIX_MAP)
    3. Falls back to CONTENT_FALLBACK_PROJECT

    Args:
        sst: Dict with keys ready_for_review, recently_passed_qc, overdue
        project_id_map: Dict mapping project record IDs to project names

    Returns:
        Dict mapping project_name -> list of SST items (with category field added)
        Items without a project go under CONTENT_FALLBACK_PROJECT
    """
    projects = defaultdict(list)

    # Process all SST categories
    for category, items in sst.items():
        for item in items:
            project_name = None

            # Priority 1: Linked Project record
            project_id = item.get("project_id")
            if project_id and project_id in project_id_map:
                project_name = project_id_map[project_id]

            # Priority 2: Media ID prefix matching
            if not project_name:
                media_id = item.get("media_id", "")
                project_from_media = get_project_from_media_id(media_id)
                if project_from_media:
                    project_name = project_from_media

            # Priority 3: Fallback
            if not project_name:
                project_name = CONTENT_FALLBACK_PROJECT

            # Add category info to item for rendering
            item_with_category = dict(item)
            item_with_category["category"] = category

            projects[project_name].append(item_with_category)

    # Sort items within each project by due_date (soonest first)
    for project_name in projects:
        projects[project_name].sort(
            key=lambda x: x.get("due_date") or datetime.max.date()
        )

    return dict(projects)


def fetch_tasks(api_key: str) -> dict[str, list[dict]]:
    """
    Fetch active tasks from Mark's Calendar view.

    Returns dict with categorized tasks:
    - blocked: Overdue more than 1 month
    - by_status: Dict of status -> list of tasks (overdue or due within 2 weeks)
    - ongoing_by_project: Dict of project -> list of ongoing tasks
    - time_off: Personal time off items
    - professional_dev: Professional development items
    """
    records = fetch_all_records(
        ALL_TASKS_TABLE_ID,
        api_key,
        view=MARKS_CALENDAR_VIEW_ID
    )

    today = datetime.now().date()
    two_weeks = today + timedelta(days=14)
    one_month_ago = today - timedelta(days=30)

    categories = {
        "blocked": [],
        "by_status": defaultdict(list),
        "ongoing_by_project": defaultdict(list),
        "time_off": [],
        "professional_dev": [],
    }

    for record in records:
        fields = record.get("fields", {})
        status = fields.get("Status", "")

        # Skip terminal statuses
        if status in SKIP_STATUSES:
            continue

        task_full = fields.get("Task", "")
        task_name, project = parse_project_from_task(task_full)
        due_date = parse_date(fields.get("Task Due Date", ""))

        task = {
            "id": record["id"],
            "task": task_name,
            "project": project,
            "status": status or "No Status",
            "due_date": due_date,
            "link": format_task_link(record["id"]),
            "subtasks": fields.get("Subtasks", ""),
        }

        # Categorize the task
        if project in TIME_OFF_PROJECTS:
            categories["time_off"].append(task)
        elif project in PROFESSIONAL_DEV_PROJECTS:
            categories["professional_dev"].append(task)
        elif status in ONGOING_STATUSES:
            # Group ongoing by project for merging into project headings
            categories["ongoing_by_project"][project].append(task)
        elif due_date:
            if due_date < one_month_ago:
                # Overdue more than a month = blocked
                categories["blocked"].append(task)
            elif due_date < today or due_date <= two_weeks:
                # Overdue or due within 2 weeks - group by status
                categories["by_status"][status or "No Status"].append(task)
            # Items due beyond 2 weeks are not shown
        else:
            # No due date but not ongoing - skip for now
            pass

    # Sort blocked by due date
    categories["blocked"].sort(key=lambda t: t["due_date"] or datetime.max.date())

    # Sort tasks within each status by due date
    for status in categories["by_status"]:
        categories["by_status"][status].sort(
            key=lambda t: t["due_date"] or datetime.max.date()
        )

    return categories


def fetch_sst_content(api_key: str) -> dict[str, list[dict]]:
    """
    Fetch SST content organized by workflow category.

    Returns dict with keys:
    - ready_for_review: Items needing copy approval
    - recently_passed_qc: QC passed in last 30 days
    - overdue: Digital premiere passed but not wrapped up
    """
    today = datetime.now().date()
    thirty_days_ago = today - timedelta(days=30)

    categories = {
        "ready_for_review": [],
        "recently_passed_qc": [],
        "overdue": [],
    }

    def make_sst_title(fields: dict) -> str:
        """Create title from Batch-Episode + Media ID."""
        batch = fields.get("Batch-Episode", "")
        media_id = fields.get("Media ID", "")
        if batch and media_id:
            return f"{batch} | {media_id}"
        elif batch:
            return batch
        elif media_id:
            return media_id
        else:
            return fields.get("Release Title", "Untitled")

    # Fetch Ready for Review
    ready_records = fetch_all_records(
        SST_TABLE_ID,
        api_key,
        formula="{Single Source Status (BETA)} = 'Ready for Review'"
    )

    for record in ready_records:
        fields = record.get("fields", {})
        media_id = fields.get("Media ID", "")

        # Skip promotional content
        if is_promotional_content(media_id):
            continue

        # Get project ID (linked record) and premiere date for due date calculation
        project_ids = fields.get("Project", [])
        project_id = project_ids[0] if project_ids else None
        premiere = parse_date(fields.get("Digital Premiere", "")) or parse_date(fields.get("Premiere Date/Time", ""))
        due_date = (premiere - timedelta(days=30)) if premiere else None

        categories["ready_for_review"].append({
            "id": record["id"],
            "title": make_sst_title(fields),
            "media_id": media_id,
            "content_type": fields.get("Full-Length, Clip, Livestream", ""),
            "link": format_sst_link(record["id"]),
            "project_id": project_id,
            "premiere_date": premiere,
            "due_date": due_date,
        })

    # Fetch QC Passed (all, then filter by date in Python)
    qc_records = fetch_all_records(
        SST_TABLE_ID,
        api_key,
        formula="{QC} = 'Passed'"
    )

    for record in qc_records:
        fields = record.get("fields", {})
        media_id = fields.get("Media ID", "")

        # Skip promotional content
        if is_promotional_content(media_id):
            continue

        qc_date = parse_date(fields.get("QC Date", ""))

        if qc_date and qc_date >= thirty_days_ago:
            premiere = parse_date(fields.get("Digital Premiere", "")) or parse_date(fields.get("Premiere Date/Time", ""))
            due_date = (premiere - timedelta(days=30)) if premiere else None

            # Get project ID (linked record)
            project_ids = fields.get("Project", [])
            project_id = project_ids[0] if project_ids else None

            categories["recently_passed_qc"].append({
                "id": record["id"],
                "title": make_sst_title(fields),
                "media_id": media_id,
                "qc_date": qc_date,
                "digital_premiere": premiere,
                "content_type": fields.get("Full-Length, Clip, Livestream", ""),
                "link": format_sst_link(record["id"]),
                "project_id": project_id,
                "premiere_date": premiere,
                "due_date": due_date,
            })

    # Sort by QC date descending
    categories["recently_passed_qc"].sort(
        key=lambda x: x["qc_date"] or datetime.min.date(),
        reverse=True
    )

    # Fetch items with Digital Premiere in past but not wrapped up
    overdue_statuses = [
        "Ready for Review",
        "Ready for Platforms",
        "Scheduled for Hero",
        "In Production",
    ]

    for status in overdue_statuses:
        records = fetch_all_records(
            SST_TABLE_ID,
            api_key,
            formula=f"{{Single Source Status (BETA)}} = '{status}'"
        )

        for record in records:
            fields = record.get("fields", {})
            media_id = fields.get("Media ID", "")

            # Skip promotional content
            if is_promotional_content(media_id):
                continue

            premiere = parse_date(fields.get("Digital Premiere", "")) or parse_date(fields.get("Premiere Date/Time", ""))

            if premiere and premiere < today:
                due_date = (premiere - timedelta(days=30)) if premiere else None

                # Get project ID (linked record)
                project_ids = fields.get("Project", [])
                project_id = project_ids[0] if project_ids else None

                categories["overdue"].append({
                    "id": record["id"],
                    "title": make_sst_title(fields),
                    "media_id": media_id,
                    "digital_premiere": premiere,
                    "status": fields.get("Single Source Status (BETA)", ""),
                    "content_type": fields.get("Full-Length, Clip, Livestream", ""),
                    "link": format_sst_link(record["id"]),
                    "project_id": project_id,
                    "premiere_date": premiere,
                    "due_date": due_date,
                })

    # Deduplicate overdue
    seen_ids = set()
    unique_overdue = []
    for item in categories["overdue"]:
        if item["id"] not in seen_ids:
            seen_ids.add(item["id"])
            unique_overdue.append(item)

    unique_overdue.sort(
        key=lambda x: x["digital_premiere"] or datetime.min.date(),
        reverse=True
    )
    categories["overdue"] = unique_overdue

    return categories


def format_subtasks(subtasks_text: str, indent: str = "  ") -> list[str]:
    """
    Parse subtasks markdown and format for embedding in project notes.

    Subtasks come as markdown with headers and checkboxes:
    **Section**
    [x] Completed item
    [ ] Incomplete item

    Returns list of formatted lines.
    """
    if not subtasks_text or not subtasks_text.strip():
        return []

    lines = []
    for line in subtasks_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        # Section headers become bold sub-items
        if line.startswith("**") and line.endswith("**"):
            section = line[2:-2]
            lines.append(f"{indent}**{section}**")
        # Completed checkbox
        elif line.startswith("[x]") or line.startswith("[X]"):
            item = line[3:].strip()
            lines.append(f"{indent}- [x] {item}")
        # Incomplete checkbox
        elif line.startswith("[ ]"):
            item = line[3:].strip()
            lines.append(f"{indent}- [ ] {item}")
        # Plain text (rare)
        elif line:
            lines.append(f"{indent}{line}")

    return lines


def generate_project_markdown(
    project_name: str,
    project_data: dict,
    today: datetime.date,
    now: str
) -> str:
    """
    Generate markdown for a single project note.

    project_data contains:
    - blocked: list of blocked tasks
    - by_status: dict of status -> list of tasks
    - ongoing: list of ongoing tasks
    - is_special: bool (True for time_off, professional_dev)
    """
    lines = [
        "---",
        "tags:",
        "  - pbswi",
        "  - airtable-sync",
        "  - project",
        "para: inbox",
        f"last_synced: {now}",
        "---",
        "",
        f"# {project_name}",
        "",
        f"> **Last synced:** {now}",
        "",
    ]

    # Ongoing assignments (shown at top as context)
    if project_data["ongoing"]:
        lines.append("## Ongoing Assignments")
        lines.append("")
        for task in project_data["ongoing"]:
            lines.append(f"- [{task['task']}]({task['link']})")
            # Include subtasks if present
            if task.get("subtasks"):
                subtask_lines = format_subtasks(task["subtasks"])
                lines.extend(subtask_lines)
        lines.append("")

    # Blocked tasks (overdue > 30 days)
    if project_data["blocked"]:
        lines.append("## ⚠️ Blocked")
        lines.append("")
        lines.append("*Overdue more than 30 days - needs attention*")
        lines.append("")
        for task in project_data["blocked"]:
            days_overdue = (today - task["due_date"]).days if task["due_date"] else 0
            lines.append(f"- [ ] [{task['task']}]({task['link']}) *(due {task['due_date']}, {days_overdue}d overdue)*")
            if task.get("subtasks"):
                subtask_lines = format_subtasks(task["subtasks"])
                lines.extend(subtask_lines)
        lines.append("")

    # Tasks by status (ordered by STATUS_ORDER)
    status_keys = list(project_data["by_status"].keys())
    ordered_statuses = [s for s in STATUS_ORDER if s in status_keys]
    remaining_statuses = [s for s in status_keys if s not in STATUS_ORDER]
    ordered_statuses.extend(sorted(remaining_statuses))

    for status in ordered_statuses:
        status_tasks = project_data["by_status"][status]
        if not status_tasks:
            continue

        lines.append(f"## {status}")
        lines.append("")

        for task in status_tasks:
            if task["due_date"] and task["due_date"] < today:
                days_overdue = (today - task["due_date"]).days
                lines.append(f"- [ ] [{task['task']}]({task['link']}) *(due {task['due_date']}, {days_overdue}d overdue)*")
            elif task["due_date"]:
                lines.append(f"- [ ] [{task['task']}]({task['link']}) *(due {task['due_date']})*")
            else:
                lines.append(f"- [ ] [{task['task']}]({task['link']})")

            # Include subtasks
            if task.get("subtasks"):
                subtask_lines = format_subtasks(task["subtasks"])
                lines.extend(subtask_lines)

        lines.append("")

    # Footer
    lines.append("---")
    lines.append("*This note is automatically synced from AirTable. Manual edits will be overwritten.*")
    lines.append("")

    return "\n".join(lines)


def generate_content_pipeline_markdown(sst: dict[str, list[dict]], now: str) -> str:
    """
    Generate markdown for the Content Pipeline project note.

    Consolidates all SST content items.
    """
    lines = [
        "---",
        "tags:",
        "  - pbswi",
        "  - airtable-sync",
        "  - project",
        "  - content-pipeline",
        "para: inbox",
        f"last_synced: {now}",
        "---",
        "",
        f"# {CONTENT_PIPELINE_PROJECT}",
        "",
        f"> **Last synced:** {now}",
        "",
    ]

    # Overdue content
    if sst["overdue"]:
        lines.append(f"## ⚠️ Overdue ({len(sst['overdue'])} items)")
        lines.append("")
        lines.append("*Digital premiere passed, awaiting wrap-up*")
        lines.append("")

        for item in sst["overdue"][:20]:
            type_badge = f" | {item['content_type']}" if item["content_type"] else ""
            lines.append(f"- [ ] [{item['title']}]({item['link']}){type_badge}")
            lines.append(f"  - Premiere: {item['digital_premiere']} | Status: {item['status']}")

        if len(sst["overdue"]) > 20:
            lines.append(f"")
            lines.append(f"*...and {len(sst['overdue']) - 20} more*")
        lines.append("")

    # Ready for Review
    if sst["ready_for_review"]:
        lines.append(f"## Ready for Review ({len(sst['ready_for_review'])} items)")
        lines.append("")
        lines.append("*Copy needs approval before scheduling*")
        lines.append("")

        for item in sst["ready_for_review"]:
            type_badge = f" | {item['content_type']}" if item["content_type"] else ""
            lines.append(f"- [ ] [{item['title']}]({item['link']}){type_badge}")
        lines.append("")

    # Recently Passed QC
    if sst["recently_passed_qc"]:
        lines.append(f"## Recently Passed QC ({len(sst['recently_passed_qc'])} items)")
        lines.append("")
        lines.append("*QC passed in last 30 days - ready for platform scheduling*")
        lines.append("")

        for item in sst["recently_passed_qc"]:
            type_badge = f" | {item['content_type']}" if item["content_type"] else ""
            meta = []
            if item["qc_date"]:
                meta.append(f"QC: {item['qc_date']}")
            if item["digital_premiere"]:
                meta.append(f"Premiere: {item['digital_premiere']}")
            meta_str = f" *({', '.join(meta)})*" if meta else ""
            lines.append(f"- [ ] [{item['title']}]({item['link']}){type_badge}{meta_str}")
        lines.append("")

    # Footer
    lines.append("---")
    lines.append("*This note is automatically synced from AirTable. Manual edits will be overwritten.*")
    lines.append("")

    return "\n".join(lines)


def generate_dashboard_markdown(
    projects: dict[str, dict],
    sst: dict[str, list[dict]],
    now: str,
    today: datetime.date
) -> str:
    """
    Generate a dashboard note that links to all project notes.
    """
    lines = [
        "---",
        "tags:",
        "  - pbswi",
        "  - airtable-sync",
        "  - dashboard",
        "para: inbox",
        f"last_synced: {now}",
        "---",
        "",
        "# PBS Wisconsin - AirTable Dashboard",
        "",
        f"> **Last synced:** {now}",
        "",
        "## Active Projects",
        "",
    ]

    # Sort projects, putting special ones last
    regular_projects = []
    special_projects = []
    for name, data in projects.items():
        task_count = (
            len(data["blocked"]) +
            sum(len(v) for v in data["by_status"].values()) +
            len(data["ongoing"])
        )
        if task_count == 0:
            continue

        if data["is_special"]:
            special_projects.append((name, task_count))
        else:
            regular_projects.append((name, task_count))

    for name, count in sorted(regular_projects):
        filename = sanitize_filename(name)
        lines.append(f"- [[{filename}|{name}]] ({count} tasks)")

    # Content Pipeline
    sst_count = len(sst["overdue"]) + len(sst["ready_for_review"]) + len(sst["recently_passed_qc"])
    if sst_count > 0:
        filename = sanitize_filename(CONTENT_PIPELINE_PROJECT)
        lines.append(f"- [[{filename}|{CONTENT_PIPELINE_PROJECT}]] ({sst_count} items)")

    lines.append("")

    # Special projects
    if special_projects:
        lines.append("## Other")
        lines.append("")
        for name, count in sorted(special_projects):
            filename = sanitize_filename(name)
            lines.append(f"- [[{filename}|{name}]] ({count} items)")
        lines.append("")

    # Footer
    lines.append("---")
    lines.append("*This dashboard is automatically synced from AirTable.*")
    lines.append("")

    return "\n".join(lines)


def generate_markdown(tasks: dict[str, list[dict]], sst: dict[str, list[dict]]) -> str:
    """Generate the consolidated markdown note."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    today = datetime.now().date()

    lines = [
        "---",
        "tags:",
        "  - all",
        "  - pbswi",
        "  - airtable-sync",
        "para: projects",
        f"last_synced: {now}",
        "---",
        "",
        "# PBS Wisconsin - AirTable",
        "",
        f"> **Last synced:** {now}",
        "",
        "---",
        "",
    ]

    # Collect all projects that have tasks or ongoing assignments
    # for merging ongoing into project headings
    all_projects = set()
    for task in tasks["blocked"]:
        all_projects.add(task["project"])
    for status_tasks in tasks["by_status"].values():
        for task in status_tasks:
            all_projects.add(task["project"])
    for project in tasks["ongoing_by_project"]:
        all_projects.add(project)

    # BLOCKED section (overdue > 1 month)
    if tasks["blocked"]:
        lines.append("## Blocked")
        lines.append("")
        lines.append("*Overdue more than 30 days - needs attention or removal*")
        lines.append("")

        by_project = defaultdict(list)
        for task in tasks["blocked"]:
            by_project[task["project"]].append(task)

        for project in sorted(by_project.keys()):
            lines.append(f"### {project}")
            lines.append("")

            # Add ongoing assignments for this project
            if project in tasks["ongoing_by_project"]:
                for ongoing in tasks["ongoing_by_project"][project]:
                    lines.append(f"- [{ongoing['task']}]({ongoing['link']}) *(ongoing)*")

            for task in by_project[project]:
                days_overdue = (today - task["due_date"]).days if task["due_date"] else 0
                lines.append(f"- [ ] [{task['task']}]({task['link']}) *(due {task['due_date']}, {days_overdue}d overdue)*")
            lines.append("")

        lines.append("---")
        lines.append("")

    # STATUS-BASED SECTIONS (In Progress, In Planning, etc.)
    # Track which projects have been shown with their ongoing assignments
    projects_with_ongoing_shown = set(
        task["project"] for task in tasks["blocked"]
    )

    # Order statuses according to STATUS_ORDER, then any remaining
    status_keys = list(tasks["by_status"].keys())
    ordered_statuses = [s for s in STATUS_ORDER if s in status_keys]
    remaining_statuses = [s for s in status_keys if s not in STATUS_ORDER]
    ordered_statuses.extend(sorted(remaining_statuses))

    for status in ordered_statuses:
        status_tasks = tasks["by_status"][status]
        if not status_tasks:
            continue

        lines.append(f"## {status}")
        lines.append("")

        by_project = defaultdict(list)
        for task in status_tasks:
            by_project[task["project"]].append(task)

        for project in sorted(by_project.keys()):
            lines.append(f"### {project}")
            lines.append("")

            # Add ongoing assignments if not already shown
            if project in tasks["ongoing_by_project"] and project not in projects_with_ongoing_shown:
                for ongoing in tasks["ongoing_by_project"][project]:
                    lines.append(f"- [{ongoing['task']}]({ongoing['link']}) *(ongoing)*")
                projects_with_ongoing_shown.add(project)

            for task in by_project[project]:
                if task["due_date"] and task["due_date"] < today:
                    days_overdue = (today - task["due_date"]).days
                    lines.append(f"- [ ] [{task['task']}]({task['link']}) *(due {task['due_date']}, {days_overdue}d overdue)*")
                elif task["due_date"]:
                    lines.append(f"- [ ] [{task['task']}]({task['link']}) *(due {task['due_date']})*")
                else:
                    lines.append(f"- [ ] [{task['task']}]({task['link']})")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Show any remaining ongoing assignments that weren't merged into other sections
    orphan_ongoing_projects = [
        p for p in tasks["ongoing_by_project"]
        if p not in projects_with_ongoing_shown
    ]
    if orphan_ongoing_projects:
        lines.append("## Ongoing Assignments")
        lines.append("")
        for project in sorted(orphan_ongoing_projects):
            lines.append(f"### {project}")
            lines.append("")
            for ongoing in tasks["ongoing_by_project"][project]:
                lines.append(f"- [{ongoing['task']}]({ongoing['link']})")
            lines.append("")
        lines.append("---")
        lines.append("")

    # PROFESSIONAL DEVELOPMENT section
    if tasks["professional_dev"]:
        lines.append("## Professional Development")
        lines.append("")
        for task in tasks["professional_dev"]:
            if task["due_date"]:
                lines.append(f"- [ ] [{task['task']}]({task['link']}) *(due {task['due_date']})*")
            else:
                lines.append(f"- [ ] [{task['task']}]({task['link']})")
        lines.append("")
        lines.append("---")
        lines.append("")

    # TIME OFF section
    if tasks["time_off"]:
        lines.append("## Time Off")
        lines.append("")
        for task in tasks["time_off"]:
            if task["due_date"]:
                lines.append(f"- [{task['task']}]({task['link']}) | {task['due_date']}")
            else:
                lines.append(f"- [{task['task']}]({task['link']})")
        lines.append("")
        lines.append("---")
        lines.append("")

    # SST Content sections
    lines.append("## Content Pipeline")
    lines.append("")

    # Overdue
    if sst["overdue"]:
        lines.append(f"### Overdue ({len(sst['overdue'])} items)")
        lines.append("")
        lines.append("*Digital premiere passed, awaiting wrap-up*")
        lines.append("")

        for item in sst["overdue"][:20]:
            type_badge = f" | {item['content_type']}" if item["content_type"] else ""
            lines.append(f"- [ ] [{item['title']}]({item['link']}){type_badge}")
            lines.append(f"  - Premiere: {item['digital_premiere']} | Status: {item['status']}")
            lines.append("")

        if len(sst["overdue"]) > 20:
            lines.append(f"*...and {len(sst['overdue']) - 20} more*")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Ready for Review
    if sst["ready_for_review"]:
        lines.append(f"### Ready for Review ({len(sst['ready_for_review'])} items)")
        lines.append("")
        lines.append("*Copy needs approval before scheduling*")
        lines.append("")

        for item in sst["ready_for_review"]:
            type_badge = f" | {item['content_type']}" if item["content_type"] else ""
            lines.append(f"- [ ] [{item['title']}]({item['link']}){type_badge}")
        lines.append("")

        lines.append("---")
        lines.append("")

    # Recently Passed QC
    if sst["recently_passed_qc"]:
        lines.append(f"### Recently Passed QC ({len(sst['recently_passed_qc'])} items)")
        lines.append("")
        lines.append("*QC passed in last 30 days - ready for platform scheduling*")
        lines.append("")

        for item in sst["recently_passed_qc"]:
            type_badge = f" | {item['content_type']}" if item["content_type"] else ""
            meta = []
            if item["qc_date"]:
                meta.append(f"QC: {item['qc_date']}")
            if item["digital_premiere"]:
                meta.append(f"Premiere: {item['digital_premiere']}")
            meta_str = f" *({', '.join(meta)})*" if meta else ""
            lines.append(f"- [ ] [{item['title']}]({item['link']}){type_badge}{meta_str}")
        lines.append("")

        lines.append("---")
        lines.append("")

    # Footer
    lines.append("*This note is automatically synced from AirTable. Manual edits will be overwritten.*")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Sync AirTable PBS Wisconsin data to Obsidian"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print output instead of writing to file"
    )
    parser.add_argument(
        "--mode",
        choices=["legacy", "projects"],
        default="projects",
        help="Output mode: 'legacy' for single AIRTABLE.md, 'projects' for per-project notes"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_NOTE_PATH,
        help="Output file path (legacy mode only)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=INBOX_FOLDER,
        help="Output directory for project notes (projects mode)"
    )
    args = parser.parse_args()

    print("Loading AirTable API key...")
    api_key = load_api_key()

    print("Fetching tasks from Mark's Calendar...")
    tasks = fetch_tasks(api_key)
    print(f"  Blocked: {len(tasks['blocked'])}")
    total_by_status = sum(len(v) for v in tasks['by_status'].values())
    print(f"  By Status: {total_by_status} tasks across {len(tasks['by_status'])} statuses")
    for status, status_tasks in tasks['by_status'].items():
        print(f"    - {status}: {len(status_tasks)}")
    total_ongoing = sum(len(v) for v in tasks['ongoing_by_project'].values())
    print(f"  Ongoing: {total_ongoing} across {len(tasks['ongoing_by_project'])} projects")
    print(f"  Professional Dev: {len(tasks['professional_dev'])}")
    print(f"  Time Off: {len(tasks['time_off'])}")

    print("Fetching SST content...")
    sst = fetch_sst_content(api_key)
    print(f"  Ready for Review: {len(sst['ready_for_review'])}")
    print(f"  Recently Passed QC: {len(sst['recently_passed_qc'])}")
    print(f"  Overdue: {len(sst['overdue'])}")

    # Resolve project names for SST items
    print("Resolving SST project links...")
    all_project_ids = set()
    for category_items in sst.values():
        for item in category_items:
            if item.get("project_id"):
                all_project_ids.add(item["project_id"])
    project_id_map = fetch_project_names(list(all_project_ids), api_key)
    print(f"  Resolved {len(project_id_map)} projects")

    # Group SST by project
    sst_by_project = group_sst_by_project(sst, project_id_map)
    print(f"  SST distributed across {len(sst_by_project)} projects")
    fallback_count = len(sst_by_project.get(CONTENT_FALLBACK_PROJECT, []))
    if fallback_count > 0:
        print(f"  ({fallback_count} items in fallback '{CONTENT_FALLBACK_PROJECT}')")

    if args.mode == "legacy":
        # Original single-file mode
        print("Generating markdown (legacy mode)...")
        markdown = generate_markdown(tasks, sst)

        if args.dry_run:
            print("\n" + "=" * 60)
            print("DRY RUN - Would write to:", args.output)
            print("=" * 60 + "\n")
            print(markdown)
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with open(args.output, "w") as f:
                f.write(markdown)
            print(f"\nWritten to: {args.output}")

    else:
        # Per-project mode
        print("Grouping tasks by project...")
        projects = group_tasks_by_project(tasks)
        print(f"  Found {len(projects)} projects with active tasks")

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        today = datetime.now().date()

        # Create output directory
        output_dir = args.output_dir
        if not args.dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)

        notes_updated = []
        notes_created = []
        matched_sst_projects = set()  # Track SST projects matched to task projects

        # Generate per-project notes
        for project_name, project_data in projects.items():
            # Skip empty projects
            task_count = (
                len(project_data["blocked"]) +
                sum(len(v) for v in project_data["by_status"].values()) +
                len(project_data["ongoing"])
            )
            if task_count == 0:
                continue

            # Extract base project name and look for existing note
            base_name = extract_base_project_name(project_name)
            existing_note = find_project_note(base_name, OBSIDIAN_VAULT_PATH)

            # Extract completed IDs from existing note (if any)
            completed_task_ids = set()
            completed_sst_ids = set()
            if existing_note and existing_note.exists():
                existing_content = existing_note.read_text()
                completed_task_ids = extract_completed_record_ids(
                    existing_content, AIRTABLE_SECTION_START, AIRTABLE_SECTION_END
                )
                completed_sst_ids = extract_completed_record_ids(
                    existing_content, SST_SECTION_START, SST_SECTION_END
                )

            # Generate the AirTable section (skipping completed items)
            airtable_section = generate_airtable_section(
                project_name, project_data, today, now, completed_task_ids
            )

            # Check for matching SST content for this project
            # Try both full project name and base name since SST uses Project table names
            sst_items = sst_by_project.get(project_name, [])
            matched_sst_key = project_name if sst_items else None
            if not sst_items:
                # Try matching by base name (SST projects may have different naming)
                for sst_proj_name, items in sst_by_project.items():
                    sst_base = extract_base_project_name(sst_proj_name)
                    if sst_base == base_name:
                        sst_items = items
                        matched_sst_key = sst_proj_name
                        break
            if matched_sst_key:
                matched_sst_projects.add(matched_sst_key)
            sst_section = generate_sst_section(sst_items, today, now, completed_sst_ids) if sst_items else ""

            if existing_note:
                # Update existing note with AirTable section
                if args.dry_run:
                    print(f"\n{'=' * 60}")
                    print(f"PROJECT: {project_name}")
                    print(f"  Base name: {base_name}")
                    print(f"  Would UPDATE existing note: {existing_note}")
                    if sst_items:
                        print(f"  SST items: {len(sst_items)}")
                    print(f"{'=' * 60}")
                    print(airtable_section[:500] + "..." if len(airtable_section) > 500 else airtable_section)
                    if sst_section:
                        print("\n--- SST SECTION ---")
                        print(sst_section[:500] + "..." if len(sst_section) > 500 else sst_section)
                else:
                    update_note_with_airtable_section(existing_note, airtable_section)
                    if sst_section:
                        update_note_with_sst_section(existing_note, sst_section)
                    notes_updated.append(existing_note)
            else:
                # Create new note from template in inbox
                filename = f"LEAD — {base_name}.md"
                filepath = output_dir / filename
                title = f"LEAD — {base_name}"

                if args.dry_run:
                    print(f"\n{'=' * 60}")
                    print(f"PROJECT: {project_name}")
                    print(f"  Base name: {base_name}")
                    print(f"  Would CREATE new note: {filepath}")
                    if sst_items:
                        print(f"  SST items: {len(sst_items)}")
                    print(f"{'=' * 60}")
                    print(airtable_section[:500] + "..." if len(airtable_section) > 500 else airtable_section)
                    if sst_section:
                        print("\n--- SST SECTION ---")
                        print(sst_section[:500] + "..." if len(sst_section) > 500 else sst_section)
                else:
                    create_new_project_note(filepath, title, airtable_section)
                    if sst_section:
                        update_note_with_sst_section(filepath, sst_section)
                    notes_created.append(filepath)

        # Handle SST items for projects that have SST content but no tasks
        # (These weren't processed in the main tasks loop above)
        # Iterate over a copy since we may add to fallback during iteration
        for sst_project_name in list(sst_by_project.keys()):
            # Skip if already matched to a task project, or if it's the fallback project
            if sst_project_name in matched_sst_projects:
                continue
            if sst_project_name == CONTENT_FALLBACK_PROJECT:
                continue  # Handle fallback separately below

            sst_items = sst_by_project[sst_project_name]

            # This project has SST content but no tasks - add SST section only
            base_name = extract_base_project_name(sst_project_name)
            existing_note = find_project_note(base_name, OBSIDIAN_VAULT_PATH)

            # Extract completed SST IDs from existing note (if any)
            completed_sst_ids = set()
            if existing_note and existing_note.exists():
                existing_content = existing_note.read_text()
                completed_sst_ids = extract_completed_record_ids(
                    existing_content, SST_SECTION_START, SST_SECTION_END
                )

            sst_section = generate_sst_section(sst_items, today, now, completed_sst_ids)

            if existing_note:
                if args.dry_run:
                    print(f"\n{'=' * 60}")
                    print(f"SST-ONLY PROJECT: {sst_project_name}")
                    print(f"  Base name: {base_name}")
                    print(f"  Would UPDATE existing note: {existing_note}")
                    print(f"  SST items: {len(sst_items)}")
                    print(f"{'=' * 60}")
                    print(sst_section[:500] + "..." if len(sst_section) > 500 else sst_section)
                else:
                    update_note_with_sst_section(existing_note, sst_section)
                    if existing_note not in notes_updated:
                        notes_updated.append(existing_note)
            else:
                # No existing note found - these items go to fallback
                sst_by_project[CONTENT_FALLBACK_PROJECT] = (
                    sst_by_project.get(CONTENT_FALLBACK_PROJECT, []) + sst_items
                )

        # Handle fallback note for unmatched SST items (WEEKLY — Content Posting)
        fallback_items = sst_by_project.get(CONTENT_FALLBACK_PROJECT, [])
        if fallback_items:
            fallback_filename = f"WEEKLY — {CONTENT_FALLBACK_PROJECT}.md"
            existing_fallback = find_existing_note(fallback_filename, OBSIDIAN_VAULT_PATH)
            fallback_path = existing_fallback if existing_fallback else output_dir / fallback_filename

            # Extract completed SST IDs from existing fallback note (if any)
            completed_fallback_ids = set()
            if existing_fallback and existing_fallback.exists():
                existing_content = existing_fallback.read_text()
                completed_fallback_ids = extract_completed_record_ids(
                    existing_content, SST_SECTION_START, SST_SECTION_END
                )

            fallback_section = generate_sst_section(fallback_items, today, now, completed_fallback_ids)

            if args.dry_run:
                print(f"\n{'=' * 60}")
                print(f"FALLBACK: {CONTENT_FALLBACK_PROJECT}")
                print(f"  Items: {len(fallback_items)}")
                if existing_fallback:
                    print(f"  Would UPDATE existing: {fallback_path}")
                else:
                    print(f"  Would CREATE new: {fallback_path}")
                print(f"{'=' * 60}")
                print(fallback_section[:500] + "..." if len(fallback_section) > 500 else fallback_section)
            else:
                if existing_fallback:
                    update_note_with_sst_section(existing_fallback, fallback_section)
                    notes_updated.append(fallback_path)
                else:
                    # Create new fallback note with just the SST section
                    fallback_content = f"""---
tags:
  - all
  - pbswi
  - airtable-sync
  - content-pipeline
created: {datetime.now().strftime("%Y-%m-%d")}
status: active
para: projects
---

# WEEKLY — {CONTENT_FALLBACK_PROJECT}

Unmatched content items that couldn't be assigned to a specific project.

---

{fallback_section}
"""
                    fallback_path.parent.mkdir(parents=True, exist_ok=True)
                    fallback_path.write_text(fallback_content)
                    notes_created.append(fallback_path)

        # Generate Dashboard note (still uses full-note approach)
        dashboard_filename = "AIRTABLE Dashboard.md"
        existing_dashboard = find_existing_note(dashboard_filename, OBSIDIAN_VAULT_PATH)
        dashboard_path = existing_dashboard if existing_dashboard else output_dir / dashboard_filename
        dashboard_markdown = generate_dashboard_markdown(projects, sst, now, today)

        if args.dry_run:
            print(f"\n{'=' * 60}")
            print("DASHBOARD")
            if existing_dashboard:
                print(f"Would UPDATE existing: {dashboard_path}")
            else:
                print(f"Would CREATE new: {dashboard_path}")
            print(f"{'=' * 60}")
            print(dashboard_markdown)
        else:
            with open(dashboard_path, "w") as f:
                f.write(dashboard_markdown)
            if existing_dashboard:
                notes_updated.append(dashboard_path)
            else:
                notes_created.append(dashboard_path)

        if not args.dry_run:
            def rel_path(fp):
                try:
                    return str(fp.relative_to(OBSIDIAN_VAULT_PATH))
                except ValueError:
                    return str(fp)

            if notes_updated:
                print(f"\nUpdated {len(notes_updated)} existing notes:")
                for fp in notes_updated:
                    print(f"  - {rel_path(fp)}")

            if notes_created:
                print(f"\nCreated {len(notes_created)} new notes in inbox:")
                for fp in notes_created:
                    print(f"  - {rel_path(fp)}")

    print("\nDone!")


if __name__ == "__main__":
    import urllib.parse
    main()
