---
name: ticket
description: Create, query, and update support tickets via the ticket MCP server. Use this when users need to create a support request, check ticket status, or when FAQ cannot answer their question.
metadata: '{"nanobot":{"emoji":"🎫","always":true}}'
---

# Ticket Management

## Available MCP Tools

All ticket operations go through the **ticket** MCP server. The tools are:

| Tool | Description |
|------|-------------|
| `mcp_ticket_create_ticket` | Create a new support ticket |
| `mcp_ticket_get_ticket` | Get ticket details by ID |
| `mcp_ticket_list_user_tickets` | List all tickets for a user |
| `mcp_ticket_update_ticket` | Update ticket status or add a comment |
| `mcp_ticket_submit_feedback` | Record satisfaction rating and feedback for a ticket |

## Tool Parameters

### create_ticket

| Parameter | Required | Description |
|-----------|----------|-------------|
| `title` | Yes | Brief one-line summary of the issue |
| `description` | Yes | Detailed description of the problem |
| `priority` | No | `low`, `medium` (default), `high`, or `urgent` |
| `user_id` | Yes | The user's ID from the platform |
| `user_name` | No | The user's display name |
| `platform` | No | Source platform: `feishu`, `dingtalk`, `telegram` |

### get_ticket

| Parameter | Required | Description |
|-----------|----------|-------------|
| `ticket_id` | Yes | The ticket ID to look up |

### list_user_tickets

| Parameter | Required | Description |
|-----------|----------|-------------|
| `user_id` | Yes | The user's ID |
| `status` | No | Filter by: `open`, `in_progress`, `resolved`, `closed` |

### update_ticket

| Parameter | Required | Description |
|-----------|----------|-------------|
| `ticket_id` | Yes | The ticket ID to update |
| `status` | No | New status value |
| `comment` | No | Comment text to add |

### submit_feedback

| Parameter | Required | Description |
|-----------|----------|-------------|
| `ticket_id` | Yes | The ticket ID to rate |
| `rating` | Yes | Satisfaction score: 1 (very dissatisfied) to 5 (very satisfied) |
| `feedback` | No | Optional free-text feedback |

## When to Create a Ticket

| Scenario | Priority | Example |
|----------|----------|---------|
| Service outage or data loss | `urgent` | "My data dashboard is completely empty!" |
| Blocking issue, can't work | `high` | "I can't log into my account" |
| FAQ miss, feature question | `medium` | "How do I set up a custom integration?" |
| User explicitly asks for human | `high` | "I want to speak to a real person" |
| Complaint or frustration | `high` | "Your service is terrible, this is broken" |
| Minor suggestion or typo | `low` | "There's a spelling error on the pricing page" |

## Status Update Workflow

1. When a user asks about a previous ticket, call `list_user_tickets` first to find it
2. Call `get_ticket` for the specific ticket to show full details
3. If the user says the issue is resolved, call `update_ticket` with `status: "resolved"`
4. If the user provides additional info, call `update_ticket` with the info as a `comment`

## Escalation (问题升级)

Escalation is a distinct action from normal ticket creation — it involves **human handoff** with explicit confirmation and SLA tracking.

### When to Escalate

| Trigger | Action |
|---------|--------|
| User explicitly says "转人工" / "speak to a human" | Escalate immediately, no FAQ attempt |
| Same issue recurs 3+ times without resolution | Escalate with summary of previous attempts |
| Service outage or data loss reported | Escalate, then create urgent ticket |
| User is visibly frustrated or angry | Acknowledge feelings first, then escalate |
| Security incident or data breach suspected | Escalate immediately with minimal questions |

### SLA Tiers

| Priority | Human Response | Ticket Created As |
|----------|---------------|-------------------|
| `urgent` | within 30 minutes | urgent |
| `high` | within 4 hours | high |
| `medium` | within 24 hours | medium |
| `low` | within 72 hours | low |

### Escalation Protocol

Step by step:

1. **Acknowledge** — Validate the user's concern first
2. **Create ticket** — Always `urgent` or `high` priority for escalated issues
3. **Confirm handoff** — Tell the user exactly when and how they'll be contacted
4. **Record reason** — Include the escalation trigger in the ticket description

