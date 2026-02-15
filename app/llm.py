"""
LLM Module - OpenAI Integration
================================
Handles all interactions with OpenAI API including:
- Email classification and analysis
- Task extraction
- Executive summaries
"""

import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, date
import pandas as pd
from openai import OpenAI
import streamlit as st
import os

from config import MODEL, LLM_BODY_CHARS
from email_processing import safe_extract_json, identify_user_role
from priority_engine import calculate_priority_score, map_to_priority


# ============================================================================
# OPENAI CLIENT SETUP
# ============================================================================

@st.cache_resource
def get_openai_client():
    api_key = st.secrets["OPENAI_API_KEY"]
    return OpenAI(api_key=api_key)

# ============================================================================
# ADVANCED EMAIL ANALYSIS
# ============================================================================

def llm_email_analysis_enhanced(
    client: OpenAI, 
    subject: str, 
    sender: str, 
    body: str, 
    recipient_count: int, 
    importance: str, 
    user_config: dict, 
    user_name_input: str, 
    received_date_context: str = "", 
    lang: str = "es", 
    is_phishing: bool = False, 
    is_spam: bool = False
) -> Dict[str, Any]:
    """
    Comprehensive LLM-based email analysis with user context.
    
    Args:
        client: OpenAI client
        subject: Email subject
        sender: Sender name/address
        body: Email body
        recipient_count: Number of recipients
        importance: Email importance flag
        user_config: User preferences dict
        user_name_input: Name of the user
        received_date_context: Email received date
        lang: Language code (es/en)
        is_phishing: Security flag
        is_spam: Security flag
        
    Returns:
        Dict with priority, score, summary, tasks, etc.
    """
    # 1. User priority instruction
    custom_instruction = user_config.get("priority_instruction", "").strip()
    
    instruction_block = ""
    if custom_instruction:
        instruction_block = f"""
    2. USER PRIORITY INSTRUCTION (SECONDARY RULES):
    Only applies if Step 1 did not already trigger a "High" priority match.
    The user has provided a specific rule: "{custom_instruction}"
    
    EVALUATION TASK:
    1. Does the content match the user's rule?
    2. IF IT MATCHES:
       - Set "forced_priority": "High" (if instruction implies high/urgent)
       - Set "forced_priority": "Low" (if instruction implies low/ignore)
       - Set "forced_priority": "Medium" (if instruction implies medium)
    3. IF IT DOES NOT MATCH:
       - Leave "forced_priority" as null.
    """
        
    context_str = f"Recipients: {recipient_count}"
    if importance: 
        context_str += f", Importance: {importance}"
    if received_date_context: 
        context_str += f", EMAIL_RECEIVED_DATE: {received_date_context} (CRITICAL: Use this date as reference for 'tomorrow', 'next week')"
    
    context_hint = ""
    if any(kw in subject.lower() for kw in [
        "action needed", "approval", "endorsement", "review required"
    ]):
        context_hint = "\n⚠️ CRITICAL: The subject line indicates this requires APPROVAL/ACTION. Classify as Approval_Request or Action_Request accordingly."

    # Identify user role
    user_role = identify_user_role(
        user_name=user_name_input,
        from_name=sender.split('<')[0].strip() if '<' in sender else sender,
        from_addr=sender.split('<')[1].replace('>', '').strip() if '<' in sender else sender,
        to_field=str(user_config.get('to_field', '')),  
        cc_field=str(user_config.get('cc_field', ''))
    )
    
    # Build role context
    role_context = ""
    if user_role["is_sender"]:
        role_context = f"\n⚠️ CRITICAL: {user_name_input} is the SENDER of this email. Do NOT assign tasks to them unless they explicitly assign themselves a follow-up action."
    elif user_role["is_cc"]:
        role_context = f"\n⚠️ CRITICAL: {user_name_input} is in CC (copy). Only assign tasks if they are EXPLICITLY mentioned by name in the body (e.g., '@{user_name_input}', 'Dear {user_name_input}', '{user_name_input}, please...')."
    elif user_role["is_primary_recipient"]:
        role_context = f"\n✅ {user_name_input} is a primary recipient (To). Analyze if actions are directed to them."
    else:
        role_context = f"\n⚠️ {user_name_input} does not appear in To/CC/From. Verify carefully if tasks apply to them."
        
    # Body limit (longer for training emails)
    body_limit = LLM_BODY_CHARS
    if "csod.com" in sender.lower() or "training" in subject.lower(): 
        body_limit = 6000

    target_lang = "Spanish" if lang == "es" else "English"

    # Examples based on language
    if lang == "es":
        ex_spec = '"Revisar los indicadores de calidad y confirmar cambios"'
        ex_who = '"Responder a Isabel sobre el proyecto"'
        ex_quest = '"1. Explicar por qué es urgente"'
        ex_coord = '["Revisar los indicadores"]'
        lang_note = "Even if the email is in English, TRANSLATE the tasks to Spanish."
    else:
        ex_spec = '"Review data quality indicators and confirm changes"'
        ex_who = '"Reply to Isabel regarding the project"'
        ex_quest = '"1. Explain why this is urgent"'
        ex_coord = '["Review the indicators"]'
        lang_note = "Even if the email is in Spanish, TRANSLATE the tasks to English."
    
    # FULL PROMPT
    prompt = f"""You are an intelligent email classification system for {user_name_input}, a busy professional returning from vacation.
{context_hint}
{role_context}

PRIORITY DETERMINATION LOGIC
{instruction_block}
If this doesn't resulted in a forced priority, determine priority based on content urgency and business impact 

CRITICAL LANGUAGE INSTRUCTION:
- OUTPUT LANGUAGE: {target_lang}
- The fields 'summary' and 'actions' MUST be written in {target_lang}.
- {lang_note}

==============================================================================
CRITICAL RULES FOR IDENTIFYING {user_name_input}:
==============================================================================

0. USER IDENTIFICATION:
   You are analyzing emails FOR: {user_name_input}
   
   NAME VARIATIONS TO RECOGNIZE (all refer to the same person):
   {', '.join(user_role.get('user_variations', [user_name_input]))}
   
   FLEXIBLE MATCHING RULES:
   - Match ANY of these variations (e.g., "John" even if full name is "Doe, John")
   - Case-insensitive matching
   - If a task is assigned to someone else, it is NOT a task for {user_name_input}

==============================================================================
TASK ASSIGNMENT DETECTION (CRITICAL):
==============================================================================

1. DIRECT ASSIGNMENT PATTERNS (Extract as tasks):
   - "[Name], [verb]" → "John, please review the report"
   - "@[Name]" → "@John can you check this?"
   - "Dear [Name]" → "Dear John, we need..."
   - "[Name], ¿podrías...?" → "John, ¿podrías revisar...?"
   - "[Name], could you...?" → "John, could you update...?"
   - "[Name], necesitamos que..." → "John, necesitamos que confirmes..."
   - "[Name], can you...?" → "John, can you handle...?"
   - "[Name] - [task]" → "John - please confirm by EOD"

2. INDIRECT ASSIGNMENT PATTERNS (Extract as tasks):
   - "[Name] debe/should [action]" → "John debe revisar los indicadores"
   - "Necesitamos que [Name] [action]" → "Necesitamos que John actualice las métricas"
   - "We need [Name] to [action]" → "We need John to confirm the data"
   - "[Name] puede encargarse de..." → "John puede encargarse del resumen"

3. CC-ONLY DETECTION RULES:
   - If {user_name_input} is in CC but NOT explicitly mentioned by name in the body:
     → action_level = "None"
     → tasks = []
     → email_type = "FYI_Informational"
   
   - If {user_name_input} is in CC AND explicitly mentioned (patterns above):
     → Extract tasks normally
     → Classify based on content

4. MULTIPLE RECIPIENTS:
   - If tasks are distributed to DIFFERENT people (e.g., "John, review X. Maria, update Y."):
     → Extract ONLY tasks assigned to {user_name_input}
     → Do NOT include tasks for others

==============================================================================
EMAIL CLASSIFICATION:
==============================================================================

1. EMAIL_TYPE (choose ONE):
   - Approval_Request: Someone needs your explicit approval/sign-off
   - Decision_Required: You must make a decision or provide judgment
   - Action_Request: Someone needs you to DO something specific
   - Meeting: Meeting invite, update, cancellation, or confirmation
   - Report_Update: Status update, report, metrics, or progress
   - FYI_Informational: Information only, no action needed
   - Notification_System: Automated system notification (calendar, SharePoint, etc.)
   - External_Request: Request from external party/client/vendor

2. ACTION_LEVEL (choose ONE):
   - Mandatory: You MUST execute a task (e.g., "submit report", "complete form", "approve budget", "could you do...", "please...")
   - Optional: Action is suggested but not mandatory
   - None: No task needed from you

3. DECISION_LEVEL (choose ONE):
   - Required: Must decide
   - Optional: Input requested but not mandatory
   - None: No decision

4. SUMMARY: 2 sentences. What is happening + What is expected from {user_name_input}.
   VALIDATION RULES FOR SUMMARY:
   - MUST be 20-60 words total
   - MUST NOT repeat the subject line
   - MUST describe actual content, not just echo the title
   - MUST be written in YOUR OWN WORDS
   - Example BAD: "RE: Future of APO" (this is just the subject!)
   - Example GOOD: "Matt is asking if you know any contacts for SAP IBP implementation. He wants to assess the impact on the SANITY/APO system."

5. ACTIONS: List specific tasks assigned to {user_name_input}. Empty if none.
   
   STRICT VALIDATION RULES FOR ACTIONS:

   **ALWAYS INCLUDE ACTIONS FOR:**
   - Approval_Request → ["Approve or reject [specific item]"]
   - Decision_Required → ["Decide on [specific question]"]
   - Action_Request (Mandatory) → List ALL specific tasks mentioned for {user_name_input}
   - Email with numbered questions (1, 2, 3) → List each question as separate task
   - External_Request → ["Respond to [what is being requested]"]
   
   **USE EMPTY ARRAY [] ONLY FOR:**
   - FYI_Informational with action_level=None
   - Report_Update with action_level=None  
   - Notification_System (automated notifications)
   - Thread closures ("Thanks", "Got it", "No action needed")
   - CC emails where {user_name_input} is NOT explicitly mentioned
   
    **FORMAT RULES:**
   - MUST BE IN {target_lang}
   - Be specific: {ex_spec}  
   - Include WHO asked: {ex_who}   
   - Extract questions: {ex_quest}  
   - Avoid vague: "Review the email"
   
   **COORDINATION EMAILS (CRITICAL):**
   When an email distributes tasks to multiple people:
   - ONLY extract tasks explicitly assigned to {user_name_input}
   - Ignore tasks assigned to others
   - Example: "John, review indicators. Maria, update metrics." 
     -> For John: {ex_coord}  

6. DEADLINE: Extract exact date in YYYY-MM-DD format, or null if none mentioned.
   - SCOPE: Include both TASK DUE DATES and MEETING/EVENT DATES.
   - IF EMAIL IS A MEETING INVITE/UPDATE: The "deadline" is the date of the meeting.
   - REFERENCE DATE: {received_date_context if received_date_context else 'Unknown'}
   - CRITICAL: "Tomorrow" means {received_date_context} + 1 day.
   - "Next week" means the week following {received_date_context}.

7. URGENCY:
   - CALCULATE RELATIVE TO THE EMAIL DATE ({received_date_context}), NOT TODAY'S REAL DATE.
   - Immediate: The task deadline is within 24-48 hours of {received_date_context}.
   - Short-term: Within the same week as {received_date_context}.
   - Medium-term: 1-2 weeks after {received_date_context}.
   - Low: No clear deadline or > 2 weeks after {received_date_context}.

8. PROJECT: Name of specific project/initiative mentioned. 
   - If matches WATCHLIST → Use that name.
   - If NOT in WATCHLIST but a project is discussed → Extract the project name anyway.
   - If no project → "None"

9. BLOCKS_OTHERS: true if email explicitly states someone is waiting/blocked
   Examples: "Alejandra is waiting", "audit tomorrow", "team needs this"

10. DECISION_PENDING: true if a decision is explicitly waiting on someone

==============================================================================
CONTEXT:
==============================================================================
{context_str}
FROM: {sender}
SUBJECT: {subject}
CONTENT (CURRENT MESSAGE ONLY): {body[:body_limit]}

==============================================================================
RESPONSE FORMAT:
==============================================================================
Respond ONLY with valid JSON (no markdown):
{{
  "forced_priority": "High" | "Medium" | "Low" | null,
  "email_type": "...",
  "action_level": "...",
  "decision_level": "...",
  "summary": "...",
  "actions": ["task1", "task2"],
  "deadline": "YYYY-MM-DD" or null,
  "urgency": "...",
  "project": "...",
  "blocks_others": true/false,
  "decision_pending": true/false
}}"""

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are an expert email classifier. Respond ONLY with valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=800,
        )
        
        raw_resp = resp.choices[0].message.content.strip()
        data = safe_extract_json(raw_resp)
        
        # SUMMARY VALIDATION
        summary = str(data.get("summary", "")).strip()
        if not summary or summary == subject or len(summary) < 30:
            body_preview = body[:300].replace("\n", " ").strip()
            summary = f"Email from {sender.split()[0]} regarding {subject[:60]}. {body_preview[:150]}"
        
        if ("training" in subject.lower() or "csod" in sender.lower()) and data.get("deadline"):
            if str(data["deadline"]) not in summary:
                summary += f" Deadline: {data['deadline']}."
        
        # TASKS VALIDATION
        forbidden_tasks = ["stay informed", "monitor", "be aware", "keep in mind", "take action"]
        tasks = [t for t in data.get("actions", []) if not any(f in t.lower() for f in forbidden_tasks)]
        
        if not tasks:
            if data.get("action_level") == "Mandatory": 
                tasks = ["Complete required action"]
            elif data.get("decision_level") == "Required": 
                tasks = ["Provide decision"]

        score = calculate_priority_score(data, importance, subject)
        
        # Get forced priority
        forced_prio = data.get("forced_priority")

        # VIP projects logic
        detected_project = str(data.get("project", "")).strip()
        vip_projects_list = user_config.get("priority_projects", [])
        
        if detected_project and detected_project.lower() != "none":
            for vip_proj in vip_projects_list:
                vip_clean = vip_proj.lower().strip()
                detected_clean = detected_project.lower().strip()
                if vip_clean and (vip_clean in detected_clean or detected_clean in vip_clean):
                    forced_prio = "High"
                    break
        
        # Final priority mapping
        priority = map_to_priority(
            sender=sender, 
            subject=subject, 
            body=body,
            email_type=data.get("email_type", "FYI_Informational"),
            action_level=data.get("action_level", "None"),
            decision_level=data.get("decision_level", "None"),
            urgency=data.get("urgency", "Low"),
            blocks_others=data.get("blocks_others", False),
            score=score, 
            importance=importance, 
            user_config=user_config,
            forced_priority=forced_prio,
            is_phishing=is_phishing,
            is_spam=is_spam
        )
        
        return {
            "priority": priority, 
            "score": score, 
            "summary": summary[:300],
            "tasks": tasks, 
            "context": str(data.get("project", "")).strip()[:150],
            "requires_action": data.get("action_level") in ["Mandatory", "Optional"],
            "email_type": data.get("email_type", "FYI_Informational"),
            "action_level": data.get("action_level", "None"),
            "decision_level": data.get("decision_level", "None"),
            "deadline": data.get("deadline"),
            "urgency": data.get("urgency", "Low"),
            "project": data.get("project", "None"),
            "blocks_others": data.get("blocks_others", False),
            "decision_pending": data.get("decision_pending", False),
            "forced_priority": forced_prio
        }
        
    except Exception as e:
        print(f"❌ Error in LLM analysis: {e}")
        return {
            "priority": "Medium", 
            "score": 50, 
            "summary": f"{sender.split()[0]} sent: {subject[:100]}", 
            "tasks": [],
            "email_type": "FYI_Informational", 
            "action_level": "None", 
            "deadline": None, 
            "urgency": "Low", 
            "project": "None",
            "blocks_others": False, 
            "decision_pending": False, 
            "requires_action": False, 
            "forced_priority": None
        }


