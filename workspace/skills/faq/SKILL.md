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

### Step 0: Diagnose — Is This Question Answerable?

**Before searching, pause and classify the user's question.** A vague question searched blindly produces irrelevant results and wastes the user's time. A good Agent diagnoses first, searches second.

**Vague / under-specified (DO NOT search yet — ask clarifying questions first):**
- Missing key details: "Something's wrong with my data", "It's not working", "I have a problem"
- Ambiguous scope: "Help me with billing", "Tell me about the API", "I need account help"
- No error context: "I got an error", "The sync failed" (which error? which sync?)
- Broad complaints: "The dashboard is messed up", "My account is broken"

**Specific / actionable (proceed to Step 1 and search immediately):**
- Contains error codes: "CS-ERR-5001", "Getting 429 errors", "Error 401 on API"
- Names exact features: "How to set up a webhook?", "Where to download invoices?"
- Clear goal + context: "I want to pay with Alipay", "Dashboard takes 30 seconds to load"
- Step-by-step requests: "How do I reset my password?", "Steps to upgrade from Free to Starter"

**Diagnosis Rules:**
1. Ask at most **1-2 clarifying questions** in a single turn. Do NOT ask more than 2.
2. Questions should narrow the scope: topic area, error code, what the user was doing, what they expected vs what happened.
3. After the user replies, proceed to Step 1 (search) immediately — do NOT ask a second round of clarification.
4. If the user insists the problem is urgent (outage, data loss, security), skip diagnosis and escalate directly.

**Diagnosis Reply Template:**
```
I'd love to help! To find the right answer quickly, could you tell me:

1. [Specific question 1 — e.g., "What error message are you seeing?"]
2. [Specific question 2 — e.g., "Which part of CloudSync were you using when this happened?"]

This will help me narrow down the solution for you.
```

### Step 1: Analyze the Question

Identify the topic area (General / Billing / API / Troubleshooting) and extract the core keywords. If the question spans multiple topics, note all relevant areas.

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

### Multi-Turn Diagnosis (vague → clarify → search)

**User:** "Something's wrong with my data"
**Agent:** *Classify as VAGUE — no error code, no specifics.*
→ Respond: "I'd love to help! To find the right answer quickly, could you tell me: 1) What exactly looks wrong — is the data missing, incorrect, or not syncing? 2) Are you seeing any error codes? This will help me narrow down the solution."
→ Do NOT search yet.

**User:** "The sync is stuck and I see CS-ERR-5001"
**Agent:** *Now specific — has error code + symptom.*
→ Search: `mcp_rag_search_knowledge_base(query="data sync stuck CS-ERR-5001", top_k=5, alpha=0.5)` → troubleshooting.md, score 0.82 → Respond with solution.

---

**User:** "Help me with billing"
**Agent:** *Classify as VAGUE — ambiguous scope.*
→ Respond: "Sure! To point you in the right direction — are you looking to 1) upgrade your plan, 2) check an invoice, 3) update payment method, or 4) something else?"
→ Do NOT search yet.

**User:** "I want to switch from monthly to yearly"
**Agent:** *Now specific.*
→ Search: `mcp_rag_search_knowledge_base(query="switch from monthly to annual billing", top_k=5, alpha=0.3)` → billing.md, score 0.85 → Respond with steps.

---

### Direct Search (specific → search immediately)

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
