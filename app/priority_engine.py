"""
Motor de Prioridad - Puntuación y Priorización de Correos
==========================================================
Calcula puntuaciones de prioridad y clasifica los correos en niveles
Alta/Media/Baja según reglas de negocio, urgencia y preferencias del usuario.
"""

import re
import math
import unicodedata
import difflib
from typing import Dict, Any, List
import pandas as pd

from config import TRUSTED_SENDER_DOMAINS


# ============================================================================
# UNIFICACIÓN DE NOMBRES DE PROYECTO (Eliminación de duplicados)
# ============================================================================

_PROJECT_PREFIX_RE = re.compile(r"^(proyecto|project|proj\.?|proy\.?)\s+", re.I)

_GENERIC_TAIL_TOKENS = {
    "implementation", "implementacion", "impl"
}

_GENERIC_HEAD_TOKENS = {
    "implementation", "implementacion", "impl"
}

_PROJECT_STOPWORDS = {
    "de", "del", "la", "el", "los", "las", "of", "the", "and", "y"
}


def _strip_generic_head_tokens(norm_key: str) -> str:
    """Eliminar tokens genéricos iniciales del nombre del proyecto."""
    if not norm_key:
        return ""
    toks = norm_key.split()
    while toks and toks[0] in _GENERIC_HEAD_TOKENS:
        toks = toks[1:]
        while toks and toks[0] in _PROJECT_STOPWORDS:
            toks = toks[1:]
    return " ".join(toks).strip()


def _strip_generic_tail_tokens(norm_key: str) -> str:
    """Eliminar tokens genéricos finales del nombre del proyecto."""
    if not norm_key:
        return ""
    toks = norm_key.split()
    while toks and toks[-1] in _GENERIC_TAIL_TOKENS:
        toks = toks[:-1]
    return " ".join(toks).strip()


