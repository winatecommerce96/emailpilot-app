"""
Policy enforcement for agents.

Provides budgets, guardrails, and safety checks for agent execution.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PolicyViolation:
    """Represents a policy violation."""
    type: str
    message: str
    severity: str  # "warning", "error", "critical"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentPolicy:
    """Policy configuration for agent execution."""
    
    # Tool call limits
    max_tool_calls: int = 15
    max_calls_per_tool: int = 5
    tool_call_timeout_seconds: int = 10
    
    # Time limits
    timeout_seconds: int = 60
    max_thinking_time_seconds: int = 30
    
    # PII and safety
    enable_pii_redaction: bool = True
    pii_patterns: List[str] = field(default_factory=lambda: [
        r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Names
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'\b[\w\.-]+@[\w\.-]+\.\w+\b',  # Email
        r'\b\d{10,}\b'  # Phone numbers
    ])
    
    # Denied operations
    denied_tools: Set[str] = field(default_factory=lambda: {
        "write_to_firestore",
        "delete_from_firestore",
        "send_email",
        "execute_code"
    })
    
    # Resource limits
    max_response_tokens: int = 2000
    max_memory_mb: int = 500
    
    # Retry configuration
    max_retries: int = 3
    retry_delay_seconds: int = 2
    
    # Allowed domains for HTTP tools
    allowed_domains: List[str] = field(default_factory=lambda: [
        "api.klaviyo.com",
        "localhost",
        "127.0.0.1",
        "jsonplaceholder.typicode.com"
    ])


class PolicyEnforcer:
    """Enforces policies during agent execution."""
    
    def __init__(self, policy: Optional[AgentPolicy] = None):
        """
        Initialize enforcer.
        
        Args:
            policy: Policy configuration
        """
        self.policy = policy or AgentPolicy()
        self.violations: List[PolicyViolation] = []
        self.tool_call_counts: Dict[str, int] = {}
        self.total_tool_calls = 0
        self.start_time = datetime.utcnow()
    
    def check_timeout(self) -> bool:
        """
        Check if execution has timed out.
        
        Returns:
            True if timeout exceeded
        """
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        
        if elapsed > self.policy.timeout_seconds:
            self.add_violation(
                PolicyViolation(
                    type="timeout",
                    message=f"Execution timeout exceeded: {elapsed}s > {self.policy.timeout_seconds}s",
                    severity="critical"
                )
            )
            return True
        
        return False
    
    def check_tool_call(self, tool_name: str) -> bool:
        """
        Check if tool call is allowed.
        
        Args:
            tool_name: Name of tool to call
        
        Returns:
            True if allowed, False otherwise
        """
        # Check if tool is denied
        if tool_name in self.policy.denied_tools:
            self.add_violation(
                PolicyViolation(
                    type="denied_tool",
                    message=f"Tool '{tool_name}' is denied by policy",
                    severity="error"
                )
            )
            return False
        
        # Check total tool calls
        if self.total_tool_calls >= self.policy.max_tool_calls:
            self.add_violation(
                PolicyViolation(
                    type="tool_budget_exceeded",
                    message=f"Total tool calls exceeded: {self.total_tool_calls} >= {self.policy.max_tool_calls}",
                    severity="error"
                )
            )
            return False
        
        # Check per-tool limits
        tool_count = self.tool_call_counts.get(tool_name, 0)
        if tool_count >= self.policy.max_calls_per_tool:
            self.add_violation(
                PolicyViolation(
                    type="tool_limit_exceeded",
                    message=f"Tool '{tool_name}' called {tool_count} times (limit: {self.policy.max_calls_per_tool})",
                    severity="warning"
                )
            )
            return False
        
        # Update counts
        self.total_tool_calls += 1
        self.tool_call_counts[tool_name] = tool_count + 1
        
        return True
    
    def check_url(self, url: str) -> bool:
        """
        Check if URL is allowed.
        
        Args:
            url: URL to check
        
        Returns:
            True if allowed
        """
        from urllib.parse import urlparse
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Check against allowed domains
            for allowed in self.policy.allowed_domains:
                if allowed in domain or domain in allowed:
                    return True
            
            self.add_violation(
                PolicyViolation(
                    type="denied_domain",
                    message=f"Domain '{domain}' not in allowed list",
                    severity="warning",
                    metadata={"url": url}
                )
            )
            return False
        
        except Exception as e:
            logger.error(f"URL parsing error: {e}")
            return False
    
    def redact_pii(self, text: str) -> str:
        """
        Redact PII from text.
        
        Args:
            text: Text to redact
        
        Returns:
            Redacted text
        """
        if not self.policy.enable_pii_redaction:
            return text
        
        redacted = text
        redaction_count = 0
        
        for pattern in self.policy.pii_patterns:
            try:
                matches = re.findall(pattern, redacted)
                if matches:
                    redaction_count += len(matches)
                    redacted = re.sub(pattern, "[REDACTED]", redacted)
            except re.error as e:
                logger.warning(f"Invalid PII pattern: {pattern}, error: {e}")
        
        if redaction_count > 0:
            self.add_violation(
                PolicyViolation(
                    type="pii_detected",
                    message=f"Redacted {redaction_count} potential PII instances",
                    severity="warning"
                )
            )
        
        return redacted
    
    def add_violation(self, violation: PolicyViolation) -> None:
        """Add a policy violation."""
        self.violations.append(violation)
        
        logger.warning(
            f"Policy violation [{violation.severity}]: "
            f"{violation.type} - {violation.message}"
        )
    
    def get_violations(
        self,
        severity: Optional[str] = None
    ) -> List[PolicyViolation]:
        """
        Get violations, optionally filtered by severity.
        
        Args:
            severity: Filter by severity level
        
        Returns:
            List of violations
        """
        if severity:
            return [v for v in self.violations if v.severity == severity]
        return self.violations
    
    def has_critical_violations(self) -> bool:
        """Check if there are any critical violations."""
        return any(v.severity == "critical" for v in self.violations)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get policy enforcement summary.
        
        Returns:
            Summary dictionary
        """
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "elapsed_seconds": elapsed,
            "tool_calls": self.total_tool_calls,
            "tool_call_breakdown": dict(self.tool_call_counts),
            "violations": len(self.violations),
            "violations_by_severity": {
                "critical": len(self.get_violations("critical")),
                "error": len(self.get_violations("error")),
                "warning": len(self.get_violations("warning"))
            },
            "limits": {
                "max_tool_calls": self.policy.max_tool_calls,
                "timeout_seconds": self.policy.timeout_seconds
            },
            "has_critical": self.has_critical_violations()
        }
    
    def reset(self) -> None:
        """Reset enforcer state."""
        self.violations = []
        self.tool_call_counts = {}
        self.total_tool_calls = 0
        self.start_time = datetime.utcnow()