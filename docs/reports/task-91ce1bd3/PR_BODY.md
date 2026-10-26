SomPong can now use `org.email_ceo` with its existing Run Inbox token. The wrapper forces COO/session identity, refuses missing CXO_SESSION_ID, exposes no recipient, and leaves CEO-only delivery, caps, and deduplication to the hub.

`org.quota` reads the local snapshot without credentials, omits source paths, and flags data older than two hours. The snapshot writer sets 0644 before atomic replacement so SomPong can read it.

Validation: 25 focused MCP/email/snapshot tests pass. The requested five-file suite produced 126 passed, 10 failed, 1 xfailed; failures concern sandbox-denied Unix sockets, chown, and systemd access. Full details are in docs/reports/task-91ce1bd3/REPORT.md. No live email sent. Base is origin/main at 4b6af024; the flagged local-main commit is not in the branch ancestry.
