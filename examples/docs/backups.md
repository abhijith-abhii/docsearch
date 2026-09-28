# Backup policy

The backup retention period is 14 days. Each database backup is encrypted at rest. Backups run every day at 02:00 UTC. A backup failure pages the on-call engineer after two consecutive failed runs.

## Recovery

Before restoring a backup, stop all writers. Restore to a new database instance and verify row counts and the latest committed transaction. Switch traffic only after the verification checks pass. The illustrative recovery time objective is 30 minutes; this policy is not evidence that the objective has been achieved.
