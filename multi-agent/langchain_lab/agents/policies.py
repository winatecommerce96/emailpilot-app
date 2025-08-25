"""
Policy enforcement for agents.

Provides guardrails including tool call budgets, time limits,
PII redaction, and write prevention.
"""

import re
import time
import logging
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class AgentPolicy:
    """Policy configuration for agent execution."""
    
    # Resource limits
    max_tool_calls: int = 15
    max_iterations: int = 10
    timeout_seconds: int = 30
    
    # Safety policies
    allow_writes: bool = False
    redact_pii: bool = True
    
    # Allowed tools (None = all allowed)
    allowed_tools: Optional[Set[str]] = None
    blocked_tools: Optional[Set[str]] = None
    
    # Rate limiting
    tool_call_delay_ms: int = 100  # Minimum delay between tool calls
    
    def __post_init__(self):
        """Initialize blocked tools if not provided."""
        if self.blocked_tools is None and not self.allow_writes:
            # Block any tools that might write data
            self.blocked_tools = {
                "firestore_write", "klaviyo_write", "file_write",
                "database_update", "api_post", "api_put", "api_delete"
            }


@dataclass
class PolicyViolation:
    """Record of a policy violation."""
    timestamp: datetime
    policy_type: str
    details: str
    severity: str  # "warning", "error", "critical"


class PolicyEnforcer:
    """Enforces policies during agent execution."""
    
    PII_PATTERNS = [
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'EMAIL'),
        (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', 'PHONE'),
        (r'\b\d{3}-\d{2}-\d{4}\b', 'SSN'),
        (r'\b(?:\d{4}[-\s]?){3}\d{4}\b', 'CREDIT_CARD'),
        (r'\b\d{5}(?:-\d{4})?\b', 'ZIPCODE'),
    ]
    
    def __init__(self, policy: Optional[AgentPolicy] = None):
        """
        Initialize policy enforcer.
        
        Args:
            policy: AgentPolicy instance (creates default if not provided)
        """
        self.policy = policy or AgentPolicy()
        self.violations: List[PolicyViolation] = []
        self.tool_call_count = 0
        self.iteration_count = 0
        self.start_time = None
        self.last_tool_call_time = None
    
    def start_execution(self) -> None:
        """Mark the start of agent execution."""
        self.start_time = time.time()
        self.tool_call_count = 0
        self.iteration_count = 0
        self.violations = []
        logger.info(f"Policy enforcement started with limits: {self.policy}")
    
    def check_timeout(self) -> bool:
        """
        Check if execution has timed out.
        
        Returns:
            True if within time limit, False if timed out
        """
        if self.start_time is None:
            return True
        
        elapsed = time.time() - self.start_time
        if elapsed > self.policy.timeout_seconds:
            self.add_violation(
                "timeout",
                f"Execution timed out after {elapsed:.1f} seconds",
                "critical"
            )
            return False
        return True
    
    def check_tool_call(self, tool_name: str) -> bool:
        """
        Check if a tool call is allowed.
        
        Args:
            tool_name: Name of the tool being called
        
        Returns:
            True if allowed, False if blocked
        """
        # Check tool call budget
        if self.tool_call_count >= self.policy.max_tool_calls:
            self.add_violation(
                "tool_budget",
                f"Tool call budget exceeded ({self.tool_call_count}/{self.policy.max_tool_calls})",
                "error"
            )
            return False
        
        # Check allowed/blocked tools
        if self.policy.allowed_tools and tool_name not in self.policy.allowed_tools:
            self.add_violation(
                "tool_blocked",
                f"Tool '{tool_name}' not in allowed list",
                "error"
            )
            return False
        
        if self.policy.blocked_tools and tool_name in self.policy.blocked_tools:
            self.add_violation(
                "tool_blocked",
                f"Tool '{tool_name}' is blocked by policy",
                "error"
            )
            return False
        
        # Check rate limiting
        if self.last_tool_call_time:
            elapsed_ms = (time.time() - self.last_tool_call_time) * 1000
            if elapsed_ms < self.policy.tool_call_delay_ms:
                time.sleep((self.policy.tool_call_delay_ms - elapsed_ms) / 1000)
        
        # Update counters
        self.tool_call_count += 1
        self.last_tool_call_time = time.time()
        
        return True
    
    def check_iteration(self) -> bool:
        """
        Check if another iteration is allowed.
        
        Returns:
            True if allowed, False if limit reached
        """
        if self.iteration_count >= self.policy.max_iterations:
            self.add_violation(
                "iteration_limit",
                f"Max iterations reached ({self.policy.max_iterations})",
                "error"
            )
            return False
        
        self.iteration_count += 1
        return True
    
    def redact_pii(self, text: str) -> str:
        """
        Redact PII from text.
        
        Args:
            text: Text to redact
        
        Returns:
            Text with PII redacted
        """
        if not self.policy.redact_pii:
            return text
        
        redacted = text
        for pattern, pii_type in self.PII_PATTERNS:
            matches = re.findall(pattern, redacted)
            if matches:
                logger.debug(f"Redacting {len(matches)} {pii_type} instances")
                redacted = re.sub(pattern, f"[REDACTED_{pii_type}]", redacted)
        
        return redacted
    
    def check_output(self, output: Any) -> Any:
        """
        Check and sanitize agent output.
        
        Args:
            output: Agent output to check
        
        Returns:
            Sanitized output
        """
        if isinstance(output, str):
            return self.redact_pii(output)
        elif isinstance(output, dict):
            return {k: self.check_output(v) for k, v in output.items()}
        elif isinstance(output, list):
            return [self.check_output(item) for item in output]
        else:
            return output
    
    def add_violation(
        self,
        policy_type: str,
        details: str,
        severity: str = "warning"
    ) -> None:
        """
        Record a policy violation.
        
        Args:
            policy_type: Type of policy violated
            details: Details about the violation
            severity: Severity level
        """
        violation = PolicyViolation(
            timestamp=datetime.now(),
            policy_type=policy_type,
            details=details,
            severity=severity
        )
        self.violations.append(violation)
        
        if severity == "critical":
            logger.error(f"CRITICAL POLICY VIOLATION: {details}")
        elif severity == "error":
            logger.warning(f"Policy violation: {details}")
        else:
            logger.debug(f"Policy warning: {details}")
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of policy enforcement.
        
        Returns:
            Dictionary with enforcement statistics
        """
        elapsed = time.time() - self.start_time if self.start_time else 0
        
        return {
            "tool_calls": self.tool_call_count,
            "iterations": self.iteration_count,
            "elapsed_seconds": round(elapsed, 2),
            "violations": [
                {
                    "timestamp": v.timestamp.isoformat(),
                    "type": v.policy_type,
                    "details": v.details,
                    "severity": v.severity
                }
                for v in self.violations
            ],
            "limits": {
                "max_tool_calls": self.policy.max_tool_calls,
                "max_iterations": self.policy.max_iterations,
                "timeout_seconds": self.policy.timeout_seconds
            }
        }
    
    def is_compliant(self) -> bool:
        """
        Check if execution has been compliant with all policies.
        
        Returns:
            True if no critical/error violations, False otherwise
        """
        return not any(
            v.severity in ["critical", "error"]
            for v in self.violations
        )