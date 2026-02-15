"""
Módulo de Seguridad - Detección de Spam y Phishing
===================================================
Gestiona el análisis de seguridad de correos electrónicos incluyendo
detección de spam, puntuación de phishing y evaluación de riesgo basada en LLM.
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
# DETECCIÓN DE SPAM Y PHISHING
# ============================================================================

def phishing_score(subject: str, body: str, sender_addr: str) -> int:
    """
    Calcular puntuación de riesgo de phishing basada en patrones sospechosos.
    
    Args:
        subject: Asunto del correo electrónico
        body: Contenido del cuerpo del correo
        sender_addr: Dirección de correo del remitente
        
    Returns:
        Puntuación de riesgo de 0-20 (mayor valor = más sospechoso)
    """
    s = f"{subject} {body} {sender_addr}".lower()
    score = 0
    
    # Palabras clave típicas de phishing
    phishing_keywords = [
        "verify", "verification", "password", "contraseña", "reset", 
        "restablecer", "account locked", "suspended", "unusual activity", 
        "click here", "invoice", "factura", "payment", "wire transfer", 
        "gift card", "crypto", "confirm identity", "act now"
    ]
    if any(k in s for k in phishing_keywords): 
        score += 3
    
    # Palabras clave típicas de spam
    spam_keywords = [
        "unsubscribe", "you have won", "congratulations", 
        "buy now", "free money"
    ]
    if any(k in s for k in spam_keywords): 
        score += 2
    
    # Indicadores de urgencia
    urgent = [
        "urgent", "urgente", "asap", "immediately", 
        "critical", "act now"
    ]
    urgent_count = sum(1 for u in urgent if u in s)
    if urgent_count >= 2: 
        score += 3
    elif urgent_count == 1: 
        score += 1
    
    # Número de URLs (sospechoso si hay muchos enlaces)
    url_count = len(re.findall(r"\[URL\]", s))
    if url_count >= 5: 
        score += 4
    elif url_count >= 3: 
        score += 3
    
    # Dirección de remitente larga (frecuente en spam)
    if "@" in sender_addr and len(sender_addr.split("@")[0]) > 20: 
        score += 1
    
    return min(score, 20)


def is_phishing(subject: str, body: str, sender_addr: str) -> bool:
    """
    Determinar si el correo probablemente es phishing.
    
    Args:
        subject: Asunto del correo
        body: Cuerpo del correo
        sender_addr: Dirección del remitente
        
    Returns:
        True si se detecta phishing
    """
    score = phishing_score(subject, body, sender_addr)
    dom = sender_domain(sender_addr)
    
    # Puntuación alta = phishing
    if score >= 10: 
        return True
    
    # Puntuación media + dominio no confiable = phishing
    if score >= 7 and dom and dom not in TRUSTED_SENDER_DOMAINS: 
        return True
    
    return False


def is_spam(subject: str, body: str, sender_addr: str) -> bool:
    """
    Determinar si el correo es spam o marketing.
    
    Args:
        subject: Asunto del correo
        body: Cuerpo del correo
        sender_addr: Dirección del remitente
        
    Returns:
        True si se detecta spam
    """
    dom = sender_domain(sender_addr)
    
    # Confiar en dominios conocidos
    if dom in TRUSTED_SENDER_DOMAINS: 
        return False
    
    s = f"{subject} {body}".lower()
    sender_lower = sender_addr.lower()
    
    # Patrones comunes de remitentes de spam
    spam_senders = [
        "regaloresponsable", "noreply", "no-reply", "newsletter"
    ]
    if any(d in sender_lower for d in spam_senders): 
        return True
    
    # Palabras clave relacionadas con regalos / marketing
    gift_keywords = [
        "cesta navidad", "obsequio", "regalo", 
        "gift card", "lotes navidad"
    ]
    if any(kw in s for kw in gift_keywords): 
        return True

    # Permitir herramientas de trabajo
    work_tools = [
        "quip", "jira", "confluence", "slack", "trello", 
        "teams", "planner", "sharepoint"
    ]
    if any(tool in sender_lower or tool in s for tool in work_tools): 
        return False
    
    # Permitir confirmaciones de viaje
    travel_keywords = [
        "flight", "vuelo", "boarding", "embarque", "gate", 
        "puerta", "ticket", "billete", "renfe", "iberia"
    ]
    if any(kw in s for kw in travel_keywords): 
        return False
    
    # Permitir newsletters internas
    if "sandoz" in sender_lower and ("digest" in s or "newsletter" in s): 
        return False
    
    # Detectar ofertas formativas de marketing
    is_marketing_training = (
        ("training" in s or "curso" in s) and 
        any(word in s for word in ["sin coste", "gratis", "free", "descuento", "oferta", "opcional"]) and 
        "csod.com" not in sender_lower
    )
    if is_marketing_training: 
        return True
    
    # Múltiples marcadores de spam
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
    Usar un LLM para analizar el riesgo de seguridad del correo.
    
    Args:
        client: Instancia del cliente OpenAI
        subject: Asunto del correo
        sender: Nombre/dirección del remitente
        body: Cuerpo del correo (truncado)
        
    Returns:
        Diccionario con: risk_level, is_phishing, is_spam, red_flags, explanation
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
