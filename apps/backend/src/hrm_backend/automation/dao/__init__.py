"""DAO exports for automation package."""

from hrm_backend.automation.dao.automation_rule_dao import AutomationRuleDAO
from hrm_backend.automation.dao.execution_log_dao import AutomationExecutionLogDAO

__all__ = ["AutomationExecutionLogDAO", "AutomationRuleDAO"]
