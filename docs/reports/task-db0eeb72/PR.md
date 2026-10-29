Add one-shot DiskSteward M4 report to CTO Main

Contabo ticks now attempt a fixed-window M4 report from 2 November 2026 at 23:00 Thai time. The zero-model letter includes each host's seven-day minimum, Thai timestamps, sample count, latest sample, steward ledger count, and Contabo's longest qualifying run. Below-15 GB minima identify P5 as CTO Main's next step.

The report uses lib.mailbox.send, a process lock, and an atomic success stamp. Failures retry; subsequent successful runs skip. The standalone `m4-report --now ISO --dry-run` command previews the letter without sending or writing state.

Validation: the new M4 tests and existing steward/host tests passed (92 passed, 1 native-Windows test skipped); git diff --check passed. All new send paths were mocked. See REPORT.md for sampling and send/stamp crash limitations.
