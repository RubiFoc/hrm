"""Automation rule evaluation and (future) execution package.

This package owns:
- trigger event contracts (schemas),
- rule persistence model (automation_rules),
- deterministic evaluation (`event -> planned actions`) without side effects.

`TASK-08-02` adds an executor for planned `notification.emit` actions. Retries and durable execution
logs are deferred to later slices.
"""
