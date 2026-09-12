# Reliable job processing

A worker claims a job by acquiring a lease in a database transaction.
The lease has a unique token so an old worker cannot acknowledge a reclaimed job.

## Retry behavior

Temporary failures use exponential retry delays. After the maximum attempt count,
the queue stores the job in a dead-letter state for explicit inspection and replay.

## Delivery semantics

Lease fencing protects the queue state, but it cannot undo a side effect already
performed by an expired worker. An external consumer still needs idempotency.
