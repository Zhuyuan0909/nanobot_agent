#!/usr/bin/env python3
"""Ticket management MCP Server — JSON-RPC 2.0 over stdio with SQLite storage.

Provides five tools: create_ticket, get_ticket, list_user_tickets, update_ticket, submit_feedback.

IMPORTANT: ALL debug/logging output MUST go to sys.stderr. Writing anything
other than JSON-RPC to stdout will break nanobot's MCP client connection.
"""

import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "tickets.db")


def log(msg: str) -> None:
    """Write debug/status messages to stderr to avoid stdio pollution."""
    print(f"[ticket_server] {msg}", file=sys.stderr, flush=True)


def init_database() -> None:
    """Create the tickets table and data directory if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id   TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            description TEXT NOT NULL,
            priority    TEXT DEFAULT 'medium',
            status      TEXT DEFAULT 'open',
            user_id     TEXT NOT NULL,
            user_name   TEXT DEFAULT '',
            platform    TEXT DEFAULT '',
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            comments    TEXT DEFAULT '[]',
            satisfaction_rating INTEGER DEFAULT NULL,
            feedback_text        TEXT DEFAULT NULL
        )
    """)
    # Add satisfaction columns to existing databases (safe to run on new ones too)
    for col, col_type in [("satisfaction_rating", "INTEGER"), ("feedback_text", "TEXT")]:
        try:
            conn.execute(f"ALTER TABLE tickets ADD COLUMN {col} {col_type} DEFAULT NULL")
        except sqlite3.OperationalError:
            pass  # Column already exists
    conn.commit()
    conn.close()
    log(f"Database ready: {DB_PATH}")