def _proj_norm_key_raw(s: str) -> str:
    """Normalizar el nombre del proyecto para su comparación."""
    if not isinstance(s, str):
        s = "" if s is None else str(s)
    s = s.strip()
    if not s:
        return ""
    s = _PROJECT_PREFIX_RE.sub("", s).strip()
    s = "".join(
        ch for ch in unicodedata.normalize("NFKD", s.lower()) 
        if not unicodedata.combining(ch)
    )
    s = re.sub(r"[^a-z0-9\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _proj_norm_key(s: str) -> str:
    """Normalización completa con eliminación de tokens iniciales y finales."""
    raw = _proj_norm_key_raw(s)
    raw = _strip_generic_head_tokens(raw)
    return _strip_generic_tail_tokens(raw)


def _proj_display_name(s: str) -> str:
    """Obtener el nombre para mostrar del proyecto."""
    if not isinstance(s, str):
        s = "" if s is None else str(s)
    s = s.strip()
    if not s:
        return ""
    s = _PROJECT_PREFIX_RE.sub("", s).strip()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _is_abbrev_orig(orig: str) -> bool:
    """Verificar si el nombre del proyecto es una abreviatura."""
    disp = _proj_display_name(orig or "")
    return bool(disp) and disp.isalpha() and disp.isupper() and 1 <= len(disp) <= 3


def _projects_similar(a_key: str, b_key: str, a_orig: str = "", b_orig: str = "") -> bool:
    """Determinar si dos nombres de proyecto son lo suficientemente similares como para fusionarlos."""
    if not a_key or not b_key:
        return False
    if a_key == b_key:
        return True

    # Alta similitud entre cadenas
    r = difflib.SequenceMatcher(None, a_key, b_key).ratio()
    if r >= 0.88:
        return True

    # Contención en nombres largos
    if (a_key in b_key or b_key in a_key) and min(len(a_key), len(b_key)) >= 4:
        return True

    # Nombres de proyecto cortos
    if max(len(a_key), len(b_key)) <= 12:
        if a_key[:3] == b_key[:3] and r >= 0.80:
            return True

    # Abreviatura frente a nombre completo
    if _is_abbrev_orig(a_orig) and len(a_key) <= 3:
        if (b_key.startswith(a_key + " ") or 
            (b_key.startswith(a_key) and b_key.isalpha() and len(b_key) >= 4)):
            return True
        if b_key.split() and b_key.split()[0] == a_key and len(a_key) <= 4:
            return True

    if _is_abbrev_orig(b_orig) and len(b_key) <= 3:
        if (a_key.startswith(b_key + " ") or 
            (a_key.startswith(b_key) and a_key.isalpha() and len(a_key) >= 4)):
            return True
        if a_key.split() and a_key.split()[0] == b_key and len(b_key) <= 4:
            return True

    return False


def build_project_canonical_map(project_values: List[Any]) -> Dict[str, str]:
    """
    Construir un mapeo desde variaciones de nombres de proyecto hacia un nombre canónico.
    
    Args:
        project_values: Lista de todos los nombres de proyecto detectados en los correos
    
    Returns:
        Diccionario que mapea cada variación a su nombre canónico
    """
    counts: Dict[str, int] = {}
    for v in project_values or []:
        if v is None:
            continue
        s = str(v).strip()
        if not s or s.lower() in ("none", "nan", "null"):
            continue
        counts[s] = counts.get(s, 0) + 1

    if not counts:
        return {}

    # Ordenar por frecuencia (los más comunes primero)
    uniques = sorted(counts.keys(), key=lambda x: (-counts[x], len(x)))

    # Agrupar nombres similares en clusters
    clusters: List[Dict[str, Any]] = []
    for orig in uniques:
        key = _proj_norm_key(orig)
        if not key:
            continue
        placed = False
        for cl in clusters:
            if _projects_similar(key, cl["key"], orig, cl.get("repr", "")):
                cl["members"].append(orig)
                placed = True
                break
        if not placed:
            clusters.append({"key": key, "members": [orig], "repr": orig})

    # Elegir el nombre canónico para cada cluster
    mapping: Dict[str, str] = {}
    for cl in clusters:
        members = cl["members"]

        def _cand_score(cand: str) -> int:
            freq = counts.get(cand, 1)
            disp = _proj_display_name(cand)
            prefix_pen = 1 if _PROJECT_PREFIX_RE.match(cand.strip() or "") else 0
            length_pen = len(disp) if disp else len(cand)

            raw_key = _proj_norm_key_raw(cand)
            stripped_key = _strip_generic_tail_tokens(raw_key)
            tail_pen = 1 if raw_key and stripped_key and raw_key != stripped_key else 0

            return freq * 100 - prefix_pen * 20 - tail_pen * 25 - length_pen

        best = max(members, key=_cand_score)
        canon = _proj_display_name(best) or best.strip()
        if canon.islower():
            canon = canon.capitalize()

        for m in members:
            mapping[m] = canon

    return mapping


def unify_projects_in_df(df: pd.DataFrame, project_col: str = "project") -> pd.DataFrame:
    """
    Unificar variaciones de nombres de proyecto en un DataFrame.
    
    Args:
        df: DataFrame que contiene la columna de proyectos
        project_col: Nombre de la columna que contiene el proyecto
    
    Returns:
        DataFrame con nombres de proyecto unificados
    """
    if df is None or df.empty or project_col not in df.columns:
        return df
    
    proj_map = build_project_canonical_map(df[project_col].tolist())
    if not proj_map:
        return df

    def _apply(v: Any) -> str:
        if v is None:
            return "None"
        s = str(v).strip()
        if not s or s.lower() in ("none", "nan", "null"):
            return "None"
        return proj_map.get(s, s)

    df[project_col] = df[project_col].apply(_apply)
    return df


# ============================================================================
# LÓGICA DE PRIORIDAD FORZADA POR EL USUARIO
# ============================================================================

def check_user_overrides(text_content: str, sender: str, vip_senders: List[str]) -> bool:
    """
    Comprobar si el correo coincide con las reglas de remitentes VIP definidas por el usuario.
    
    Args:
        text_content: Texto combinado de asunto + cuerpo
        sender: Dirección del remitente
        vip_senders: Lista de patrones de remitentes VIP
    
    Returns:
        True si el remitente coincide con la lista VIP
    """
    sender_clean = sender.lower().strip()
    for vip_entry in vip_senders:
        if vip_entry and vip_entry.lower() in sender_clean:
            return True
    return False


# ============================================================================
# MOTOR DE CÁLCULO DE PRIORIDAD
# ============================================================================

def calculate_priority_score(
    data: Dict[str, Any], 
    importance: str = "", 
    subject: str = ""
) -> int:
    """
    Calcular puntuación numérica de prioridad (0-100).
    
    Args:
        data: Resultados del análisis LLM
        importance: Indicador de importancia del correo
        subject: Línea de asunto
    
    Returns:
        Puntuación entre 0-100 (mayor valor = más urgente)
    """
    score = 50
    subject_lower = subject.lower()
    
    # 1. Indicadores en el asunto
    if "[high priority]" in subject_lower or "[urgent]" in subject_lower: 
        score += 20
    if importance and str(importance).strip().lower() == 'high': 
        score += 20
    
    # 2. Pesos según tipo de correo
    type_weights = {
        "Approval_Request": 25, 
        "Decision_Required": 25, 
        "External_Request": 20,
        "Action_Request": 15, 
        "Meeting": 10, 
        "Report_Update": 5,
        "FYI_Informational": 0, 
        "Notification_System": -15
    }
    email_type = data.get("email_type", "")
    action_level = data.get("action_level", "None")

    if email_type == "Notification_System" and action_level == "Mandatory":
        score += 15
    else:
        score += type_weights.get(email_type, 0)
    
    # 3. Contexto y penalizaciones
    summary = str(data.get("summary", "")).lower()
    full_context_check = (
        subject_lower + " " + summary + " " + 
        str(data.get("project", "")).lower()
    )

    # Penalización por spam/marketing
    spam_keywords = [
        "newsletter", "promotional", "black friday", 
        "sale", "unsubscribe", "club novartis"
    ]
    if any(kw in full_context_check for kw in spam_keywords): 
        score -= 30
    
    marketing_triggers = [
        "trial", "free access", "survey", "encuesta", 
        "webinar", "demo", "easyvideo", "trail"
    ]
    is_marketing_context = any(kw in full_context_check for kw in marketing_triggers)
    if is_marketing_context: 
        score -= 15

    # Detección de cierre de hilo
    closure_keywords = [
        "confirmed completion", "task completed", "no action", 
        "thanks", "got it", "acknowledged"
    ]
    if any(kw in summary for kw in closure_keywords): 
        score -= 20
    
    # 4. Nivel de acción/decisión
    if data.get("action_level") == "Mandatory": 
        score += 20
    elif data.get("action_level") == "Optional": 
        score += 10
    
    if data.get("decision_level") == "Required": 
        score += 20
    elif data.get("decision_level") == "Optional": 
        score += 10
    
    # 5. Urgencia
    urgency_weights = {
        "Immediate": 30, 
        "Short-term": 20, 
        "Medium-term": 10, 
        "Low": -5
    }
    detected_urgency = data.get("urgency", "Low")
    
    if not is_marketing_context:
        score += urgency_weights.get(detected_urgency, 0)
    else:
        if detected_urgency in ["Immediate", "Short-term"]: 
            score -= 10
    
    # 6. Bloqueos y dependencias
    if data.get("blocks_others"): 
        score += 25
    if data.get("decision_pending"): 
        score += 15
    
    # 7. Fechas límite
    if data.get("deadline") and not is_marketing_context:
        try:
            deadline = pd.to_datetime(data["deadline"])
            days_until = (deadline - pd.Timestamp.now()).days
            deadline_weight = 0
            
            if data.get("action_level") == "Mandatory":
                if days_until < 1: 
                    deadline_weight = 30
                elif days_until < 3: 
                    deadline_weight = 20
                elif days_until < 7: 
                    deadline_weight = 10
            elif data.get("action_level") == "Optional":
                if days_until < 1: 
                    deadline_weight = 10
            
            score += deadline_weight
        except: 
            pass
    
    return max(0, min(100, score))


def map_to_priority(
    sender: str, 
    subject: str, 
    body: str, 
    email_type: str, 
    action_level: str, 
    decision_level: str, 
    urgency: str, 
    blocks_others: bool, 
    score: int, 
    importance: str = "", 
    user_config: dict = None, 
    forced_priority: str = None, 
    is_phishing: bool = False, 
    is_spam: bool = False
) -> str:
    """
    Asignar el nivel final de prioridad (Alta/Media/Baja).
    
    Args:
        sender: Dirección del remitente
        subject: Asunto del correo
        body: Cuerpo del correo
        email_type: Tipo clasificado
        action_level: Obligatorio/Opcional/Ninguno
        decision_level: Requerido/Opcional/Ninguno
        urgency: Inmediato/Corto plazo/Mediano plazo/Bajo
        blocks_others: Si el correo bloquea a otras personas
        score: Puntuación de prioridad calculada
        importance: Indicador de importancia del correo
        user_config: Diccionario de preferencias del usuario
        forced_priority: Anulación forzada por LLM o reglas
        is_phishing: Resultado de detección de phishing
        is_spam: Resultado de detección de spam
        
    Returns:
        "High", "Medium", or "Low"
    """
    # Regla de seguridad
    if is_phishing or is_spam:
        return "Low"
    
    user_config = user_config or {}
    full_text = f"{subject} {body}"
    
    # Sobrescritura por remitente VIP
    if check_user_overrides(full_text, sender, user_config.get('vip_senders', [])):
        return "High"

    # Prioridad forzada por el usuario
    if forced_priority and forced_priority in ["High", "Medium", "Low"]:
        return forced_priority
    
    # Beneficios corporativos
    is_trusted = any(d in sender.lower() for d in TRUSTED_SENDER_DOMAINS)
    benefit_keywords = [
        "cesta navidad", "lote navidad", 
        "obsequio empresa", "bonus letter"
    ]
    if is_trusted and any(kw in subject.lower() for kw in benefit_keywords): 
        return "Medium"
    
    # Reglas de alta prioridad
    if any(kw in subject.lower() for kw in [
        "wants to share", "requested access", "sharing request"
    ]) and ("sharepoint" in sender.lower() or "confluence" in sender.lower()): 
        return "High"
    
    if urgency == "Immediate" or blocks_others: 
        return "High"
    if score >= 75: 
        return "High"
    if email_type in ["Approval_Request", "Decision_Required"]: 
        return "High"
    if action_level == "Mandatory" and urgency == "Short-term": 
        return "High"
    if email_type == "External_Request" and urgency in ["Immediate", "Short-term"]: 
        return "High"
    
    # Solicitudes de ayuda/soporte
    support_keywords = [
        "dare asking", "need your support", "asking for your support", 
        "need your help", "can you help", "asking for your help", 
        "appreciate your support", "is there a way", 
        "is there an easy way", "mentioned you"
    ]
    if any(kw in body.lower() for kw in support_keywords): 
        return "Medium"
    
    # Prioridad media (si hay acciones)
    if action_level in ["Mandatory", "Optional"]:
        if score >= 50:
            return "Medium"
        else:
            return "Medium"
    
    # Prioridad baja (spam de remitentes no confiables)
    if not is_trusted:
        spam_indicators = [
            "newsletter", "promotional", "unsubscribe", 
            "black friday", "sale"
        ]
        if any(indicator in full_text.lower() for indicator in spam_indicators):
            return "Low"
    
    # Prioridad baja (sin acción + baja urgencia)
    if score < 30 and action_level == "None":
        return "Low"
    if urgency == "Low" and action_level == "None":
        return "Low"
    
    return "Medium"
