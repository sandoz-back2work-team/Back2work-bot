"""
Security Module - Spam and Phishing Detection
==============================================
Handles email security analysis including spam detection,
phishing scoring, and LLM-based risk assessment.
"""

import re
from typing import Dict, Any
from openai import OpenAI

from config import (
    TRUSTED_SENDER_DOMAINS,
    MODEL
)
from email_processing import sender_domain, safe_extract_json


# ============================================================================
# SPAM & PHISHING DETECTION
# ============================================================================

def phishing_score(subject: str, body: str, sender_addr: str) -> int:
    """
    Calculate phishing risk score based on suspicious patterns.
    
    Args:
        subject: Email subject line
        body: Email body content
        sender_addr: Sender email address
        
    Returns:
        Risk score from 0-20 (higher = more suspicious)
    """
    s = f"{subject} {body} {sender_addr}".lower()
    score = 0
    
    # Phishing keywords
    phishing_keywords = [
        "verify", "verification", "password", "contraseña", "reset", 
        "restablecer", "account locked", "suspended", "unusual activity", 
        "click here", "invoice", "factura", "payment", "wire transfer", 
        "gift card", "crypto", "confirm identity", "act now"
    ]
    if any(k in s for k in phishing_keywords): 
        score += 3
    
    # Spam keywords
    spam_keywords = [
        "unsubscribe", "you have won", "congratulations", 
        "buy now", "free money"
    ]
    if any(k in s for k in spam_keywords): 
        score += 2
    
    # Urgency indicators
    urgent = [
        "urgent", "urgente", "asap", "immediately", 
        "critical", "act now"
    ]
    urgent_count = sum(1 for u in urgent if u in s)
    if urgent_count >= 2: 
        score += 3
    elif urgent_count == 1: 
        score += 1
    
    # URL count (suspicious if many links)
    url_count = len(re.findall(r"\[URL\]", s))
    if url_count >= 5: 
        score += 4
    elif url_count >= 3: 
        score += 3
    
    # Long sender address (often spam)
    if "@" in sender_addr and len(sender_addr.split("@")[0]) > 20: 
        score += 1
    
    return min(score, 20)


def is_phishing(subject: str, body: str, sender_addr: str) -> bool:
    """
    Determine if email is likely phishing.
    
    Args:
        subject: Email subject
        body: Email body
        sender_addr: Sender address
        
    Returns:
        True if phishing detected
    """
    score = phishing_score(subject, body, sender_addr)
    dom = sender_domain(sender_addr)
    
    # High score = phishing
    if score >= 10: 
        return True
    
    # Medium score + untrusted domain = phishing
    if score >= 7 and dom and dom not in TRUSTED_SENDER_DOMAINS: 
        return True
    
    return False


def is_spam(subject: str, body: str, sender_addr: str) -> bool:
    """
    Determine if email is spam/marketing.
    
    Args:
        subject: Email subject
        body: Email body
        sender_addr: Sender address
        
    Returns:
        True if spam detected
    """
    dom = sender_domain(sender_addr)
    
    # Trust known domains
    if dom in TRUSTED_SENDER_DOMAINS: 
        return False
    
    s = f"{subject} {body}".lower()
    sender_lower = sender_addr.lower()
    
    # Common spam patterns
    spam_senders = [
        "regaloresponsable", "noreply", "no-reply", "newsletter"
    ]
    if any(d in sender_lower for d in spam_senders): 
        return True
    
    # Gift/marketing keywords
    gift_keywords = [
        "cesta navidad", "obsequio", "regalo", 
        "gift card", "lotes navidad"
    ]
    if any(kw in s for kw in gift_keywords): 
        return True

    # Allow work tools
    work_tools = [
        "quip", "jira", "confluence", "slack", "trello", 
        "teams", "planner", "sharepoint"
    ]
    if any(tool in sender_lower or tool in s for tool in work_tools): 
        return False
    
    # Allow travel confirmations
    travel_keywords = [
        "flight", "vuelo", "boarding", "embarque", "gate", 
        "puerta", "ticket", "billete", "renfe", "iberia"
    ]
    if any(kw in s for kw in travel_keywords): 
        return False
    
    # Allow internal newsletters from Sandoz
    if "sandoz" in sender_lower and ("digest" in s or "newsletter" in s): 
        return False
    
    # Detect marketing training offers
    is_marketing_training = (
        ("training" in s or "curso" in s) and 
        any(word in s for word in ["sin coste", "gratis", "free", "descuento", "oferta", "opcional"]) and 
        "csod.com" not in sender_lower
    )
    if is_marketing_training: 
        return True
    
    # Multiple spam markers
    spam_markers = [
        "unsubscribe", "newsletter", "promotional", "marketing", 
        "no-reply", "noreply", "you have won", "buy now"
    ]
    if s.count("unsubscribe") >= 2: 
        return True
    if sum(1 for m in spam_markers if m in s) >= 2: 
        return True
    
    return False


def llm_security_analysis(
    client: OpenAI, 
    subject: str, 
    sender: str, 
    body: str
) -> Dict[str, Any]:
    """
    Use LLM to analyze email security risk.
    
    Args:
        client: OpenAI client instance
        subject: Email subject
        sender: Sender name/address
        body: Email body (truncated)
        
    Returns:
        Dict with risk_level, is_phishing, is_spam, red_flags, explanation
    """
    prompt = f"""Analyze this email and return ONLY valid JSON:
{{ "risk_level": "medium", "is_phishing": false, "is_spam": false, "red_flags": [], "explanation": "" }}

SUBJECT: {subject}
SENDER: {sender}
BODY: {body[:2000]}"""
    
    try:
        resp = client.chat.completions.create(
            model=MODEL, 
            messages=[{"role": "user", "content": prompt}]
        )
        return safe_extract_json(resp.choices[0].message.content)
    except:
        return {}
