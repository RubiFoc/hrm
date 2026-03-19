"""DAO exports for automation package."""

from hrm_backend.automation.dao.automation_rule_dao import AutomationRuleDAO
from hrm_backend.automation.dao.execution_log_dao import AutomationExecutionLogDAO
from hrm_backend.automation.dao.metric_event_dao import AutomationMetricEventDAO

__all__ = [
    "AutomationExecutionLogDAO",
    "AutomationMetricEventDAO",
    "AutomationRuleDAO",
]