# ============================================================================
# EXECUTIVE SUMMARY GENERATION
# ============================================================================

def llm_overall_summary(
    client, 
    high_priority_emails, 
    total_emails, 
    range_text, 
    lang="es"
):
    """
    Generate executive summary of high priority emails.
    
    Args:
        client: OpenAI client
        high_priority_emails: List of high priority email dicts
        total_emails: Total number of emails analyzed
        range_text: Date range description
        lang: Language code (es/en)
        
    Returns:
        Executive summary text
    """
    if not high_priority_emails: 
        return "ℹ️ No hay correos de alta prioridad para resumir." if lang == "es" else "ℹ️ No high priority emails found to summarize."

    today_str = datetime.now().strftime("%Y-%m-%d")
    
    context_text = ""
    for i, email in enumerate(high_priority_emails[:10]):
        context_text += f"Email {i+1} from {email.get('sender', 'Unknown')}:\n - Subject: {email.get('subject', 'No Subject')}\n - Critical Details: {email.get('summary', 'No content')}\n"
        if email.get('deadline'): 
            context_text += f" - Deadline: {email.get('deadline')}\n"
        context_text += "\n"

    target_language = "Spanish" if lang == "es" else "English"

    prompt = f"""Act as an expert Executive Assistant. Analyze the following HIGH PRIORITY emails received during an absence ({range_text}):
CONTEXT DATA:
    - TODAY'S DATE IS: {today_str}
    - EMAILS TO ANALYZE:
    {context_text}
    
    INSTRUCTIONS:
    1. Write a **Bullet-point Executive Summary** in {target_language}.
    2. MAX LENGTH: 250 words total. Be concise. Do not enter "Email Nº...:"
    3. STRUCTURE:
        - 🚨 **Critical Blockers/Urgent:** Top 2-3 items requiring immediate attention today.
        - 📅 **Key Deadlines:** Mention deadlines.
        - 👤 **Other high-priority emails:** Any direct request from VIPs not covered above.
    4. CRITICAL RULE FOR DATES:
        - NEVER use relative terms like "Mañana", "Tomorrow", "Today", "Yesterday", "Next week", "Este martes".
        - ALWAYS use ABSOLUTE DATES (e.g., "25 Oct", "10 Nov", "Lunes 12").
    5. CRITICAL RULE FOR PAST DEADLINES (FILTERING):
        - Compare every deadline against TODAY'S DATE ({today_str}).
        - IF A DEADLINE IS IN THE PAST (older than today), DO NOT INCLUDE IT in the "Key Deadlines" section.
        - Only mention a past item if it is a critical blocker that requires an apology or immediate recovery. Otherwise, ignore it.
    6. STYLE: Direct, action-oriented, no fluff.
    7. IMPORTANT: The output MUST be in {target_language}.
    8. Start with a natural phrase like "During the period..." (translated to {target_language})."""
    
    try:
        resp = client.chat.completions.create(
            model=MODEL, 
            messages=[
                {"role": "system", "content": f"You are an executive assistant. You speak {target_language}."}, 
                {"role": "user", "content": prompt}
            ], 
            temperature=0.3
        )
        return resp.choices[0].message.content
    except: 
        return "❌ No se pudo generar el resumen automático." if lang == "es" else "❌ Could not generate automatic summary."
