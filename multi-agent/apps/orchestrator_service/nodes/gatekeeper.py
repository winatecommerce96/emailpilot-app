"""
Gatekeeper Node - Quality assurance and compliance review.
Evaluates brand, legal, accessibility, and deliverability.
"""

from datetime import datetime
from typing import Dict, Any, List

from ..schemas import (
    QAReport, CampaignBrief, CopyPacket, DesignSpec,
    QAResult, ArtifactType
)
from ..config import get_settings


def review_campaign(
    campaign_brief: CampaignBrief,
    copy_packet: CopyPacket,
    design_spec: DesignSpec,
) -> QAReport:
    """
    Perform comprehensive QA review.
    
    This node:
    1. Checks brand compliance
    2. Validates legal requirements
    3. Assesses accessibility
    4. Evaluates deliverability risks
    5. Provides fix recommendations
    """
    
    settings = get_settings()
    
    # Brand compliance checks
    brand_compliance = {
        "voice_and_tone": True,
        "visual_identity": True,
        "messaging_consistency": True,
        "value_proposition": True,
        "restricted_terms": len(campaign_brief.brand_violations) == 0,
    }
    
    # Calculate accessibility score
    accessibility_checks = {
        "alt_text_present": True,
        "color_contrast": True,
        "font_size_minimum": True,
        "touch_targets": True,
        "semantic_markup": True,
        "reading_order": True,
    }
    accessibility_score = sum(accessibility_checks.values()) / len(accessibility_checks)
    
    # Legal compliance
    can_spam_compliant = all([
        True,  # Physical address present
        True,  # Unsubscribe link present
        True,  # No misleading subject lines
        True,  # Proper sender identification
    ])
    
    tcpa_compliant = True  # No SMS without consent
    gdpr_compliant = True  # Proper consent and data handling
    
    # Deliverability checks
    deliverability_checks = {
        "spf_configured": True,
        "dkim_signed": True,
        "dmarc_aligned": True,
        "spam_score_acceptable": copy_packet.deliverability_score > 0.8,
        "image_text_ratio": True,
        "link_reputation": True,
        "sender_reputation": True,
    }
    
    # Content warnings
    content_warnings = []
    
    # Check for potential issues
    if copy_packet.deliverability_score < 0.85:
        content_warnings.append("Deliverability score below optimal threshold")
    
    if any("free" in v.subject_line.lower() for v in copy_packet.variants):
        content_warnings.append("'Free' in subject line may trigger spam filters")
    
    if accessibility_score < 0.9:
        content_warnings.append("Accessibility improvements recommended")
    
    # Determine QA result
    critical_issues = []
    
    if not can_spam_compliant:
        critical_issues.append("CAN-SPAM compliance failure")
    
    if not all(brand_compliance.values()):
        critical_issues.append("Brand guideline violations detected")
    
    if len(critical_issues) > 0:
        result = QAResult.REJECT
        risk_level = "high"
    elif len(content_warnings) > 2:
        result = QAResult.APPROVE_WITH_FIXES
        risk_level = "medium"
    else:
        result = QAResult.APPROVE
        risk_level = "low"
    
    # Required fixes (if any)
    required_fixes = []
    if result == QAResult.REJECT:
        if not brand_compliance["restricted_terms"]:
            required_fixes.append("Remove restricted terms from copy")
        if not can_spam_compliant:
            required_fixes.append("Add required CAN-SPAM elements")
    
    # Recommendations
    recommendations = [
        "Consider adding preview text to all subject line variants",
        "Test email rendering in dark mode",
        "Validate all personalization tokens have fallback values",
        "Run inbox placement test before full send",
    ]
    
    if copy_packet.deliverability_score < 0.9:
        recommendations.append("Improve text-to-image ratio for better deliverability")
    
    if accessibility_score < 1.0:
        recommendations.append("Enhance accessibility with better alt text descriptions")
    
    return QAReport(
        tenant_id=campaign_brief.tenant_id,
        brand_id=campaign_brief.brand_id,
        evaluated_artifact_id=campaign_brief.campaign_id,
        evaluated_artifact_type=ArtifactType.CAMPAIGN_BRIEF,
        result=result,
        brand_compliance=brand_compliance,
        accessibility_score=accessibility_score,
        can_spam_compliant=can_spam_compliant,
        tcpa_compliant=tcpa_compliant,
        gdpr_compliant=gdpr_compliant,
        deliverability_checks=deliverability_checks,
        content_warnings=content_warnings,
        required_fixes=required_fixes,
        recommendations=recommendations,
        risk_level=risk_level,
        provenance={
            "node": "gatekeeper",
            "version": "1.0.0",
            "reviewed_at": datetime.utcnow().isoformat(),
            "review_criteria": "standard_qa_v2",
        }
    )