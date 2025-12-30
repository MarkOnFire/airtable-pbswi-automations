# Platform Publishing Checklists

This directory contains Markdown checklist templates for PBS Wisconsin's video content publishing workflow.

## How These Templates Are Used

When a Digital Premiere Date is set in the SSOT (Single Source of Truth) table, the AirTable automation:
1. Reads the selected platforms from the SSOT record
2. Creates a task entry in the All Tasks table for each platform
3. Populates the `Subtasks` field with the appropriate checklist template

## Template Variables

Templates support the following variables that are replaced at runtime:

| Variable | Description | Example |
|----------|-------------|---------|
| `{project_name}` | Release Title or Batch-Episode from SSOT | "Wisconsin Foodie S15E03" |
| `{premiere_date}` | Digital Premiere date from SSOT | "2025-01-15" |
| `{platform_name}` | Platform name (for generic template) | "Instagram" |

## Available Templates

### Core Platforms (SSOT)
| Template | SSOT Platform | All Tasks Platform |
|----------|---------------|-------------------|
| `youtube.md` | YouTube | YouTube |
| `facebook.md` | Facebook | Facebook |
| `pbs-website.md` | pbswisconsin.org/openbar | Program/Project Website |
| `quiltshow-website.md` | quiltshow.com | Program/Project Website |
| `quilt-show-facebook.md` | GWQS Facebook | Quilt Show Facebook |

### Additional Platforms (All Tasks)
| Template | All Tasks Platform(s) |
|----------|----------------------|
| `instagram.md` | Instagram |
| `instagram-story.md` | Instagram Story |
| `youtube-shorts.md` | YouTube Shorts |
| `media-manager.md` | Media Manager |
| `pbs-learningmedia.md` | PBS LearningMedia |
| `education-platforms.md` | Education Facebook, Education YouTube, Education Website |
| `podcast.md` | Podcast Apps |
| `generic.md` | Other Note, Observance Day, etc. |

## Platform Mapping

The automation script maps SSOT platforms to All Tasks platforms:

```javascript
const platformMapping = {
    'YouTube': 'YouTube',
    'Facebook': 'Facebook',
    'GWQS Facebook': 'Quilt Show Facebook',
    'pbswisconsin.org/openbar': 'Program/Project Website',
    'quiltshow.com': 'Program/Project Website',
    'Other - See Notes': 'Other Note'
};
```

## Customizing Templates

1. **Edit existing templates** to match your team's actual workflow
2. **Add new templates** for additional platforms as needed
3. **Update the automation script** to include new templates

### Template Format

Each template follows this structure:

```markdown
# Platform Publishing Checklist

**Project:** {project_name}
**Premiere Date:** {premiere_date}

---

## Section 1
- [ ] Task item
- [ ] Another task

## Section 2
- [ ] More tasks
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | December 2025 | Initial templates created |

## Feedback

If checklists need updates:
1. Edit the template file in this directory
2. Changes will apply to future automated task entries
3. Existing entries are not automatically updated
