"""
Back2Work Bot - Main Application
=================================
Streamlit application for post-vacation email analysis.
"""

import streamlit as st
from streamlit_calendar import calendar
import plotly.express as px
import plotly.graph_objects as go
import json
import re
import hashlib
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime, date
import pandas as pd
from urllib.parse import quote
from openai import OpenAI

# Local imports
from config import (
    SANDOZ_NAVY, SANDOZ_BLUE, SANDOZ_LIGHT_BLUE, 
    SANDOZ_PALE, SANDOZ_SEQ, MAX_LLM_CALLS, MODEL,
    TRUSTED_SENDER_DOMAINS
)
from translations import TRANSLATIONS, t
from email_processing import (
    normalize_text, extract_main, clean_sender_display,
    clean_contacts_display, identify_user_role, 
    count_recipients, sender_domain
)
from security import is_phishing, is_spam, llm_security_analysis
from priority_engine import unify_projects_in_df, calculate_priority_score, map_to_priority
from llm import get_openai_client, llm_email_analysis_enhanced, llm_overall_summary
from gmail_connector import GmailConnector


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Back2Work Bot",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    div.stButton > button:first-child {
        background-color: #001841;
        color: white;
        border-radius: 5px;
        border: none;
        width: 100%;
    }
    div.stButton > button:hover {
        background-color: #48668E;
        color: white;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# VISUALIZATION HELPERS
# ============================================================================

def generate_interactive_plotly(df, lang="es"):
    """Generate interactive Plotly charts for dashboard."""
    colors = [SANDOZ_NAVY, SANDOZ_BLUE, SANDOZ_LIGHT_BLUE, SANDOZ_PALE]
    h_size = 320  
    
    # 1. Top Senders
    top_senders = df['sender'].value_counts().head(10).reset_index()
    top_senders.columns = ['sender', 'count']

    fig_senders = px.bar(
        top_senders, x='count', y='sender', orientation='h',
        color_discrete_sequence=[SANDOZ_BLUE]
    )
    fig_senders.update_layout(
        title="", 
        showlegend=False,
        clickmode='event+select',
        height=h_size,
        margin=dict(l=10, r=10, t=10, b=10) 
    )

    # 2. Priority (Treemap)
    prio_df = df['priority'].value_counts().reset_index()
    prio_df.columns = ['priority', 'count']

    fig_prio = px.treemap(
        prio_df, path=['priority'], values='count',
        color='priority', color_discrete_sequence=colors
    )
    fig_prio.update_layout(
        title="", 
        height=h_size,
        margin=dict(l=5, r=5, t=5, b=5) 
    )

    # 3. Email Type
    type_df = df['email_type'].value_counts().reset_index()
    type_df.columns = ['email_type', 'count']
    
    fig_type = px.bar(
        type_df, x='count', y='email_type', orientation='h',
        color_discrete_sequence=[SANDOZ_LIGHT_BLUE]
    )
    fig_type.update_layout(
        title="", 
        showlegend=False,
        height=h_size,
        margin=dict(l=10, r=10, t=10, b=10)
    )

    # 4. Projects
    proj_df = df[df['project'] != 'None']['project'].value_counts().reset_index()
    proj_df.columns = ['project', 'count']

    fig_proj = px.bar(
        proj_df, x='count', y='project', orientation='h',
        color_discrete_sequence=[SANDOZ_NAVY]
    )
    fig_proj.update_layout(
        title="", 
        showlegend=False,
        height=h_size,
        margin=dict(l=10, r=10, t=10, b=10)
    )
    
    return fig_senders, fig_prio, fig_type, fig_proj


# ============================================================================
# EMAIL DETAIL MODAL
# ============================================================================

@st.dialog("📧 Detalles del Correo")
def show_email_popup(row_data, lang, popup_key="default"):
    """Display email details in a modal popup."""
    
    # Priority badge with urgency
    action_level = row_data.get('action_level', 'None')
    urgency = row_data.get('urgency', 'Low')
    
    urgency_colors = {
        "Immediate":   ("#FF4B4B", "#FFE5E5"),  
        "Short-term":  ("#FF4B4B", "#FFE5E5"),  
        "Medium-term": ("#FFA500", "#FFF3E0"),  
        "Low":         ("#28A745", "#E8F5E9")   
    }
    
    text_color, bg_color = urgency_colors.get(urgency, ("#666666", "#F0F0F0"))
    
    # Translate levels
    if lang == "es":
        action_text = "Obligatoria" if action_level == "Mandatory" else "Opcional"
        urgency_map = {
            "Immediate": "Inmediata",
            "Short-term": "Corto plazo",
            "Medium-term": "Medio plazo",
            "Low": "Largo plazo"
        }
        urgency_text = urgency_map.get(urgency, urgency)
    else:
        action_text = action_level
        urgency_text = "Long term" if urgency == "Low" else urgency
    
    # Status banner
    st.markdown(
        f"""<div style="background-color: {bg_color}; 
                      padding: 16px; 
                      border-radius: 8px; 
                      margin-bottom: 20px;
                      border-left: 6px solid {text_color};">
        <strong style="color: {text_color}; font-size: 16px;">⚡ {action_text} · {urgency_text}</strong>
        </div>""",
        unsafe_allow_html=True
    )
    
    # Deadline
    deadline = row_data.get('deadline')
    if deadline and str(deadline) != 'None':
        st.markdown(f"### 📅 {deadline}")
    
    st.markdown("---")
    
    # Basic info
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown(f"**{t('modal_from', lang)}:**")
        st.markdown(f"**{t('modal_subject', lang)}:**")
        st.markdown(f"**{t('modal_date', lang)}:**")
        st.markdown(f"**{t('modal_to', lang)}:**") 
        st.markdown(f"**{t('modal_cc', lang)}:**")
    
    with col2:
        st.markdown(row_data['sender'])
        st.markdown(row_data['subject'])
        st.markdown(f"{row_data['date']}")
        st.markdown(clean_contacts_display(row_data.get('raw_to', '')))
        st.markdown(clean_contacts_display(row_data.get('raw_cc', '')))
    
    st.markdown("---")
    
    # Tasks
    st.markdown(f"### ✅ {'Tareas Pendientes:' if lang == 'es' else 'Pending Tasks:'}")
    
    tasks = row_data.get('tasks', [])
    if tasks and len(tasks) > 0:
        for i, task in enumerate(tasks, 1):
            st.markdown(
                f"""<div style="background-color: #F8F9FA; 
                              padding: 12px; 
                              border-radius: 6px; 
                              margin-bottom: 8px;
                              border-left: 4px solid #001841;">
                <strong>{i}.</strong> {task}
                </div>""",
                unsafe_allow_html=True
            )
    else:
        st.caption("_" + ("Sin tareas específicas" if lang == "es" else "No specific tasks") + "_")
    
    st.markdown("---")
    
    # Summary
    st.markdown(f"### 📝 {'Resumen:' if lang == 'es' else 'Summary:'}")
    st.info(row_data.get('summary', 'Sin resumen disponible' if lang == "es" else 'No summary available'))
    
    st.markdown("---")

    # Gmail integration with authuser
    current_user_email = st.session_state.get('user_email', '')
    thread_id = str(row_data.get('threadId', '')).strip()
    has_thread_id = (thread_id and thread_id.lower() not in ['nan', 'none', ''])

    if has_thread_id:
        if current_user_email:
            gmail_link = f"https://mail.google.com/mail/?authuser={current_user_email}#inbox/{thread_id}"
        else:
            gmail_link = f"https://mail.google.com/mail/u/0/#inbox/{thread_id}"
            
        btn_label = t("btn_open_thread", lang)
        btn_help = t("help_open_thread", lang, email=current_user_email or 'default')
        
    else:
        raw_sender = row_data.get('sender', '')
        to_email = raw_sender.split('<')[1].replace('>', '').strip() if '<' in raw_sender else raw_sender.strip()
        
        raw_subject = row_data.get('subject', '')
        subject_reply = raw_subject if raw_subject.lower().startswith("re:") else f"Re: {raw_subject}"
        
        base_link = "https://mail.google.com/mail/?view=cm&fs=1"
        if current_user_email:
            base_link += f"&authuser={current_user_email}"
            
        gmail_link = f"{base_link}&to={quote(to_email)}&su={quote(subject_reply)}"
        
        btn_label = t("btn_reply_new", lang)
        btn_help = t("help_reply_new", lang)

    # Action buttons
    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        if st.button(
            "👁️ " + t("view_details", lang),
            use_container_width=True,
            type="secondary",
            key=f"view_full_from_popup_{popup_key}"
        ):
            st.session_state[f"show_body_{popup_key}"] = True

    with col_btn2:
        st.link_button(
            btn_label,
            url=gmail_link,
            use_container_width=True,
            type="primary",
            help=btn_help
        )

    # Show body if requested
    if st.session_state.get(f"show_body_{popup_key}", False):
        st.markdown("### " + t("modal_body", lang))
        body_content = row_data.get('raw_body', 'No content available')
        st.text_area(
            label="",
            value=body_content,
            height=300,
            disabled=True,
            label_visibility="collapsed",
            key=f"body_area_{popup_key}"
        )



# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    col_lang, col_spacer = st.columns([1, 5])
    
    #IDIOMA
    if 'language' not in st.session_state:
        st.session_state.language = 'es'

    st.sidebar.markdown("### 🌐 Idioma / Language")
    
    col_es, col_en = st.sidebar.columns(2)
    
    # Botón Español
    if col_es.button("🇪🇸 Español"):
        st.session_state.language = 'es'
        st.rerun()
        
    # Botón Inglés
    if col_en.button("🇬🇧 English"):
        st.session_state.language = 'en'
        st.rerun() 
    
    lang = st.session_state.language
    
    st.sidebar.markdown("---")

    # TÍTULO
    st.title(f"📧 {t('page_title', lang)}")  
    st.write(t("page_subtitle", lang))

    st.sidebar.header(t("sidebar_config", lang)) 

    # FUENTES
    st.sidebar.subheader(t("source_title", lang)) 
    
    # Opciones traducidas dinámicamente
    option_csv = t("source_csv", lang)
    option_gmail = t("source_gmail", lang)
    
    data_source = st.sidebar.radio(
        t("source_select", lang),                
        [option_csv, option_gmail], 
        help=t("source_help", lang)           
    )
    
    uploaded_file = None
    gmail_connector = None
    
    if data_source == option_csv:
        uploaded_file = st.sidebar.file_uploader(
            t("upload_csv", lang), 
            type=["csv"],
            key="csv_uploader"
        )
    
    elif data_source == option_gmail:
        st.sidebar.info(t("gmail_auth_info", lang)) 
        
        if st.sidebar.button(t("gmail_auth_btn", lang), type="primary"):
            try:
                gmail_connector = GmailConnector()
            except Exception as e:
                st.error(f"Error al iniciar el conector: {e}")
                return
    
            with st.spinner(t("gmail_authenticating", lang)): 
                if gmail_connector.authenticate():
                    st.session_state['gmail_authenticated'] = True
                    st.session_state['gmail_connector'] = gmail_connector
                    
                    try:
                        email = gmail_connector.get_user_email()
                        name = gmail_connector.get_user_display_name()
                        st.session_state['user_email'] = email
                        st.session_state['user_name_from_gmail'] = name
                        
                        st.success(t("gmail_success", lang, email=email))
                        st.info(t("gmail_id", lang, name=name))
                    except:
                        st.success("✅ Conectado correctamente")
                        
                else:
                    st.error(t("gmail_error", lang))
    
    
    # Detección automática (Gmail) vs manual (CSV)
    if st.session_state.get('gmail_authenticated'):
        default_name = st.session_state.get('user_name_from_gmail', 'Usuario')
        help_text = t("auto_name_help", lang)
    else:
        default_name = ""
        help_text = t("user_name_help", lang)
    
    user_name_input = st.sidebar.text_input(
        t("user_name_label", lang), 
        value=default_name,
        placeholder=t("user_name_placeholder", lang), 
        help=help_text
    )
    
    # Validación final
    if not user_name_input or not user_name_input.strip():
        user_name_input = "Usuario" 

    client = get_openai_client()
    user_key = None 
    
    if not client:
        st.sidebar.markdown("---")
        st.sidebar.subheader(t("api_key_header", lang)) 
        st.sidebar.info(t("api_key_missing_info", lang))
        
        default_key = st.session_state.get('manual_openai_key', '')
        user_key = st.sidebar.text_input(
            "API Key", 
            type="password", 
            value=default_key,
            placeholder=t("api_key_placeholder", lang), 
            help=t("api_key_help", lang) 
        )
    
    if user_key:
        try:
            client = OpenAI(api_key=user_key)
            st.session_state['manual_openai_key'] = user_key
            st.sidebar.success(t("api_key_success", lang)) 
        except Exception as e:
            st.sidebar.error(t("api_key_load_error", lang, error=e))
            client = None
    
    
    #FECHAS
    st.sidebar.subheader(t("vacation_period", lang))
    
    start_date, end_date = None, None

    dates = st.sidebar.date_input(
        t("date_range_label", lang), 
        [] 
    )

    # Lógica de validación
    if len(dates) == 2:
        start_date, end_date = dates
        msg = f"Del {start_date} al {end_date}" if lang == "es" else f"From {start_date} to {end_date}"
        st.sidebar.success(msg)

    st.sidebar.subheader(t("priorities_section", lang))
    vip_input = st.sidebar.text_area(
        t("vip_senders", lang), 
        placeholder=t("vip_placeholder", lang)
    )
    proj_input = st.sidebar.text_area(
        t("key_projects", lang), 
        placeholder=t("projects_placeholder", lang)
    )

    kw_input = st.sidebar.text_area( 
        t("priority_rules_label", lang),     
        value="", 
        placeholder=t("priority_rules_placeholder", lang), 
        help=t("priority_rules_help", lang) 
    )
    
    run_btn = st.sidebar.button(t("start_analysis", lang), type="primary")


    if "result_df" not in st.session_state: st.session_state.result_df = None
    if "summary_text" not in st.session_state: 
        st.session_state.summary_text = ""
    
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": t("chat_welcome", lang)}
        ]
    else:
        if len(st.session_state.messages) > 0 and st.session_state.messages[0]["role"] == "assistant":
            expected_welcome = t("chat_welcome", lang)
            if "analizados" in st.session_state.messages[0]["content"] or "analyzed" in st.session_state.messages[0]["content"]:
                st.session_state.messages[0]["content"] = expected_welcome

    # EJECUCIÓN (LÓGICA 'RUN' DEL SCRIPT)
    if run_btn:

        if start_date is None or end_date is None:

            st.error(t("date_warning", lang)) 
            return
            
        # Validar fuente de datos
        if data_source == option_gmail and not st.session_state.get('gmail_authenticated'): 
            st.error(t("gmail_warning_auth", lang)) 
            return
        
        if data_source == option_csv and not uploaded_file:
            st.error(t("upload_error", lang))
            return
        
        if not client:
            st.error(t("api_key_error", lang))
            return
        
        with st.spinner(t("processing", lang)):
            if data_source == option_csv:
                try:
                    df = pd.read_csv(uploaded_file, encoding="utf-8", on_bad_lines="skip")
                except:
                    df = pd.read_csv(uploaded_file, encoding="latin1", on_bad_lines="skip")
            
            elif data_source == option_gmail:
                gmail_connector = st.session_state.get('gmail_connector')
                
                # Determinar rango de fechas
                if start_date and end_date:
                    fetch_start = datetime.combine(start_date, datetime.min.time())
                    fetch_end = datetime.combine(end_date + pd.Timedelta(days=1), datetime.min.time())
                else:
                    fetch_start = None
                    fetch_end = None
                
                # Descargar emails
                emails_data = gmail_connector.fetch_emails(
                    start_date=fetch_start,
                    end_date=fetch_end,
                    max_results=10000,
                    query="",
                    lang=lang 
                )
                
                if not emails_data:
                    st.error(t("no_emails_found", lang))
                    return
                
                # Convertir a DataFrame
                df = pd.DataFrame(emails_data)
                
            # DATE FILTERING
            range_str = t("range_all", lang)
            if start_date and end_date and 'Received_date' in df.columns:
                df['Received_date'] = pd.to_datetime(df['Received_date'], errors='coerce')
                mask = (df['Received_date'].dt.date >= start_date) & (df['Received_date'].dt.date <= end_date)
                df = df.loc[mask]
                range_str = t("range_from_to", lang, start=start_date, end=end_date)
            
            if df.empty:
                st.error(f"❌ No hay emails en {range_str}.")
            else:

                df_proc = df.copy()

                col = {
                    "subject": "Subject", "body": "Body", 
                    "from_name": "From: (Name)", "from_addr": "From: (Address)",
                    "importance": "Importance", "to_addr": "To: (Address)", 
                    "cc_addr": "CC: (Address)", "bcc_addr": "BCC: (Address)", 
                    "to_name": "To: (Name)","cc_name": "CC: (Name)"
                }
                
                rows = []
                llm_calls = 0
                prog_bar = st.progress(0)
                
                vip_senders_list = [x.strip() for x in vip_input.split(',') if x.strip()]
                priority_projects_list = [x.strip() for x in proj_input.split(',') if x.strip()]
                instruction_clean = kw_input.strip()

                # MAIN LOOP
                for i, (idx, row) in enumerate(df_proc.iterrows()):
                    prog_bar.progress(min((i + 1) / len(df_proc), 1.0))
                    
                    user_conf = {
                        "vip_senders": vip_senders_list,
                        "priority_projects": priority_projects_list,  
                        "priority_instruction": instruction_clean,
                        "to_field": str(row.get(col["to_addr"], "")),
                        "cc_field": str(row.get(col["cc_addr"], ""))
                    }
                                    
                    subj = normalize_text(row.get(col["subject"], ""))
                    body = normalize_text(row.get(col["body"], ""))
                    s_name = normalize_text(row.get(col["from_name"], ""))
                    s_addr = normalize_text(row.get(col["from_addr"], ""))

                    user_role = identify_user_role(
                        user_name=user_name_input,
                        from_name=s_name,
                        from_addr=s_addr,
                        to_field=str(row.get(col["to_addr"], "")),
                        cc_field=str(row.get(col["cc_addr"], ""))
                    )
                    

                    imp = str(row.get(col["importance"], "")).strip()
                    if imp:
                        imp = imp.lower().strip()
                        if imp in ['high', 'importante', 'alta']: imp = 'high'
                        elif imp in ['normal', '']: imp = 'normal'

                    
                    to_count = count_recipients(str(row.get(col["to_addr"], "")), str(row.get(col["cc_addr"], "")), str(row.get(col["bcc_addr"], "")))

                    # 1. Detection
                    is_phish = is_phishing(subj, body, s_addr)
                    is_sp = is_spam(subj, body, s_addr)
                    
                    # 2. Security LLM
                    security_analysis = {}
                    if llm_calls < MAX_LLM_CALLS and (is_phish or is_sp) and llm_calls < 30:
                        security_analysis = llm_security_analysis(client, subj, f"{s_name} <{s_addr}>", body)
                        llm_calls += 1
                    
                    risk_level = security_analysis.get("risk_level", "low")
                    is_phish = security_analysis.get("is_phishing", is_phish)
                    is_sp = security_analysis.get("is_spam", is_sp)

                    # 3. Whitelist Check
                    dom = sender_domain(s_addr)
                    full_text_check = (subj + " " + s_name + " " + s_addr + " " + body[:500]).lower()
                    whitelist_keywords = ["quip digest", "quip updates", "sandoz group ag", "weekly digest", "iberia", "vuelo", "flight", "jira", "confluence", "sharepoint"]
                    
                    is_trusted = (dom in TRUSTED_SENDER_DOMAINS)
                    is_whitelisted = any(kw in full_text_check for kw in whitelist_keywords)
                    
                    if is_trusted or is_whitelisted:
                        is_phish = False
                        is_sp = False
                        if risk_level == "critical": risk_level = "medium"

                    # 5. Content Analysis
                    main_body = extract_main(body, subj)
                    raw_date = row.get("Received_date")
                    try:
                        dt_obj = pd.to_datetime(raw_date, utc=True)
                        email_date_str = dt_obj.strftime('%Y-%m-%d (%A)')
                    except:
                        email_date_str = str(raw_date)
                    
                    analysis = {}
                    if llm_calls < MAX_LLM_CALLS:
                        analysis = llm_email_analysis_enhanced(
                            client, subj, f"{s_name} <{s_addr}>", main_body, to_count, imp, user_conf, user_name_input, email_date_str, lang=lang, is_phishing=is_phish, is_spam=is_sp
                        )

                        if analysis.get("deadline") and analysis.get("deadline") != "None":
                            try:

                                dl_date = pd.to_datetime(analysis["deadline"]).date()

                                email_date_ref = date.today()
                               
                                dias_diferencia = (dl_date - email_date_ref).days
                                
                                if dias_diferencia < 0:
                                    analysis["urgency"] = "Immediate"
                                elif dias_diferencia <= 2: 
                                    analysis["urgency"] = "Immediate"  
                                elif dias_diferencia <= 7:
                                    analysis["urgency"] = "Short-term"  
                                elif dias_diferencia <= 14:
                                    analysis["urgency"] = "Medium-term" 
                                else:
                                    analysis["urgency"] = "Low"          
                            except Exception as e:
                                pass
                        

                        if user_role["is_cc"] and analysis.get("tasks"):
                            main_body_lower = main_body.lower()
                            user_mentioned = False
                            
                            for variation in user_role["user_variations"]:
                                # ========== PATRONES MEJORADOS DE MENCIÓN ==========
                                patterns = [
                                    f"@{variation}",                 
                                    f"dear {variation}",             
                                    f"hi {variation}",                
                                    f"hola {variation}",               
                                    f"{variation}, please",            
                                    f"{variation}, can you",           
                                    f"{variation}, could you",         
                                    f"{variation}, podrias",          
                                    f"{variation}, necesitamos que",   
                                    f"{variation} -",                  
                                    f"cc: {variation}",                
                                    f"@{variation[0]}",                
                                    f"{variation},",
                                    f"{variation}:",
                                ]
                                
                                action_verbs = ["revisar", "confirmar", "actualizar", "encargarte", "review", "confirm", "update", "check"]
                                for verb in action_verbs:
                                    if f"{variation}" in main_body_lower and verb in main_body_lower:
                                        name_pos = main_body_lower.find(variation)
                                        verb_pos = main_body_lower.find(verb, name_pos)
                                        if 0 < verb_pos - name_pos < 50:
                                            user_mentioned = True
                                            break
                                
                                if user_mentioned:
                                    break
                                    
                                if any(pattern in main_body_lower for pattern in patterns):
                                    user_mentioned = True
                                    break
                            
                            if not user_mentioned:
                                analysis["tasks"] = []
                                analysis["action_level"] = "None"
                                analysis["requires_action"] = False
                                if analysis.get("email_type") not in ["FYI_Informational", "Notification_System"]:
                                    analysis["email_type"] = "FYI_Informational"
                                analysis["summary"] = f"[CC - FYI] {analysis.get('summary', '')}"
                        llm_calls += 1
                    else:
                        # FALLBACK HEURÍSTICO
                        body_preview = main_body[:200].replace("\n", " ").strip()
                        s_first = clean_sender_display(s_name, s_addr).split()[0]
                        subj_low = subj.lower()
                        body_low = main_body.lower()
                        
                        email_type = "FYI_Informational"
                        if "csod.com" in s_addr.lower(): email_type = "Notification_System"
                        elif any(k in subj_low for k in ["action needed", "required"]): email_type = "Action_Request"
                        
                        action_level = "None"
                        if any(k in body_low for k in ["must complete", "mandatory"]): action_level = "Mandatory"
                        
                        urgency = "Low"
                        if any(k in subj_low for k in ["urgent", "today"]): urgency = "Immediate"
                        
                        tasks = []
                        if action_level == "Mandatory": tasks = ["Complete required action"]
                        
                        score_heur = 50
                        if action_level == "Mandatory": score_heur += 20
                        if urgency == "Immediate": score_heur += 30
                        
                        prio = "Medium"
                        if score_heur >= 75: prio = "High"
                        
                        analysis = {
                            "priority": prio, "score": score_heur, "summary": f"Email from {s_first}: {subj[:50]}",
                            "tasks": tasks, "email_type": email_type, "action_level": action_level,
                            "urgency": urgency, "deadline": None, "project": "None", "blocks_others": False, "decision_pending": False
                        }
                    

                    forced_val = analysis.get("forced_priority") 

                    score = calculate_priority_score(analysis, imp, subj)
                    
                    # 2. Mapeo
                    priority = map_to_priority(
                        sender=clean_sender_display(s_name, s_addr), 
                        subject=subj, 
                        body=main_body,
                        email_type=analysis.get("email_type", "FYI"), 
                        action_level=analysis.get("action_level", "None"),
                        decision_level=analysis.get("decision_level", "None"),
                        urgency=analysis.get("urgency", "Low"),
                        blocks_others=analysis.get("blocks_others", False), 
                        score=score, 
                        importance=imp, 
                        user_config=user_conf,
                        forced_priority=forced_val 
                    )
                    
                    rows.append({
                        "date": str(row.get("Received_date", "")),
                        "sender": clean_sender_display(s_name, s_addr),
                        "subject": subj,
                        "priority": priority, 
                        "score": score,
                        "summary": analysis.get("summary", ""),
                        "tasks": analysis.get("tasks", []),
                        "email_type": analysis.get("email_type", "FYI"),
                        "deadline": analysis.get("deadline", None),
                        "requires_action": analysis.get("requires_action", False),
                        "project": analysis.get("project", "None"),
                        "action_level": analysis.get("action_level", "None"),
                        "urgency": analysis.get("urgency", "Low"),
                        "is_phishing": is_phish,
                        "is_spam": is_sp,
                        "raw_body": row.get(col["body"], ""),          
                        "raw_to": str(row.get(col["to_addr"], "")),    
                        "raw_cc": str(row.get(col["cc_addr"], "")),   
                        "raw_from_addr": s_addr,
                        "raw_to_name": str(row.get(col["to_name"], "")),
                        "raw_cc_name": str(row.get(col["cc_name"], "")),
                        "threadId": str(row.get("threadId", row.get("thread_id", "")))
                    })
                
                st.session_state.result_df = pd.DataFrame(rows)

            
                # DEDUPLICACIÓN DE HILOS
                if not st.session_state.result_df.empty and 'threadId' in st.session_state.result_df.columns:
                    df_temp = st.session_state.result_df.copy()
                    
                    df_temp['dt_sort'] = pd.to_datetime(df_temp['date'], errors='coerce')
                    
                    indices_to_downgrade = []
                    
                    groups = df_temp.dropna(subset=['threadId']).groupby('threadId')
                    
                    for thread_id, group in groups:
                        if len(group) > 1:
                            group = group.sort_values(by='dt_sort', ascending=False)
                            
                            old_indices = group.index[1:].tolist()
                            indices_to_downgrade.extend(old_indices)
                    
                    if indices_to_downgrade:
                        st.session_state.result_df.loc[indices_to_downgrade, 'priority'] = 'Low'
                        st.session_state.result_df.loc[indices_to_downgrade, 'deadline'] = None

                        history_prefix = "[HISTORIAL - Ver último correo]" if lang == "es" else "[HISTORY - See last email]"
                        check_tag = "[HISTORIAL" if lang == "es" else "[HISTORY"
                        
                        for idx in indices_to_downgrade:
                            st.session_state.result_df.at[idx, 'tasks'] = []
                            current_summary = st.session_state.result_df.at[idx, 'summary']

                            if check_tag not in str(current_summary):
                                st.session_state.result_df.at[idx, 'summary'] = f"{history_prefix} {current_summary}"


                # UNIFICACIÓN DE PROYECTOS
                st.session_state.result_df = unify_projects_in_df(st.session_state.result_df, project_col="project")
                
                # Generar Resumen
                high_prio = st.session_state.result_df[st.session_state.result_df["priority"] == "High"].sort_values("score", ascending=False).to_dict("records")
                st.session_state.summary_text = llm_overall_summary(client, high_prio, len(st.session_state.result_df), range_str,lang=lang)

    

    # PANTALLA DE RESULTADOS
    if st.session_state.result_df is not None:
        
        # 1. MENSAJE PERSISTENTE
        total_emails = len(st.session_state.result_df)
        st.success(t("analysis_complete", lang, count=total_emails))

        df_res = st.session_state.result_df
        
        # 2. CREACIÓN DE 5 PESTAÑAS 
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            t("tab_summary", lang),      
            t("tab_calendar", lang),     
            t("tab_inbox", lang), 
            t("tab_charts", lang),
            t("tab_chat", lang)
        ])

        # =========================================================
        # PESTAÑA 1: RESUMEN Y ACCIONES
        # =========================================================
        with tab1:
            # RESUMEN EJECUTIVO
            st.subheader(t("executive_summary", lang))
            st.info(st.session_state.summary_text)
            
            st.markdown("---")
            
            # ACCIONES REQUERIDAS
            st.subheader(t("actions_table_title", lang))
            
            actions_df = df_res[
                df_res['tasks'].apply(lambda x: isinstance(x, list) and len(x) > 0)
            ].copy()
            
            if not actions_df.empty:
                today = date.today()

                actions_df['deadline_dt'] = pd.to_datetime(actions_df['deadline'], errors='coerce').dt.date
                
                actions_df['es_vencida'] = actions_df['deadline_dt'].apply(
                    lambda x: x < today if pd.notna(x) else False
                )


                prio_rank_map = {"High": 1, "Medium": 2, "Low": 3}
                actions_df['prio_rank'] = actions_df['priority'].map(prio_rank_map).fillna(4)


                actions_df['deadline_sort'] = actions_df['deadline_dt'].fillna(pd.Timestamp('2099-12-31').date())

                actions_df = actions_df.sort_values(
                    by=['deadline_sort', 'prio_rank'],
                    ascending=[True, True]
                )
                
                # SECCIÓN DE FILTROS                                         
                st.markdown(t("filters_title", lang))
                
                col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                
                prio_map = {
                    "High": "Alta" if lang == "es" else "High",
                    "Medium": "Media" if lang == "es" else "Medium",
                    "Low": "Baja" if lang == "es" else "Low"
                }
                prio_reverse = {v: k for k, v in prio_map.items()}
                
                tipo_map = {
                    "Mandatory": "Obligatoria" if lang == "es" else "Mandatory",
                    "Optional": "Opcional" if lang == "es" else "Optional"
                }
                tipo_reverse = {v: k for k, v in tipo_map.items()}
                
                with col_f1:
                    prio_options_display = list(prio_map.values())
                    default_prio = [prio_map["High"], prio_map["Medium"]]
                    
                    selected_prio_display = st.multiselect(
                        "Prioridad" if lang == "es" else "Priority",
                        options=prio_options_display,
                        default=default_prio,  
                        key="filter_prio_actions"
                    )
                    selected_prio = [prio_reverse[x] for x in selected_prio_display]
                
                with col_f2:
                    # Filtro Tipo - SOLO OBLIGATORIA POR DEFECTO
                    tipo_options_display = list(tipo_map.values())
                    default_tipo = [tipo_map["Mandatory"]] 
                    
                    selected_tipo_display = st.multiselect(
                        "Tipo" if lang == "es" else "Type",
                        options=tipo_options_display,
                        default=default_tipo, 
                        key="filter_tipo_actions"
                    )
                    selected_tipo = [tipo_reverse[x] for x in selected_tipo_display]
                
                with col_f3:
                    remitentes_unicos = sorted(actions_df['sender'].unique())
                    selected_sender = st.multiselect(
                        "Remitente" if lang == "es" else "Sender",
                        options=remitentes_unicos,
                        default=[],
                        key="filter_sender_actions"
                    )
                
                with col_f4:
                    solo_vencidas = st.checkbox(
                        t("filter_only_overdue", lang),
                        value=False,
                        key="filter_vencidas"
                    )
                
                # APLICAR FILTROS
                actions_filtered = actions_df.copy()
                
                if selected_prio:
                    actions_filtered = actions_filtered[actions_filtered['priority'].isin(selected_prio)]
                
                if selected_tipo:
                    actions_filtered = actions_filtered[actions_filtered['action_level'].isin(selected_tipo)]
                
                if selected_sender:
                    actions_filtered = actions_filtered[actions_filtered['sender'].isin(selected_sender)]
                
                if solo_vencidas:
                    actions_filtered = actions_filtered[actions_filtered['es_vencida'] == True]
                
                total_original = len(actions_df)
                total_filtrado = len(actions_filtered)
                
                if total_filtrado < total_original:
                    st.info(t("showing_tasks", lang, count=total_filtrado, total=total_original))
                
                st.markdown("---")
                
                if 'completed_tasks' not in st.session_state:
                    st.session_state.completed_tasks = set()
                if 'in_progress_tasks' not in st.session_state:
                    st.session_state.in_progress_tasks = set()
                if 'task_states' not in st.session_state:
                    st.session_state.task_states = {}
                
                if 'selected_row_index' not in st.session_state:
                    st.session_state.selected_row_index = None
                
                actions_view = actions_filtered.reset_index(drop=True)
                
                status_column = []
                check_column = []
                tipo_column = []
                priority_column = []
                fecha_limite_column = []
                
                
                status_map_normalization = {
                    "📋 Pendiente": "pending", "📋 Pending": "pending",
                    "🔵 En Progreso": "progress", "🔵 In Progress": "progress",
                    "✅ Hecho": "done", "✅ Done": "done"
                }
                
                for idx, row in actions_view.iterrows():
                    task_id = f"{row['sender']}_{row['subject']}_{row['date']}"
                    
                    raw_state = st.session_state.task_states.get(task_id, "pending")
                    
                    internal_status = status_map_normalization.get(raw_state, "pending")
                    
                    if internal_status == "done":
                        estado = t("status_done", lang)
                    elif internal_status == "progress":
                        estado = t("status_progress", lang)
                    else:
                        estado = t("status_pending", lang)
                    
                    st.session_state.task_states[task_id] = estado
                    status_column.append(estado)
                    
                    check_column.append(idx == st.session_state.selected_row_index)

                    # Tipo
                    if row['action_level'] == 'Mandatory':
                        tipo_column.append("Obligatoria" if lang == "es" else "Mandatory")
                    else:
                        tipo_column.append("Opcional" if lang == "es" else "Optional")

                    # Prioridad con emojis
                    if row['priority'] == 'High':
                        priority_column.append("🔴 Alta" if lang == "es" else "🔴 High")
                    elif row['priority'] == 'Medium':
                        priority_column.append("🟠 Media" if lang == "es" else "🟠 Medium")
                    else:
                        priority_column.append("🟢 Baja" if lang == "es" else "🟢 Low")

                    # Fecha Límite
                    deadline_val = row['deadline']
                    if pd.isna(deadline_val) or str(deadline_val) in ['', 'None', 'nan']:
                        fecha_limite_column.append('-')
                    elif row['es_vencida']:
                        fecha_limite_column.append(f"⚠️ {deadline_val}")
                    else:
                        fecha_limite_column.append(str(deadline_val))
                
                # Crear DataFrame para mostrar
                display_df = pd.DataFrame({
                    '✓': check_column,
                    'Estado': status_column,
                    'Fecha Límite': fecha_limite_column,
                    'Prioridad': priority_column,
                    'Tipo': tipo_column,
                    'Remitente': actions_view['sender'],
                    'Asunto': actions_view['subject'],
                    'Tareas Extraídas': actions_view['tasks'].apply(
                        lambda x: '; '.join(x) if isinstance(x, list) else str(x)
                    )
                })

                display_df['✓'] = display_df['✓'].astype(bool)
                
                # CAPTION
                vencidas_count = actions_view['es_vencida'].sum()
                
                caption_text = t("table_caption", lang)
                
                if vencidas_count > 0:
                    caption_text += t("table_caption_overdue", lang, count=vencidas_count)
                
                st.caption(caption_text)
                
                # CSS PARA COLOREAR LAS COLUMNAS
                st.markdown("""
                <style>
                /* Colores para celdas de Prioridad */
                [data-testid="stDataFrame"] [data-testid="stDataFrameCell"]:has(div:contains("🔴 Alta")) {
                    background: linear-gradient(135deg, #DC2626 0%, #B91C1C 100%) !important;
                }
                
                [data-testid="stDataFrame"] [data-testid="stDataFrameCell"]:has(div:contains("🔴 Alta")) div {
                    color: white !important;
                    font-weight: 700 !important;
                    text-align: center !important;
                }
                
                [data-testid="stDataFrame"] [data-testid="stDataFrameCell"]:has(div:contains("🟠 Media")) {
                    background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%) !important;
                }
                
                [data-testid="stDataFrame"] [data-testid="stDataFrameCell"]:has(div:contains("🟠 Media")) div {
                    color: white !important;
                    font-weight: 700 !important;
                    text-align: center !important;
                }
                
                [data-testid="stDataFrame"] [data-testid="stDataFrameCell"]:has(div:contains("🟢 Baja")) {
                    background: linear-gradient(135deg, #10B981 0%, #059669 100%) !important;
                }
                
                [data-testid="stDataFrame"] [data-testid="stDataFrameCell"]:has(div:contains("🟢 Baja")) div {
                    color: white !important;
                    font-weight: 700 !important;
                    text-align: center !important;
                }
                
                /* Colores para celdas de Tipo */
                [data-testid="stDataFrame"] [data-testid="stDataFrameCell"]:has(div:contains("🔴 Obligatoria")) {
                    background: linear-gradient(135deg, #DC2626 0%, #991B1B 100%) !important;
                }
                
                [data-testid="stDataFrame"] [data-testid="stDataFrameCell"]:has(div:contains("🔴 Obligatoria")) div {
                    color: white !important;
                    font-weight: 600 !important;
                    text-align: center !important;
                }
                
                [data-testid="stDataFrame"] [data-testid="stDataFrameCell"]:has(div:contains("🔵 Opcional")) {
                    background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%) !important;
                }
                
                [data-testid="stDataFrame"] [data-testid="stDataFrameCell"]:has(div:contains("🔵 Opcional")) div {
                    color: white !important;
                    font-weight: 600 !important;
                    text-align: center !important;
                }
                
                /* ========== FECHAS VENCIDAS - GRIS CLARO MEJORADO ========== */
                [data-testid="stDataFrame"] [data-testid="stDataFrameCell"]:has(div:contains("⚠️")) {
                    background: linear-gradient(135deg, #E8E8E8 0%, #F5F5F5 100%) !important;
                    border: 1px solid #CCCCCC !important;
                }
                
                [data-testid="stDataFrame"] [data-testid="stDataFrameCell"]:has(div:contains("⚠️")) div {
                    color: #666666 !important;
                    font-weight: 600 !important;
                    text-align: center !important;
                    font-style: italic !important;
                }
                /* =========================================================== */
                
                /* Bordes redondeados en celdas coloreadas */
                [data-testid="stDataFrame"] [data-testid="stDataFrameCell"]:has(div:contains("🔴")),
                [data-testid="stDataFrame"] [data-testid="stDataFrameCell"]:has(div:contains("🟠")),
                [data-testid="stDataFrame"] [data-testid="stDataFrameCell"]:has(div:contains("🟢")),
                [data-testid="stDataFrame"] [data-testid="stDataFrameCell"]:has(div:contains("🔵")),
                [data-testid="stDataFrame"] [data-testid="stDataFrameCell"]:has(div:contains("⚠️")) {
                    border-radius: 6px !important;
                    padding: 8px !important;
                }
                </style>
                """, unsafe_allow_html=True)

                options_status = [t("status_pending", lang), t("status_progress", lang), t("status_done", lang)]
                
                
                # TABLA EDITABLE
                edited_data = st.data_editor(
                    display_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        '✓': st.column_config.CheckboxColumn(
                            "✓",
                            help=t("check_column_help", lang),
                            default=False,
                            width="small"
                        ),
                        'Estado': st.column_config.SelectboxColumn(
                            t("col_status", lang),
                            help=t("status_column_help", lang),
                            width="medium",
                            options=options_status,
                            required=True
                        ),
                        'Prioridad': st.column_config.TextColumn(
                            t("col_priority", lang),
                            width="medium",
                            disabled=True
                        ),
                        'Tipo': st.column_config.TextColumn(
                            t("col_type", lang),
                            width="medium",
                            disabled=True
                        ),
                        'Fecha Límite': st.column_config.TextColumn(
                            t("col_deadline", lang),
                            width="medium",
                            disabled=True
                        ),
                        'Remitente': st.column_config.TextColumn(
                            t("col_sender", lang),
                            width="medium",
                            disabled=True
                        ),
                        'Asunto': st.column_config.TextColumn(
                            t("col_subject", lang),
                            width="large",
                            disabled=True
                        ),
                        'Tareas Extraídas': st.column_config.TextColumn(
                            t("col_extracted_tasks", lang),
                            width="large",
                            disabled=True
                        )
                    },
                    key="actions_editor_final",
                    height=500
                )
                
                changes_detected = False
                newly_selected_idx = None
                
                for idx, row in edited_data.iterrows():
                    task_id = f"{actions_view.iloc[idx]['sender']}_{actions_view.iloc[idx]['subject']}_{actions_view.iloc[idx]['date']}"
                    
                    # DETECTAR CAMBIOS EN EL ESTADO
                    new_estado = row['Estado']
                    old_estado = st.session_state.task_states.get(task_id, t("status_pending", lang))
                    
                    if new_estado != old_estado:
                        changes_detected = True
                        st.session_state.task_states[task_id] = new_estado
                        
                        if new_estado == t("status_done", lang):
                            st.session_state.completed_tasks.add(task_id)
                            st.session_state.in_progress_tasks.discard(task_id)
                        elif new_estado == t("status_progress", lang):
                            st.session_state.in_progress_tasks.add(task_id)
                            st.session_state.completed_tasks.discard(task_id)
                        else:  # Pendiente
                            st.session_state.completed_tasks.discard(task_id)
                            st.session_state.in_progress_tasks.discard(task_id)
                    
                    # DETECTAR SELECCIÓN 
                    if row['✓'] == True:
                        if st.session_state.selected_row_index != idx:
                            newly_selected_idx = idx
                
                if newly_selected_idx is not None:
                    st.session_state.selected_row_index = newly_selected_idx
                    changes_detected = True
                
                if st.session_state.selected_row_index is not None:
                    if st.session_state.selected_row_index < len(edited_data):
                        current_check = edited_data.iloc[st.session_state.selected_row_index]['✓']
                        if not current_check:
                            st.session_state.selected_row_index = None
                            changes_detected = True
                    else:
                        st.session_state.selected_row_index = None
                        changes_detected = True
                
                if st.session_state.selected_row_index is not None and not changes_detected:
                    idx = st.session_state.selected_row_index
                    
                    if idx < len(actions_view):
                        full_email = actions_view.iloc[idx]
                        
                        unique_str = f"{full_email['sender']}_{full_email['subject']}_{full_email['date']}_{idx}"
                        popup_key = hashlib.md5(unique_str.encode()).hexdigest()[:8]
                        
                        show_email_popup(full_email, lang, popup_key)
                
                if changes_detected:
                    st.rerun()
                
                st.markdown("---")
                
                # SECCIÓN DE PROGRESO
                st.markdown(f"### 📊 {t('progress_title', lang)}")
                
                total_tasks = len(actions_view)
                completed = len(st.session_state.completed_tasks)
                in_progress = len(st.session_state.in_progress_tasks)
                
                completed = min(completed, total_tasks)
                progress_pct = completed / total_tasks if total_tasks > 0 else 0.0
                progress_pct = max(0.0, min(progress_pct, 1.0))
                
                st.markdown(f"""
                <style>
                [data-testid="stProgress"] > div > div > div {{
                    background-color: {SANDOZ_BLUE};
                }}
                </style>
                """, unsafe_allow_html=True)
                
                st.progress(progress_pct)
                
                col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4)
                
                with col_metric1:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #48668E 0%, #001841 100%); 
                                padding: 15px; 
                                border-radius: 8px; 
                                text-align: center;
                                box-shadow: 0 2px 6px rgba(0,0,0,0.1);">
                        <p style="color: white; margin: 0; font-size: 12px; opacity: 0.9;">{t('metric_completed', lang)}</p>
                        <p style="color: white; margin: 5px 0 0 0; font-size: 24px; font-weight: 700;">{completed}/{total_tasks}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_metric2:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #A8D5FF 0%, #48668E 100%); 
                                padding: 15px; 
                                border-radius: 8px; 
                                text-align: center;
                                box-shadow: 0 2px 6px rgba(0,0,0,0.1);">
                        <p style="color: #001841; margin: 0; font-size: 12px; opacity: 0.9;">{t('metric_progress', lang)}</p>
                        <p style="color: #001841; margin: 5px 0 0 0; font-size: 24px; font-weight: 700;">{in_progress}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_metric3:
                    pending = total_tasks - completed - in_progress
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #E6F1F8 0%, #A8D5FF 100%); 
                                padding: 15px; 
                                border-radius: 8px; 
                                text-align: center;
                                box-shadow: 0 2px 6px rgba(0,0,0,0.1);">
                        <p style="color: #001841; margin: 0; font-size: 12px; opacity: 0.9;">{t('metric_pending', lang)}</p>
                        <p style="color: #001841; margin: 5px 0 0 0; font-size: 24px; font-weight: 700;">{pending}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_metric4:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #001841 0%, #48668E 100%); 
                                padding: 15px; 
                                border-radius: 8px; 
                                text-align: center;
                                box-shadow: 0 2px 6px rgba(0,0,0,0.1);">
                        <p style="color: white; margin: 0; font-size: 12px; opacity: 0.9;">{t('metric_total_prog', lang)}</p>
                        <p style="color: white; margin: 5px 0 0 0; font-size: 24px; font-weight: 700;">{progress_pct*100:.0f}%</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            else:
                st.info(t("no_pending_actions", lang))
                
        # =========================================================
        # PESTAÑA 2: CALENDARIO
        # =========================================================
        with tab2:
            st.subheader(t("calendar_title", lang))
            st.caption(t("calendar_caption", lang))
            
            # Filtrar emails con deadline
            df_con_fecha = df_res[df_res['deadline'].notna()].copy()
            
            if df_con_fecha.empty:
                st.info(t("no_deadlines", lang))
            else:
                today = date.today()
                
                eventos = []
                
                for idx, fila in df_con_fecha.iterrows():
                    task_id = f"{fila['sender']}_{fila['subject']}_{fila['date']}"
                    
                    es_hecha = task_id in st.session_state.get('completed_tasks', set())
                    
                    priority_val = str(fila.get('priority', 'Low'))
                    
                    try:
                        event_date = pd.to_datetime(fila['deadline']).date()
                        es_pasado = event_date < today
                    except:
                        es_pasado = False
                        event_date = None

                    urgency_val = str(fila.get('urgency', 'Low'))

                    if es_hecha:
                        evt_color = "#9E9E9E" 
                        icon_prefix = "✅ "
                        text_color = "#FFFFFF"
                        status_text = "(Hecha)" if lang == "es" else "(Done)"
                    elif es_pasado:
                        evt_color = "#D3D3D3" 
                        icon_prefix = "⚠️ "
                        text_color = "#888888"
                        status_text = ""
                    else:
                        text_color = "white"
                        status_text = ""
                        

                        if urgency_val in ["Immediate", "Short-term"]:
                            evt_color = "#FF4B4B" 
                            icon_prefix = "🔴 "
                        elif urgency_val == "Medium-term":
                            evt_color = "#FFA500"  
                            icon_prefix = "🟠 "
                        else:
                            evt_color = "#28a745"  
                            icon_prefix = "🟢 "

                    eventos.append({
                        "title": f"{icon_prefix}{fila['sender']} {status_text}",
                        "start": str(fila['deadline']),
                        "color": evt_color,
                        "textColor": text_color,
                        "extendedProps": {
                            "sender": fila['sender'],
                            "subject": fila['subject'],
                            "summary": fila['summary'],
                            "priority": priority_val,
                            "date": fila['date'],
                            "tasks": fila.get('tasks', []),
                            "es_pasado": es_pasado,
                            "es_hecha": es_hecha 
                        }
                    })
                
                st.write(t("calendar_found_events", lang, count=len(eventos)))
                
                st.caption(t("calendar_legend", lang))

                calendar_options = {
                    "initialView": "dayGridMonth",
                    "headerToolbar": {
                        "left": "prev,next today",
                        "center": "title",
                        "right": "dayGridMonth,listMonth"
                    },
                    "selectable": True,
                    "editable": False,
                    "height": 650
                }
                

                dynamic_key = f"calendar_main_{len(st.session_state.get('completed_tasks', []))}_{len(st.session_state.get('in_progress_tasks', []))}"

                state = calendar(
                    events=eventos,
                    options=calendar_options,
                    key=dynamic_key 
                )
                
                # Manejo de clicks
                if state is not None and isinstance(state, dict):
                    if "eventClick" in state and state["eventClick"] is not None:
                        try:
                            event_info = state["eventClick"]["event"]
                            props = event_info.get("extendedProps", {})
                            
                            st.markdown("---")
                            
                            # CABECERA DINÁMICA 
                            header_text = t("event_details_header", lang)
                            if props.get("es_hecha"):
                                header_text += " ✅ (Hecha)" if lang == "es" else " ✅ (Done)"
                            
                            st.subheader(header_text)
                            
                            # AVISOS (HECHA O VENCIDA)
                            if props.get("es_hecha"):
                                st.success(t("event_completed_msg", lang))
                            
                            if props.get("es_pasado") and not props.get("es_hecha"):
                                st.warning(t("event_past_msg", lang))
                            
                            # DETALLES (COLUMNAS)
                            col1, col2 = st.columns([1, 3])
                            
                            with col1:
                                st.markdown(f"**{t('col_deadline', lang)}:**") 
                                st.markdown(f"**{t('modal_from', lang)}:**")   
                                st.markdown(f"**{t('modal_subject', lang)}:**") 
                            
                            with col2:
                                st.markdown(event_info.get("start", "N/A"))
                                st.markdown(props.get("sender", "N/A"))
                                st.markdown(props.get("subject", "N/A"))
                                
                            
                            st.markdown(f"**{t('col_summary', lang)}:**")
                            st.info(props.get("summary", "Sin información"))
                            
                            # Mostrar tareas
                            tasks = props.get("tasks", [])
                            if tasks and len(tasks) > 0:
                                st.markdown(f"**{t('extracted_actions', lang)}**")
                                for task in tasks:
                                    st.markdown(f"- {task}")
                            
                            # Botón ver detalles
                            if st.button(t("view_details", lang), key="view_full_email_cal"):
                                try:
                                    full_email = df_res[
                                        (df_res['sender'] == props.get("sender")) &
                                        (df_res['subject'] == props.get("subject")) &
                                        (df_res['date'] == props.get("date"))
                                    ].iloc[0]
                                    
                                    show_email_popup(full_email, lang)
                                except Exception as e:
                                    st.error(f"Error al cargar el email: {e}")
                        
                        except Exception as e:
                            st.error(f"Error visualizando detalles: {e}")
                   
        # =========================================================
        # PESTAÑA 3: BANDEJA PRIORIZADA 
        # =========================================================
        with tab3:
            st.subheader(t("prioritized_inbox", lang))
            
            prio_map = {
                "High": "Alta" if lang == "es" else "High",
                "Medium": "Media" if lang == "es" else "Medium",
                "Low": "Baja" if lang == "es" else "Low"
            }
            prio_reverse = {v: k for k, v in prio_map.items()}
        
            c1, c2, c3 = st.columns(3)
            
            prio_options = list(prio_map.values())
            defaults = [prio_map["High"], prio_map["Medium"]] 
            
            selected_prio_display = c1.multiselect(t("filter_priority", lang), prio_options, defaults)
            
            selected_prio_raw = [prio_reverse[x] for x in selected_prio_display]
        
            f_proj = c2.multiselect(t("filter_project", lang), df_res["project"].unique())
            f_send = c3.multiselect(t("filter_sender", lang), df_res["sender"].unique())
            
            df_v = df_res.copy()
            if selected_prio_raw: df_v = df_v[df_v["priority"].isin(selected_prio_raw)]
            if f_proj: df_v = df_v[df_v["project"].isin(f_proj)]
            if f_send: df_v = df_v[df_v["sender"].isin(f_send)]
            
            st.info(f"💡 {t('chart_click_instruction', lang)} {t('inbox_hint', lang)}")
        
            df_v['priority_display'] = df_v['priority'].map(prio_map).fillna(df_v['priority'])
        
            df_display = df_v[["priority_display", "date", "sender", "subject", "summary", "tasks"]].reset_index(drop=True)
            
            event_inbox = st.dataframe(
                df_display,
                use_container_width=True,
                selection_mode="single-row",
                on_select="rerun",
                key="inbox_table",
                column_config={
                    "index": None,
                    "priority_display": st.column_config.TextColumn(t("col_priority", lang), width="small"),
                    "date": st.column_config.TextColumn(t("col_date", lang), width="small"),
                    "sender": st.column_config.TextColumn(t("sender_column", lang), width="medium"),
                    "subject": st.column_config.TextColumn(t("subject_column", lang), width="medium"),
                    "tasks": st.column_config.ListColumn(t("col_actions", lang)),
                    "summary": st.column_config.TextColumn(t("col_summary", lang), width="large")
                },
                height=450
            )
            
            if len(event_inbox.selection.rows) > 0:
                idx_visual = event_inbox.selection.rows[0]
                row_visual = df_display.iloc[idx_visual]
                
                try:
                    full_row = df_res[
                        (df_res['subject'] == row_visual['subject']) & 
                        (df_res['date'] == row_visual['date']) &
                        (df_res['sender'] == row_visual['sender'])
                    ].iloc[0]
                    

                    unique_str = f"tab3_{full_row['sender']}_{full_row['subject']}_{full_row['date']}_{idx_visual}"
                    popup_key = hashlib.md5(unique_str.encode()).hexdigest()[:8]

                    show_email_popup(full_row, lang, popup_key)
                    
                except Exception as e:
                    st.error(f"Error: {e}")
                    
        # =========================================================
        # PESTAÑA 4: CUADRO DE MANDO
        # =========================================================
        with tab4:
            st.subheader(t("interactive_dashboard", lang))
            
            fig_senders, fig_prio, fig_type, fig_proj = generate_interactive_plotly(df_res, lang)

            st.markdown("""
            <style>
            .label-lateral {
                display: flex;
                align-items: center;
                justify-content: center;
                height: 320px;
                font-size: 14px;
                font-weight: bold;
                color: #001841;
                background-color: #f8f9fa;
                border-radius: 10px;
                writing-mode: vertical-rl;
                transform: rotate(180deg);
                text-align: center;
                margin-top: 10px;
                }
            </style>
            """, unsafe_allow_html=True)

            # FILA 1
            c1, g1, c2, g2 = st.columns([0.5, 2, 0.5, 2])
            with c1: 
                st.markdown(f'<div class="label-lateral">{t("chart_emails_by_sender", lang)}</div>', unsafe_allow_html=True)
            with g1: 
                ev_sender = st.plotly_chart(fig_senders, use_container_width=True, on_select="rerun", key="chart_s")
            
            with c2: 
                st.markdown(f'<div class="label-lateral">{t("chart_emails_by_priority_label", lang)}</div>', unsafe_allow_html=True)
            with g2: 
                ev_prio = st.plotly_chart(fig_prio, use_container_width=True, on_select="rerun", key="chart_p")

            # FILA 2
            c3, g3, c4, g4 = st.columns([0.7, 2, 0.7, 2])
            with c3: 
                st.markdown(f'<div class="label-lateral">{t("chart_emails_by_intention", lang)}</div>', unsafe_allow_html=True)
            with g3: 
                ev_type = st.plotly_chart(fig_type, use_container_width=True, on_select="rerun", key="chart_t")
            
            with c4: 
                st.markdown(f'<div class="label-lateral">{t("chart_emails_by_project", lang)}</div>', unsafe_allow_html=True)
            with g4: 
                ev_proj = st.plotly_chart(fig_proj, use_container_width=True, on_select="rerun", key="chart_prj")

            st.markdown("---")
            
            # LÓGICA DE FILTRADO 
            df_filtered = df_res.copy()
            titulo_tabla = t("chart_all_emails", lang)

            if ev_sender.selection.points:
                val = ev_sender.selection.points[0]['y']
                df_filtered = df_res[df_res['sender'] == val]
                titulo_tabla = f"📂 Emails de: {val}"
            
            elif ev_prio.selection.points:
                try:
                    val = ev_prio.selection.points[0]['label']
                except:
                    val = ev_prio.selection.points[0].get('label', 'N/A')
                df_filtered = df_res[df_res['priority'] == val]
                titulo_tabla = f"📂 Prioridad: {val}"

            elif ev_type.selection.points:
                val = ev_type.selection.points[0]['y']
                df_filtered = df_res[df_res['email_type'] == val]
                titulo_tabla = f"📂 Tipo: {val}"

            elif ev_proj.selection.points:
                val = ev_proj.selection.points[0]['y']
                df_filtered = df_res[df_res['project'] == val]
                titulo_tabla = f"📂 Proyecto: {val}"

            st.subheader(titulo_tabla)
            
            # PREPARACIÓN DE LA TABLA INTERACTIVA 
            cols_order = ["sender", "subject", "priority", "project", "email_type", "date"]
            
            df_display_tab4 = df_filtered[cols_order].reset_index(drop=True)
            df_display_tab4['date'] = pd.to_datetime(df_display_tab4['date'], errors='coerce')

            event_tab4 = st.dataframe(
                df_display_tab4,
                use_container_width=True,
                selection_mode="single-row",
                on_select="rerun",
                key="table_charts_interactive",
                hide_index=True,
                column_config={
                    "sender": st.column_config.TextColumn(
                        t("sender_column", lang), 
                        width="medium"
                    ),
                    "subject": st.column_config.TextColumn(
                        t("subject_column", lang), 
                        width="medium"
                    ),
                    "priority": st.column_config.TextColumn(
                        t("col_priority", lang), 
                        width="small"
                    ),
                    "project": st.column_config.TextColumn(
                        t("filter_project", lang), 
                        width="small"
                    ),
                    "email_type": st.column_config.TextColumn(
                        t("col_type", lang), 
                        width="small"
                    ),
                    # FECHA AL FINAL
                    "date": st.column_config.DatetimeColumn(
                        t("col_date", lang),
                        format="D MMM YYYY, HH:mm",
                        width="medium"
                    ),
                }
            )

            if len(event_tab4.selection.rows) > 0:
                idx_visual = event_tab4.selection.rows[0]
                row_visual = df_display_tab4.iloc[idx_visual]
                
                try:
                    full_row = df_res[
                        (df_res['subject'] == row_visual['subject']) & 
                        (df_res['sender'] == row_visual['sender'])
                    ].iloc[0]
                    
                    unique_str = f"tab4_{full_row['sender']}_{full_row['subject']}_{idx_visual}"
                    popup_key = hashlib.md5(unique_str.encode()).hexdigest()[:8]
                    
                    show_email_popup(full_row, lang, popup_key)
                    
                except Exception as e:
                    pass
                    
        # =========================================================
        # PESTAÑA 5: CHAT CON IA
        # =========================================================
        with tab5:
            st.subheader(t("chat_title", lang))
            
            clippo_img = "🤖"
            user_img = "👤" 
            
            chat_container = st.container(height=400)
            with chat_container:
                for m in st.session_state.messages:
                    avatar_actual = clippo_img if m["role"] == "assistant" else user_img
                    with st.chat_message(m["role"], avatar=avatar_actual):
                        st.write(m["content"])
            
            if p := st.chat_input(t("chat_placeholder", lang)):
                st.session_state.messages.append({"role": "user", "content": p})
                
                with chat_container:
                    with st.chat_message("user", avatar=user_img):
                        st.write(p)
                
                with st.spinner(t("chat_analyzing", lang)):
                    ctx = df_res[["sender", "subject", "summary", "priority"]].to_string()
                    try:
                        r = client.chat.completions.create(
                            model=MODEL, 
                            messages=[
                                {"role": "system", "content": t("chat_system_prompt", lang)},
                                {"role": "user", "content": f"DATOS:\n{ctx}\n\nPREGUNTA: {p}"}
                            ]
                        )
                        ans = r.choices[0].message.content
                        st.session_state.messages.append({"role": "assistant", "content": ans})
                        
                        with chat_container:
                            with st.chat_message("assistant", avatar=clippo_img):
                                st.write(ans)
                        st.rerun() 
                    except Exception as e: 
                        st.error(f"Error: {e}")

if __name__ == "__main__":
    main()

