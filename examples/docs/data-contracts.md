# Data contracts

A data contract defines required columns, types, allowed values, and record keys.
Validation runs before the warehouse transaction to catch malformed files.

## Import recovery

The batch journal and accepted records commit in one database transaction.
An import failure rolls back the batch so a retry can begin from a known state.

## Rejected rows

Invalid rows remain in local quarantine with specific validation errors.
Synthetic fixtures let recruiters run a demonstration without personal data.