### Escalation Response Templates

**User requests human:**
```
我理解您需要人工协助。我已经为您创建了一个紧急工单：

- **工单号:** TK-XXXXXXXX
- **优先级:** urgent
- **预计响应:** 30 分钟内

我们的技术支持团队会通过当前平台（飞书/钉钉）直接联系您。在此之前，您可以随时向我查询工单进度。
```

**Recurring unresolved issue:**
```
我注意到这个问题已经出现了多次但尚未完全解决。为了确保不再耽误您的时间，我已将工单 TK-XXXXXXXX 升级为紧急优先级，并附上了前几次的处理记录。

技术团队将在 30 分钟内介入处理。给您带来的不便深表歉意。
```

**Frustrated user:**
```
我完全理解您的 frustration —— 这个问题确实影响您的工作。让我立刻为您升级处理。

已创建紧急工单 TK-XXXXXXXX，团队会在 30 分钟内联系您。如果这期间有任何变化，您也可以直接告诉我。
```

### Post-Escalation Follow-up

- After escalation, do NOT close the conversation — let the user know they can still use the bot for other questions
- If the user asks about the escalated ticket later, call `get_ticket` to show the latest status and human agent's comments
- When the human agent resolves the ticket, the bot will see the resolution in the ticket comments on next query

## Satisfaction Feedback (满意度评价)

After a ticket is resolved, proactively ask the user for a satisfaction rating. Do NOT ask for feedback on escalating or in-progress tickets — only resolved ones.

### When to Ask

| Scenario | Action |
|----------|--------|
| User says issue is fixed / resolved | Ask for rating immediately |
| Ticket status changed to resolved | Ask for rating if user is still in conversation |
| User returns after ticket was resolved | Mention the resolution, then ask for rating |
| Ticket is open / in_progress | Do NOT ask for feedback yet |

### How to Ask

1. **Confirm resolution first** — Verify the issue is actually resolved
2. **Ask naturally** — Don't use a survey form tone, make it conversational
3. **Record the rating** — Call `submit_feedback` with the ticket_id and rating
4. **Respond appropriately** — Match your reply to the rating level

### Response Templates

**Rating 4-5 (satisfied):**
```
感谢您的评价！很高兴能帮您解决问题。如果后续有任何需要，随时找我。
```

**Rating 3 (neutral):**
```
感谢反馈。如果还有改进空间，欢迎告诉我具体哪里可以做得更好。
```

**Rating 1-2 (dissatisfied):**
```
感谢您的坦诚反馈。我很抱歉这次服务没有达到您的期望。我会立即将您的意见升级给团队，我们会在 24 小时内与您联系跟进。
```
→ After this, call `update_ticket` to reopen the ticket with priority `high` and a comment explaining the low rating.

### Example

**User:** "好了，数据同步恢复正常了"
**Bot:**
```
太好了！很高兴问题解决了。

在关闭工单之前，能否给这次服务打个分？（1-5 分，5 分最满意）
```
**User:** "4 分"
**Bot:** → calls `mcp_ticket_submit_feedback(ticket_id="TK-xxx", rating=4)`
```
感谢您的评价！如果后续有任何需要，随时找我。
```

## Response Examples

**Creating a ticket:**
```
I've created a support ticket for you:
- **Ticket ID:** TK-A3F8B2C1
- **Title:** Cannot export data to CSV
- **Priority:** medium
- **Status:** open

Our team will follow up within 24 hours. You can check the status anytime by asking me.
```

**Checking a ticket:**
```
Here's your ticket status:
- **TK-A3F8B2C1:** Cannot export data to CSV
  Status: in_progress | Priority: medium
  Created: 2026-05-15 | Updated: 2026-05-16
  Latest comment: "Investigating the export module, will update soon."
```

**Updating a ticket:**
```
I've updated your ticket TK-A3F8B2C1 — status changed to resolved.
Glad we could help! Feel free to reach out if you need anything else.
```
