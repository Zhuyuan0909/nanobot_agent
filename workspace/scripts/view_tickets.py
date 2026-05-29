#!/usr/bin/env python3
"""View all tickets in the SQLite database."""
import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "tickets.db")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT * FROM tickets ORDER BY created_at DESC").fetchall()

if not rows:
    print("(empty, no tickets yet)")
else:
    for r in rows:
        t = dict(r)
        print(f"Ticket: {t['ticket_id']}")
        print(f"  Title:       {t['title']}")
        print(f"  Priority:    {t['priority']} | Status: {t['status']}")
        print(f"  User:        {t['user_name']} | Platform: {t['platform']}")
        print(f"  Created:     {t['created_at']}")
        comments = json.loads(t.get("comments", "[]"))
        if comments:
            for c in comments:
                print(f"  Comment:     {c['text']} ({c['timestamp']})")
        if t.get("satisfaction_rating"):
            print(f"  Rating:      {t['satisfaction_rating']}/5 — {t.get('feedback_text', '')}")
        print()

conn.close()
