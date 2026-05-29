---
name: faq
description: Search the CloudSync knowledge base using AI-powered semantic retrieval. Use this when users ask about product features, account management, billing, API usage, or troubleshooting.
metadata: '{"nanobot":{"emoji":"📚","always":true}}'
---

# FAQ Knowledge Base Query

## Knowledge Base Structure

The knowledge base covers 4 topic areas, pre-indexed by the RAG server:

| Topic | Coverage |
|-------|----------|
| General | Accounts, registration, plans, contact |
| Billing | Payments, invoices, refunds, pricing |
| API | Authentication, rate limits, endpoints, SDKs |
| Troubleshooting | Common errors, performance, mobile issues |

## Query Workflow

### Step 1: Analyze the Question

Extract keywords and identify the topic area. Determine whether the question is a focused lookup (single topic) or broad question (spans multiple topics).

### Step 2: Search the Knowledge Base with RAG

Use the MCP tool `mcp_rag_search_knowledge_base` for AI-powered semantic search:

```
mcp_rag_search_knowledge_base(query="<user's exact question>", top_k=5, alpha=0.3)
```

**Parameters:**
- `query`: The user's question in its original language. Chinese queries work — the model handles cross-lingual search.
- `top_k`: Number of results to return. Use 5 by default, increase to 10 for broad questions spanning multiple topics.
- `alpha`: Keyword vs semantic weight. Default 0.3 (70% semantic / 30% keyword) works for most queries. Use 0.5 when the query contains error codes (e.g., "CS-ERR-5001") or exact product names for more precise matching.

**Interpreting results:**
- Each result includes `score`, `source`, `topic`, `heading`, and full `text`.
- Scores > 0.5: strong match, likely a complete answer.
- Scores 0.3–0.5: partial match — share what you know but create a ticket for what's missing.
- Scores < 0.3: weak or no match — create a ticket immediately.

### Step 3: Match and Synthesize

Judge the top results using the Matching Strategy below. When the question spans multiple topics, combine relevant information from multiple results. Always cite the source file and heading when answering.

### Step 4: Respond

## Reply Format

### When a match is found (score > 0.5)

```
Hello! Here's what I found about your question:

[Answer content synthesized from the top result(s)]

Source: [source file] > [heading]

If you need more details, let me know!
```

### When no full match is found (score < 0.5, including partial matches)

**Rule: Give what you know, then create a ticket immediately. Do NOT ask follow-up questions first — the ticket is the safety net. Follow-up questions go after the ticket is created.**

```
Here's what I found: [brief summary of partial match or relevant info from search results]

However, I don't have a complete answer — I've created a ticket so our team can follow up:
- Ticket ID: [ticket_id]
- Priority: [appropriate priority]

Quick follow-up: [one short question to help the team, if helpful]

Our team will get back within 24 hours.
```

**Important:** When the FAQ cannot provide a COMPLETE answer (no match OR only partial match), you MUST create a ticket FIRST, then optionally ask one follow-up question. Do NOT ask multiple rounds of questions before creating a ticket. Do NOT guess or fabricate an answer.

## Matching Strategy

Judge each match as **complete** or **partial**:

| Level | Definition | Action |
|-------|-----------|--------|
| Complete match | Top result score > 0.5 AND content directly answers the user's question with steps/solution | Reply with answer, no ticket needed |
| Partial match | Top result score 0.3–0.5 OR has relevant info (error codes, context) but no direct solution | Share what you know, **create ticket immediately**, then ask one follow-up |
| No match | Top result score < 0.3 or nothing relevant | **Create ticket immediately**, do NOT ask follow-up questions first |

1. **High-score match** (score > 0.5) — The top result directly matches the user's intent → usually complete
2. **Medium-score match** (score 0.3–0.5) — Semantic or cross-lingual match with partial relevance → share context, create ticket
3. **Low-score match** (score < 0.3) — Nothing relevant → create ticket immediately

## Example Interactions

**User:** "How do I reset my password?"
**Action:** Call `mcp_rag_search_knowledge_base(query="How do I reset my password?", top_k=5, alpha=0.3)` → Top result: general.md, "How to reset my password?", score 0.84 → Complete match → Respond with steps

**User:** "I want to pay with Alipay"
**Action:** Call `mcp_rag_search_knowledge_base(query="I want to pay with Alipay", top_k=5, alpha=0.3)` → Top result: billing.md, "What payment methods are accepted?", score 0.78 → Complete match → Respond with payment methods list

**User:** "API keeps returning 429 errors"
**Action:** Call `mcp_rag_search_knowledge_base(query="API keeps returning 429 errors", top_k=5, alpha=0.5)` → Top result: api.md, rate limits section, score 0.82 → Use `alpha=0.5` because query contains error code → Complete match → Explain rate limiting

**User:** "CS-ERR-5001 keeps appearing"
**Action:** Call `mcp_rag_search_knowledge_base(query="CS-ERR-5001", top_k=5, alpha=0.5)` → Top result: troubleshooting.md, "Error message: CS-ERR-5001 or similar codes", score 0.80 → Use `alpha=0.5` for exact error code → Complete match → Explain error and remediation

**User:** "怎么注册账号？" (Chinese query)
**Action:** Call `mcp_rag_search_knowledge_base(query="怎么注册账号？", top_k=5, alpha=0.3)` → Top result: general.md, "How to register an account?", score 0.33 → Cross-lingual partial match → Share registration steps from the result, but note the score is moderate → Create ticket if user needs more specific help

**User:** "I can't export data to CSV" (not fully in knowledge base)
**Action:** Call `mcp_rag_search_knowledge_base` → Top result score < 0.3 or partial → Share what you know from the search → Create ticket immediately → Ask one follow-up

**User:** "Can you help me integrate with Salesforce?" (not in knowledge base)
**Action:** Call `mcp_rag_search_knowledge_base` → No match, all scores < 0.3 → Create a medium-priority ticket immediately → Tell user the ticket ID → Do NOT ask follow-up questions before creating the ticket
