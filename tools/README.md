# `tools/`

Capabilities exposed to agents, including delegation, repository, session, and
integration operations.

- Every tool needs an explicit permission boundary and predictable inputs/outputs.
- Provider credentials and personal data must be supplied at runtime.
- UI, terminal, MCP and remote-node implementations are adapters, not global authority.
