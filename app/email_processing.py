"""
Módulo de procesamiento de emails
Funciones para limpieza, normalización y parsing de emails
"""

import re
import unicodedata
import json
from typing import Any, List, Dict
import pandas as pd

from config import MAX_BODY_CHARS

# ============================================================================
# JSON EXTRACTION UTILITY
# ============================================================================

def safe_extract_json(text: str) -> Dict[str, Any]:
    """
    Extract JSON from text that may contain markdown or additional text.
    Searches for the first valid JSON block.
    
    Args:
        text: Raw text potentially containing JSON
        
    Returns:
        Parsed JSON dict or empty dict if not found
    """
    # Try direct parsing first
    try:
        return json.loads(text)
    except:
        pass
    
    # Search for JSON code blocks
    json_patterns = [
        r'```json\s*(\{.*?\})\s*```', 
        r'```\s*(\{.*?\})\s*```',       
        r'(\{(?:[^{}]|(?:\{[^{}]*\}))*\})',  
    ]
    
    for pattern in json_patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                continue
    
    # If no valid JSON found, return empty dict
    return {}


# ============================================================================
# NORMALIZACIÓN Y LIMPIEZA DE TEXTO
# ============================================================================

def _norm(s: str) -> str:
    """
    Normaliza texto eliminando acentos, convirtiendo a minúsculas
    y normalizando espacios.
    """
    if not isinstance(s, str):
        s = "" if s is None else str(s)
    s = s.strip().lower()
    s = "".join(
        ch for ch in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(ch)
    )
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_text(x: Any) -> str:
    """
    Normaliza texto de emails eliminando caracteres especiales y URLs
    """
    s = "" if x is None else (x if isinstance(x, str) else str(x))
    s = s.replace("\u200c", " ").replace("\u200b", " ").replace("\ufeff", " ")
    s = re.sub(r"https?://\S+", "[URL]", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:MAX_BODY_CHARS]


# ============================================================================
# EXTRACCIÓN DE EMAILS Y CONTACTOS
# ============================================================================

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)


def _extract_emails(s: str) -> List[str]:
    """Extrae todas las direcciones de email de un texto"""
    if not s:
        return []
    return [e.lower() for e in EMAIL_RE.findall(s)]


def _split_contacts(field: str) -> List[Dict[str, str]]:
    """
    Parsea campos To/Cc que vengan como 'Name <email>' o listas separadas por coma/;
    
    Returns:
        List of dicts with 'raw', 'name', and 'email' keys
    """
    if not field:
        return []
    
    parts = re.split(r"[;,]\s*|\n+", str(field))
    out = []
    
    for p in parts:
        p = p.strip()
        if not p:
            continue
            
        emails = _extract_emails(p)
        email = emails[0] if emails else ""
        name = p
        
        if email:
            name = re.sub(r"<\s*" + re.escape(email) + r"\s*>", "", name).strip()
            name = re.sub(r"\(" + re.escape(email) + r"\)", "", name).strip()
        
        name = re.sub(r"\s+", " ", name).strip()
        out.append({"raw": p, "name": name, "email": email})
    
    return out


def clean_sender_display(name: str, addr: str) -> str:
    """
    Genera un nombre de display limpio para el remitente
    """
    name = (name or "").strip()
    if name:
        return name
    
    addr = (addr or "").strip()
    m = re.search(r"([^<\s]+)@([^>\s]+)", addr)
    if m:
        return m.group(1)
    
    return "Unknown"


def clean_contacts_display(raw_text):
    """
    Limpia los campos Para/CC para evitar duplicados como 'email' email.
    """
    if not raw_text or str(raw_text).lower() == 'nan':
        return "-"
    
    contacts = _split_contacts(str(raw_text))
    display_list = []
    
    for c in contacts:
        name = c.get('name', '').replace('"', '').replace("'", "").strip()
        email = c.get('email', '').strip()
        
        if not name or name.lower() == email.lower():
            display_list.append(email)
        else:
            display_list.append(name)
    
    return ", ".join(display_list)


# ============================================================================
# EXTRACCIÓN DE CONTENIDO PRINCIPAL
# ============================================================================

def extract_main(text: str, subject: str = "") -> str:
    """
    Extrae el contenido principal del email eliminando firmas y replies
    """
    if not text:
        return ""
    
    lower = text.lower()
    preserve_context = any(
        kw in subject.lower() 
        for kw in ["action needed", "approval", "endorsement", "review required"]
    )
    
    markers = [
        "-----original message-----", 
        "from:", "de:", 
        "enviado:", "sent:", 
        "_" * 30, 
        ">" * 5
    ]
    
    cut_at = None
    for m in markers:
        pos = lower.find(m)
        if pos != -1:
            cut_at = pos if cut_at is None else min(cut_at, pos)
    
    if preserve_context and cut_at:
        second_cut = None
        for m in markers:
            positions = [i for i in range(len(lower)) if lower[i:].startswith(m)]
            if len(positions) > 1:
                second_cut = positions[1] if second_cut is None else min(second_cut, positions[1])
        if second_cut and second_cut > cut_at:
            cut_at = second_cut
    
    if cut_at and cut_at > 50:
        text = text[:cut_at]
    
    signature_markers = [
        "unsubscribe", "confidential", "aviso de confidencialidad", 
        "best regards", "kind regards", "saludos", "atentamente"
    ]
    for sig in signature_markers:
        pos = lower.find(sig)
        if pos > 200:
            text = text[:pos]
            break
    
    return re.sub(r"\s+", " ", text).strip()


# ============================================================================
# IDENTIFICACIÓN DEL ROL DEL USUARIO
# ============================================================================

