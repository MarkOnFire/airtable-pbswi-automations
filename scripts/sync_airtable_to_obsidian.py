#!/usr/bin/env python3
"""
Sync PBS Wisconsin AirTable data to Obsidian vault.

Fetches tasks from Mark's Calendar view and SST content by workflow status,
then writes a consolidated markdown note to the Obsidian vault.

Usage:
    python3 scripts/sync_airtable_to_obsidian.py [--dry-run] [--output PATH]

Environment:
    AIRTABLE_API_KEY: Personal access token (reads from airtable-mcp-server/.env)
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

# Statuses for ongoing assignments (not due-date driven)
ONGOING_STATUSES = ["Milestone", "Ongoing"]

# Statuses to skip (terminal states)
SKIP_STATUSES = ["Complete", "Cancelled", "Denied", "Published"]

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
    "Approved",
]

# SST Media ID prefixes to filter out (promotional content)
# FILL = filler/interstitial, PNGV = planned giving, 4MBR = membership spots
SST_PROMO_PREFIXES = ["FILL", "PNGV", "4MBR"]

OBSIDIAN_VAULT_PATH = Path(
    "/Users/mriechers/Library/Mobile Documents/iCloud~md~obsidian/Documents/MarkBrain"
)
OUTPUT_NOTE_PATH = OBSIDIAN_VAULT_PATH / "1 - PROJECTS" / "PBSWI" / "AIRTABLE.md"

# Load API key from airtable-mcp-server .env
ENV_FILE = Path("/Users/mriechers/Developer/airtable-mcp-server/.env")


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

        categories["ready_for_review"].append({
            "id": record["id"],
            "title": make_sst_title(fields),
            "media_id": media_id,
            "content_type": fields.get("Full-Length, Clip, Livestream", ""),
            "link": format_sst_link(record["id"]),
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
            premiere = parse_date(fields.get("Digital Premiere", ""))
            categories["recently_passed_qc"].append({
                "id": record["id"],
                "title": make_sst_title(fields),
                "qc_date": qc_date,
                "digital_premiere": premiere,
                "content_type": fields.get("Full-Length, Clip, Livestream", ""),
                "link": format_sst_link(record["id"]),
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

            premiere = parse_date(fields.get("Digital Premiere", ""))

            if premiere and premiere < today:
                categories["overdue"].append({
                    "id": record["id"],
                    "title": make_sst_title(fields),
                    "digital_premiere": premiere,
                    "status": fields.get("Single Source Status (BETA)", ""),
                    "content_type": fields.get("Full-Length, Clip, Livestream", ""),
                    "link": format_sst_link(record["id"]),
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
        "--output",
        type=Path,
        default=OUTPUT_NOTE_PATH,
        help="Output file path"
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

    print("Generating markdown...")
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

    print("\nDone!")


if __name__ == "__main__":
    import urllib.parse
    main()