class TicketMCPServer:
    """Ticket management MCP Server — speaks JSON-RPC 2.0 over stdin/stdout."""

    def __init__(self) -> None:
        init_database()

    # -- request dispatch ---------------------------------------------------

    def handle_request(self, request: dict) -> dict:
        method = request.get("method", "")
        req_id = request.get("id")

        if method == "initialize":
            return {"jsonrpc": "2.0", "id": req_id, "result": self._initialize()}
        if method.startswith("notifications/"):
            return None  # JSON-RPC notifications receive no response
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": self._list_tools()}
        if method == "tools/call":
            return {"jsonrpc": "2.0", "id": req_id, "result": self._call_tool(request.get("params", {}))}

        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}

    # -- MCP lifecycle ------------------------------------------------------

    def _initialize(self) -> dict:
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "ticket-server", "version": "1.0.0"},
            "capabilities": {"tools": {}},
        }

    # -- tool definitions ---------------------------------------------------

    def _list_tools(self) -> dict:
        return {
            "tools": [
                {
                    "name": "create_ticket",
                    "description": "Create a new customer support ticket.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "title":       {"type": "string", "description": "Ticket title / summary"},
                            "description": {"type": "string", "description": "Detailed problem description"},
                            "priority":    {"type": "string", "enum": ["low", "medium", "high", "urgent"], "default": "medium"},
                            "user_id":     {"type": "string", "description": "User ID from the platform"},
                            "user_name":   {"type": "string", "description": "User display name"},
                            "platform":    {"type": "string", "description": "Source platform (feishu/dingtalk/telegram)"},
                        },
                        "required": ["title", "description", "user_id"],
                    },
                },
                {
                    "name": "get_ticket",
                    "description": "Retrieve a ticket by its ID.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "ticket_id": {"type": "string", "description": "The ticket ID"},
                        },
                        "required": ["ticket_id"],
                    },
                },
                {
                    "name": "list_user_tickets",
                    "description": "List all tickets belonging to a user, optionally filtered by status.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "User ID from the platform"},
                            "status":  {"type": "string", "enum": ["open", "in_progress", "resolved", "closed"], "description": "Optional status filter"},
                        },
                        "required": ["user_id"],
                    },
                },
                {
                    "name": "update_ticket",
                    "description": "Update ticket status or add a comment.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "ticket_id": {"type": "string", "description": "The ticket ID to update"},
                            "status":    {"type": "string", "enum": ["open", "in_progress", "resolved", "closed"], "description": "New ticket status"},
                            "comment":   {"type": "string", "description": "Optional comment to add"},
                        },
                        "required": ["ticket_id"],
                    },
                },
                {
                    "name": "submit_feedback",
                    "description": "Record a satisfaction rating and optional feedback for a resolved ticket.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "ticket_id": {"type": "string", "description": "The ticket ID to rate"},
                            "rating":    {"type": "integer", "minimum": 1, "maximum": 5, "description": "Satisfaction score: 1 (very dissatisfied) to 5 (very satisfied)"},
                            "feedback":  {"type": "string", "description": "Optional free-text feedback"},
                        },
                        "required": ["ticket_id", "rating"],
                    },
                },
            ]
        }

    # -- tool dispatch ------------------------------------------------------

    def _call_tool(self, params: dict) -> dict:
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        handlers = {
            "create_ticket":     self._create_ticket,
            "get_ticket":        self._get_ticket,
            "list_user_tickets": self._list_user_tickets,
            "update_ticket":     self._update_ticket,
            "submit_feedback":   self._submit_feedback,
        }

        handler = handlers.get(tool_name)
        if not handler:
            return {"content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}], "isError": True}

        try:
            result = handler(arguments)
            return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
        except Exception as exc:
            log(f"Tool error: {tool_name} -> {exc}")
            return {"content": [{"type": "text", "text": f"Error: {exc}"}], "isError": True}

    # -- tool implementations -----------------------------------------------

    def _create_ticket(self, args: dict) -> dict:
        ticket_id = f"TK-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now().isoformat()

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """INSERT INTO tickets (ticket_id, title, description, priority, status,
                   user_id, user_name, platform, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'open', ?, ?, ?, ?, ?)""",
                (
                    ticket_id,
                    args["title"],
                    args["description"],
                    args.get("priority", "medium"),
                    args["user_id"],
                    args.get("user_name", ""),
                    args.get("platform", ""),
                    now,
                    now,
                ),
            )
            conn.commit()

        log(f"Created ticket {ticket_id}")
        return {"success": True, "ticket_id": ticket_id, "message": f"Ticket {ticket_id} created successfully."}

    def _get_ticket(self, args: dict) -> dict:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM tickets WHERE ticket_id = ?", (args["ticket_id"],)).fetchone()

        if not row:
            return {"success": False, "message": "Ticket not found."}

        ticket = dict(row)
        ticket["comments"] = json.loads(ticket.get("comments", "[]"))
        return {"success": True, "ticket": ticket}

    def _list_user_tickets(self, args: dict) -> dict:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            if "status" in args:
                rows = conn.execute(
                    "SELECT * FROM tickets WHERE user_id = ? AND status = ? ORDER BY created_at DESC",
                    (args["user_id"], args["status"]),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM tickets WHERE user_id = ? ORDER BY created_at DESC",
                    (args["user_id"],),
                ).fetchall()

        tickets = []
        for row in rows:
            t = dict(row)
            t["comments"] = json.loads(t.get("comments", "[]"))
            tickets.append(t)

        return {"success": True, "count": len(tickets), "tickets": tickets}

    def _update_ticket(self, args: dict) -> dict:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM tickets WHERE ticket_id = ?", (args["ticket_id"],)).fetchone()
            if not row:
                return {"success": False, "message": "Ticket not found."}

            now = datetime.now().isoformat()
            ticket = dict(row)

            if "status" in args:
                conn.execute(
                    "UPDATE tickets SET status = ?, updated_at = ? WHERE ticket_id = ?",
                    (args["status"], now, args["ticket_id"]),
                )
                ticket["status"] = args["status"]

            if "comment" in args and args["comment"]:
                comments = json.loads(ticket.get("comments", "[]"))
                comments.append({"text": args["comment"], "timestamp": now})
                conn.execute(
                    "UPDATE tickets SET comments = ?, updated_at = ? WHERE ticket_id = ?",
                    (json.dumps(comments, ensure_ascii=False), now, args["ticket_id"]),
                )
                ticket["comments"] = comments

            conn.commit()

        log(f"Updated ticket {args['ticket_id']}")
        return {"success": True, "message": f"Ticket {args['ticket_id']} updated.", "ticket_id": args["ticket_id"]}

    def _submit_feedback(self, args: dict) -> dict:
        now = datetime.now().isoformat()

        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM tickets WHERE ticket_id = ?", (args["ticket_id"],)).fetchone()
            if not row:
                return {"success": False, "message": "Ticket not found."}

            conn.execute(
                "UPDATE tickets SET satisfaction_rating = ?, feedback_text = ?, updated_at = ? WHERE ticket_id = ?",
                (args["rating"], args.get("feedback", ""), now, args["ticket_id"]),
            )
            conn.commit()

        log(f"Recorded feedback for {args['ticket_id']}: rating={args['rating']}")
        return {"success": True, "message": f"Feedback recorded for ticket {args['ticket_id']}.", "ticket_id": args["ticket_id"]}

    # -- main loop -----------------------------------------------------------

    def run(self) -> None:
        log("Starting ticket MCP server...")
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = self.handle_request(request)
                if response is not None:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
            except json.JSONDecodeError:
                log(f"Invalid JSON received: {line[:100]}...")
            except KeyboardInterrupt:
                break
        log("Server stopped.")


if __name__ == "__main__":
    TicketMCPServer().run()