def identify_user_role(
    user_name: str, 
    from_name: str, 
    from_addr: str, 
    to_field: str, 
    cc_field: str,
    user_email: str = ""
) -> Dict[str, Any]:
    """
    Identifica el rol del usuario en un email (sender, primary recipient, CC)
    
    Returns:
        Dict with is_sender, is_primary_recipient, is_cc, user_variations
    """
    user_name_clean = _norm(user_name)
    from_name_clean = _norm(from_name)
    from_addr_clean = _norm(from_addr)
    
    # Generar variaciones del nombre
    user_parts = [p.strip() for p in user_name.split(',')]
    user_variations = []
    
    for part in user_parts:
        if not part.strip():
            continue
        user_variations.append(_norm(part))
        
        words = part.strip().split()
        for word in words:
            normalized_word = _norm(word)
            if len(normalized_word) >= 2:
                user_variations.append(normalized_word)
    
    user_variations.append(_norm(user_name))
    user_variations = list(dict.fromkeys(user_variations))
    
    # REMITENTE
    is_sender = False
    if user_email:
        from_emails = _extract_emails(from_addr)
        is_sender = user_email.lower() in [e.lower() for e in from_emails]
    else:
        is_sender = any(
            variation in from_name_clean or variation in from_addr_clean 
            for variation in user_variations
        )
    
    # TO
    to_emails = _extract_emails(str(to_field or ""))
    to_names = _norm(str(to_field or ""))
    
    is_primary_recipient = False
    if user_email:
        is_primary_recipient = user_email.lower() in [e.lower() for e in to_emails]
    else:
        is_primary_recipient = any(variation in to_names for variation in user_variations)
    
    # CC
    cc_emails = _extract_emails(str(cc_field or ""))
    cc_names = _norm(str(cc_field or ""))
    
    is_cc = False
    if user_email:
        is_cc = user_email.lower() in [e.lower() for e in cc_emails]
    else:
        is_cc = any(variation in cc_names for variation in user_variations)
    
    return {
        "is_sender": is_sender,
        "is_primary_recipient": is_primary_recipient,
        "is_cc": is_cc,
        "user_variations": user_variations,
        "user_email": user_email
    }


# ============================================================================
# UTILIDADES DE DOMINIO Y CONTEO
# ============================================================================

def sender_domain(addr: str) -> str:
    """Extrae el dominio de una dirección de email"""
    m = re.search(r"@([A-Za-z0-9.-]+\.[A-Za-z]{2,})", addr or "")
    return m.group(1).lower() if m else ""


def count_recipients(to_addr, cc_addr, bcc_addr) -> int:
    """Cuenta el número total de destinatarios"""
    count = 0
    for field in [to_addr, cc_addr, bcc_addr]:
        if field and isinstance(field, str) and str(field).lower() != "nan":
            count += len([x.strip() for x in str(field).split(";") if x.strip()])
    return count


# ============================================================================
# UNIFICACIÓN DE PROYECTOS (Anti-duplicados)
# ============================================================================

_PROJECT_PREFIX_RE = re.compile(r"^(proyecto|project|proj\.?|proy\.?)\s+", re.I)
_GENERIC_TAIL_TOKENS = {"implementation", "implementacion", "impl"}
_GENERIC_HEAD_TOKENS = {"implementation", "implementacion", "impl"}
_PROJECT_STOPWORDS = {"de", "del", "la", "el", "los", "las", "of", "the", "and", "y"}


def _strip_generic_head_tokens(norm_key: str) -> str:
    if not norm_key:
        return ""
    toks = norm_key.split()
    while toks and toks[0] in _GENERIC_HEAD_TOKENS:
        toks = toks[1:]
        while toks and toks[0] in _PROJECT_STOPWORDS:
            toks = toks[1:]
    return " ".join(toks).strip()


def _strip_generic_tail_tokens(norm_key: str) -> str:
    if not norm_key:
        return ""
    toks = norm_key.split()
    while toks and toks[-1] in _GENERIC_TAIL_TOKENS:
        toks = toks[:-1]
    return " ".join(toks).strip()


def _proj_norm_key_raw(s: str) -> str:
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
    raw = _proj_norm_key_raw(s)
    raw = _strip_generic_head_tokens(raw)
    return _strip_generic_tail_tokens(raw)


def _proj_display_name(s: str) -> str:
    if not isinstance(s, str):
        s = "" if s is None else str(s)
    s = s.strip()
    if not s:
        return ""
    s = _PROJECT_PREFIX_RE.sub("", s).strip()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _is_abbrev_orig(orig: str) -> bool:
    disp = _proj_display_name(orig or "")
    return bool(disp) and disp.isalpha() and disp.isupper() and 1 <= len(disp) <= 3


def _projects_similar(a_key: str, b_key: str, a_orig: str = "", b_orig: str = "") -> bool:
    """Determina si dos nombres de proyecto son similares"""
    if not a_key or not b_key:
        return False
    if a_key == b_key:
        return True
    
    # Importar difflib aquí para evitar dependencias circulares
    import difflib
    
    # Similaridad alta
    r = difflib.SequenceMatcher(None, a_key, b_key).ratio()
    if r >= 0.88:
        return True
    
    # Contención
    if (a_key in b_key or b_key in a_key) and min(len(a_key), len(b_key)) >= 4:
        return True
    
    # Proyectos cortos
    if max(len(a_key), len(b_key)) <= 12:
        if a_key[:3] == b_key[:3] and r >= 0.80:
            return True
    
    # Abreviatura vs nombre completo
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
    Construye un mapa de nombres de proyecto canónicos para unificar variaciones
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
    
    uniques = sorted(counts.keys(), key=lambda x: (-counts[x], len(x)))
    
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
    Unifica nombres de proyectos en un DataFrame
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
