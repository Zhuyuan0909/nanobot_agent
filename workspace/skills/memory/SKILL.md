---
name: memory
description: Record key personal information and important context to MEMORY.md. Use edit_file to surgically update memory whenever important information is detected.
metadata: '{"nanobot":{"emoji":"🧠","always":true}}'
---

# Memory Recording

This is a **single-user, multi-platform** setup. The same person uses the bot across DingTalk, Feishu, and other channels — all platforms share one MEMORY.md via `unified_session`.

## What to Record

### Personal Information (always record)
| Category | Examples |
|----------|----------|
| Name / identity | "我叫张三", "call me John" |
| Company / organization | "公司在字节跳动", "I work at Acme Corp" |
| Role / title | "我是后端工程师", "I'm the CTO" |
| Contact preferences | "以后用英文回复我", "don't use tables" |
| Account / user ID | User ID, account number from the platform |

### Important Business Context (always record)
| Category | Examples |
|----------|----------|
| Project details | "我们在做数据迁移", "migrating to new API version" |
| Technical environment | "用的是 PostgreSQL 15", "running on AWS" |
| Past issues & resolutions | "上次登录问题已经解决了", "the export bug was fixed in v2.3" |
| Feature requests | "希望能支持批量导出", "we need SSO integration" |
| Escalation notes | "这个客户是 VIP", "需要优先处理" |

### Do NOT record
- Greetings, small talk, casual chat
- One-time troubleshooting steps that were already answered
- Duplicate information already in the file

## MEMORY.md Format

```
# Long-term Memory

## Personal Information
- **Name:** [name]
- **Company:** [company]
- **Role:** [role]

## Preferences
- [preference]

## Project Context
- [project/issue detail]

## Important Notes
- [note]
```

Keep it simple — flat sections, no per-user subsections needed since this is single-user.

## Coexistence with Dream

Dream runs periodically to deduplicate and organize MEMORY.md. Use **surgical edits** so your changes and Dream's changes don't conflict:
- Use `edit_file` for targeted insertions/updates, NOT `write_file` for full rewrites
- This ensures Dream's concurrent edits won't be overwritten

## Process

### Step 1: Read current MEMORY.md
Call `read_file("memory/MEMORY.md")` to see existing records.

### Step 2: Determine what's new
Compare the user's message against what's already recorded. Only edit if there's genuinely new or changed information.

### Step 3: Edit surgically
Use `edit_file("memory/MEMORY.md", old_string, new_string)`:
- **Adding a new entry**: use the section header as `old_string`, append the new line(s) after it in `new_string`
- **Updating an existing entry**: use the exact line as `old_string`, replace with corrected version in `new_string`
- Always include surrounding context in `old_string` for a unique match

## Examples

**User:** "我叫王小明，在美团工作"
**Action:**
1. Read MEMORY.md → no existing name
2. `edit_file` with `old_string="## Personal Information"`, `new_string="## Personal Information\n- **Name:** 王小明\n- **Company:** 美团"`

**User:** "我换到后端组了" (previously: 前端工程师)
**Action:**
1. Read MEMORY.md → found `- **Role:** 前端工程师`
2. `edit_file` with `old_string="- **Role:** 前端工程师"`, `new_string="- **Role:** 后端工程师"`

**User:** "我们换到 AWS 了"
**Action:**
1. Read MEMORY.md → section `## Project Context` exists but no AWS mention
2. `edit_file` with `old_string="## Project Context"`, `new_string="## Project Context\n- 已迁移到 AWS"`

**User:** "你好" (no recordable info)
**Action:** Do nothing. Don't read or write — no memory-relevant content.
