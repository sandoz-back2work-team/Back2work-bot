"""
Configuración y constantes del proyecto Back2Work Bot
"""

# ============================================================================
# CONSTANTES DE OPENAI
# ============================================================================
MODEL = "gpt-4o-mini"
MAX_EMAILS = 10000
MAX_BODY_CHARS = 12000
LLM_BODY_CHARS = 4000
MAX_LLM_CALLS = 10000
TOP_N = 5

# ============================================================================
# DOMINIOS CONFIABLES (Whitelist)
# ============================================================================
TRUSTED_SENDER_DOMAINS = {
    "sandoz.com", "sandoz.net",
    "csod.com",
    "microsoft.com",
    "sharepointonline.com",
    "outlook.com",
    "regaloresponsable.es",
    "ilunion.com",
}

# ============================================================================
# COLORES CORPORATIVOS SANDOZ
# ============================================================================
SANDOZ_NAVY = "#001841"
SANDOZ_BLUE = "#48668E"
SANDOZ_LIGHT_BLUE = "#A8D5FF"
SANDOZ_OFFWHITE = "#F1ECE9"
SANDOZ_PALE = "#E6F1F8"
SANDOZ_SEQ = [SANDOZ_NAVY, SANDOZ_BLUE, SANDOZ_LIGHT_BLUE, SANDOZ_PALE]

# ============================================================================
# NOMBRES DE MESES EN ESPAÑOL
# ============================================================================
MONTHS_ES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
    7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}
