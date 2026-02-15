"""
Sistema de traducciones para Back2Work Bot
Soporta: Español (es) e Inglés (en)
"""

TRANSLATIONS = {
    "es": {
        # Títulos principales
        "page_title": "Back2Work Bot: Asistente de Retorno Vacacional",
        "page_subtitle": "Analiza tu bandeja de entrada post-vacaciones, prioriza lo importante y genera un plan de acción.",
        
        # Sidebar
        "sidebar_config": "⚙️ Configuración",
        "user_name_label": "Nombre del Usuario (Contexto)",
        "user_name_placeholder": "Ej: Rufi, Arlind",
        "user_name_help": "Formato: Apellido, Nombre. Ayuda a la IA a saber si eres el destinatario directo.",
        "upload_csv": "1. Cargar CSV de Emails",
        "vacation_period": "2. Periodo de Vacaciones",
        "analyze_all": "Analizar todo",
        "select_dates": "Seleccionar fechas",
        "date_range_label": "Rango de ausencia:",
        "priorities_section": "3. Tus Prioridades",
        "vip_senders": "Remitentes VIP",
        "vip_placeholder": "jefe@empresa.com, cliente_clave",
        "key_projects": "Proyectos Clave",
        "projects_placeholder": "Migración, Q4 Report",
        "search_label": "Búsqueda (frase o instrucción)",
        "search_placeholder": "Ej: filtra correos sobre venta del edificio",
        "start_analysis": "🚀 INICIAR ANÁLISIS",
        "date_warning": "⚠️ Por favor, selecciona fecha de inicio y fin.",
        
        # Mensajes de estado
        "upload_error": "⚠️ Sube un CSV.",
        "api_key_error": "⚠️ Falta API Key.",
        "processing": "⏳ Leyendo, filtrando y analizando con IA...",
        "no_emails": "❌ No hay emails en",
        "analysis_complete": "✅ Análisis completado. Se han analizado {count} correos.",
        
        # Pestañas
        "tab_summary": "📊 Resumen y Tareas",
        "tab_calendar": "📅 Calendario",
        "tab_inbox": "📥 Bandeja Priorizada",
        "tab_charts": "📈 Gráficas",
        "tab_chat": "💬 Chat IA",
        
        # Secciones
        "executive_summary": "📝 Resumen Ejecutivo",
        "calendar_title": "📅 Calendario de Vencimientos y Reuniones",
        "actions_required": "⚡ Acciones Requeridas",
        "ai_assistant": "💬 Asistente IA",
        "prioritized_inbox": "📋 Bandeja Priorizada",
        "interactive_dashboard": "📈 Cuadro de Mando Interactivo",
        
        # Columnas de tabla
        "date_column": "Fecha",
        "sender_column": "Remitente",
        "explanation_column": "Explicación",
        "priority_column": "Prioridad",
        "no_deadlines": "✅ No hay fechas de vencimiento ni reuniones detectadas.",
        
        # Acciones
        "action_type": "Tipo",
        "from_column": "De",
        "subject_column": "Asunto",
        "tasks_column": "Tareas Específicas (Detalle)",
        "actions_table_title": "⚡ Acciones Requeridas",
        "col_received": "Recibido",
        "col_deadline": "Fecha Límite",
        "deadline_help": "Fecha límite detectada automáticamente en el texto",
        "col_tasks_extracted": "Tareas Extraídas",
        "no_pending_actions": "🎉 ¡Genial! No se han detectado acciones pendientes explícitas.",
        "inbox_hint": "Selecciona una fila para ver el correo completo.",
        
        # Chat
        "chat_placeholder": "Pregunta sobre tus correos (Ej: ¿Qué me pide Marta?)...",
        "chat_processing": "Consultando...",
        "chat_welcome": "Hola, una vez analizados los correos, pregúntame lo que quieras.",
        "col_priority": "Prioridad",
        
        # Filtros
        "filter_priority": "Prioridad",
        "filter_project": "Proyecto",
        "filter_sender": "Remitente",
        
        # Gráficas
        "chart_click_instruction": "PULSA UNA BARRA PARA FILTRAR:",
        "chart_emails_by_priority": "Emails por Prioridad",
        "chart_filtered_by": "📂 Correos de: {sender}",
        "chart_deselect_hint": "ℹ️ Haz clic fuera de la barra o usa 'Deselect' en la gráfica para ver todos.",
        "chart_all_emails": "📋 Todos los correos analizados",
        
        # Columnas de tabla
        "col_date": "Fecha",
        "col_actions": "Acciones",
        "col_summary": "Resumen",
        "col_status": "Estado",
        "col_type": "Tipo",
        "col_sender": "Remitente",
        "col_subject": "Asunto",
        "col_extracted_tasks": "Tareas Extraídas",
        
        # Gráficos - etiquetas
        "chart_emails_by_sender": "Emails por Remitente",
        "chart_emails_by_priority_label": "Emails por Prioridad",
        "chart_emails_by_intention": "Emails por Intención",
        "chart_emails_by_project": "Emails por Proyecto",
        
        # Progreso
        "progress_title": "Progreso",
        "progress_completed": "Completados",
        "progress_in_progress": "En Progreso",
        "progress_pending": "Pendientes",
        "progress_percentage": "Progreso",
        
        # Calendario
        "calendar_caption": "Pulsa en un evento para ver los detalles del correo.",
        "event_details_header": "🔍 DETALLES DEL EVENTO SELECCIONADO",
        "extracted_actions": "Acciones extraídas:",
        "chat_title": "💬 Chat con tu Bandeja de Entrada",
        "chat_analyzing": "Analizando correos...",
        "chat_system_prompt": "Eres un asistente corporativo. Responde siempre en el idioma en el que se te pregunta.",
        
        # Ventana modal
        "view_details": "Ver detalles completos",
        "modal_title": "📧 Detalles del Correo",
        "modal_from": "De",
        "modal_to": "Para",
        "modal_cc": "CC",
        "modal_date": "Fecha",
        "modal_subject": "Asunto",
        "modal_body": "Cuerpo del Mensaje",
        "modal_close": "Cerrar",
        "modal_note": "Nota: El contenido del cuerpo se muestra tal cual se recibió (formato original).",
        
        # Fuente de datos
        "source_title": "1. Fuente de Datos",
        "source_select": "Seleccionar fuente:",
        "source_csv": "Cargar CSV",
        "source_gmail": "Conectar Gmail",
        "source_help": "Elige si cargar un archivo CSV exportado o conectar directamente a Gmail",
        "gmail_auth_info": "🔐 Se abrirá una ventana de autenticación de Google",
        "gmail_auth_btn": "🔗 Autenticar con Gmail",
        "gmail_authenticating": "Autenticando con Gmail...",
        "gmail_success": "✅ Conectado como: {email}",
        "gmail_id": "👤 Identificado como: {name}",
        "gmail_error": "❌ Error en la autenticación",
        "gmail_warning_auth": "⚠️ Debes autenticarte con Gmail primero",
        "auto_name_help": "✅ Nombre detectado automáticamente del email. Puedes editarlo.",
        
        # API KEY
        "api_key_header": "🔑 OpenAI API Key",
        "api_key_missing_info": "No se encontró una API Key configurada. Introdúcela manualmente:",
        "api_key_placeholder": "sk-...",
        "api_key_help": "Introduce tu OpenAI API Key. Se guardará solo durante esta sesión.",
        "api_key_success": "✅ API Key cargada correctamente",
        "api_key_load_error": "❌ Error al cargar la API Key: {error}",
        
        # Reglas de prioridad
        "priority_rules_label": "4. Reglas de Prioridad (Instrucciones)",
        "priority_rules_placeholder": "Ej: Los correos de Marisa son urgentes. El proyecto Zeta es prioridad baja.",
        "priority_rules_help": "Instrucciones en lenguaje natural para que la IA ajuste la prioridad.",
        
        # Errores y estados
        "no_emails_found": "❌ No se encontraron emails",
        "range_all": "Todo el periodo",
        "range_from_to": "del {start} al {end}",
        
        # Filtros y tablas
        "filters_title": "#### 🔍 Filtros",
        "filter_only_overdue": "⚠️ Solo vencidas",
        "showing_tasks": "📊 Mostrando {count} de {total} tareas",
        "table_caption": "💡 Marca **✓** para ver detalles. Usa la columna **Estado** para actualizar.",
        "table_caption_overdue": " Las fechas con **⚠️** indican evento vencido ({count}).",
        
        # Estados de tareas
        "status_pending": "📋 Pendiente",
        "status_progress": "🔵 En Progreso",
        "status_done": "✅ Hecho",
        "status_column_help": "Actualizar el estado de la tarea",
        "check_column_help": "Seleccionar para ver detalles",
        
        # Métricas
        "metric_completed": "Completadas",
        "metric_progress": "En Progreso",
        "metric_pending": "Pendientes",
        "metric_total_prog": "Progreso",
        
        # Calendario (pestaña 2)
        "calendar_found_events": "📊 Se encontraron **{count}** eventos con fecha límite",
        "calendar_legend": "🔴 Inmediato/Corto Plazo | 🟠 Medio Plazo | 🟢 Baja Urgencia | ⚪ Evento Pasado | ✅ Tarea Completada",
        "event_completed_msg": "Esta tarea ha sido marcada como completada.",
        "event_past_msg": "⚠️ Este evento venció antes de hoy.",
        
        # Botones Gmail
        "btn_open_thread": "📂 Abrir Hilo en Gmail",
        "help_open_thread": "Abre la conversación en la cuenta {email}.",
        "btn_reply_new": "↩️ Responder (Nuevo Borrador)",
        "help_reply_new": "No se encontró el hilo original. Se creará un borrador nuevo."
    },
    
    "en": {
        # Main titles
        "page_title": "Back2Work Bot: Vacation Return Assistant",
        "page_subtitle": "Analyze your post-vacation inbox, prioritize what matters and generate an action plan.",
        
        # Sidebar
        "sidebar_config": "⚙️ Configuration",
        "user_name_label": "User Name (Context)",
        "user_name_placeholder": "Ex: Doe, John",
        "user_name_help": "Format: Last Name, First Name. Helps AI know if you're the direct recipient.",
        "upload_csv": "1. Upload Email CSV",
        "vacation_period": "2. Vacation Period",
        "analyze_all": "Analyze all",
        "select_dates": "Select dates",
        "date_range_label": "Absence range:",
        "priorities_section": "3. Your Priorities",
        "vip_senders": "VIP Senders",
        "vip_placeholder": "boss@company.com, key_client",
        "key_projects": "Key Projects",
        "projects_placeholder": "Migration, Q4 Report",
        "search_label": "Search (phrase or instruction)",
        "search_placeholder": "Ex: filter emails about building sale",
        "start_analysis": "🚀 START ANALYSIS",
        "date_warning": "⚠️ Please select a start and end date.",
        
        # Status messages
        "upload_error": "⚠️ Upload a CSV file.",
        "api_key_error": "⚠️ API Key missing.",
        "processing": "⏳ Reading, filtering and analyzing with AI...",
        "no_emails": "❌ No emails found in",
        "analysis_complete": "✅ Analysis complete. {count} emails analyzed.",
        
        # Tabs
        "tab_summary": "📊 Summary & Tasks",
        "tab_calendar": "📅 Calendar",
        "tab_inbox": "📥 Prioritized Inbox",
        "tab_charts": "📈 Charts",
        "tab_chat": "💬 AI Chat",
        
        # Sections
        "executive_summary": "📝 Executive Summary",
        "calendar_title": "📅 Deadlines and Meetings Calendar",
        "actions_required": "⚡ Required Actions",
        "ai_assistant": "💬 AI Assistant",
        "prioritized_inbox": "📋 Prioritized Inbox",
        "interactive_dashboard": "📈 Interactive Dashboard",
        
        # Calendar table
        "date_column": "Date",
        "sender_column": "Sender",
        "explanation_column": "Explanation",
        "priority_column": "Priority",
        "no_deadlines": "✅ No deadlines or meetings detected.",
        
        # Actions
        "action_type": "Type",
        "from_column": "From",
        "subject_column": "Subject",
        "tasks_column": "Specific Tasks (Detail)",
        "actions_table_title": "⚡ Required Actions",
        "col_received": "Received",
        "col_deadline": "Deadline",
        "deadline_help": "Deadline automatically detected in text",
        "col_tasks_extracted": "Extracted Tasks",
        "no_pending_actions": "🎉 Great! No explicit pending actions detected.",
        "inbox_hint": "Select a row to view the full email.",
        
        # Chat
        "chat_placeholder": "Ask about your emails (Ex: What does Marta need?)...",
        "chat_processing": "Consulting...",
        "chat_welcome": "Hello, once the emails are analyzed, ask me anything.",
        
        # Filters
        "filter_priority": "Priority",
        "filter_project": "Project",
        "filter_sender": "Sender",
        
        # Charts
        "chart_click_instruction": "CLICK A BAR TO FILTER:",
        "chart_emails_by_priority": "Emails by Priority",
        "chart_filtered_by": "📂 Emails from: {sender}",
        "chart_deselect_hint": "ℹ️ Click outside the bar or use 'Deselect' on the chart to see all.",
        "chart_all_emails": "📋 All analyzed emails",
        "col_priority": "Priority",
        
        # Table columns
        "col_date": "Date",
        "col_actions": "Actions",
        "col_summary": "Summary",
        "col_status": "Status",
        "col_type": "Type",
        "col_sender": "Sender",
        "col_subject": "Subject",
        "col_extracted_tasks": "Extracted Tasks",
        
        # Charts - labels
        "chart_emails_by_sender": "Emails by Sender",
        "chart_emails_by_priority_label": "Emails by Priority",
        "chart_emails_by_intention": "Emails by Intention",
        "chart_emails_by_project": "Emails by Project",
        
        # Progress
        "progress_title": "Progress",
        "progress_completed": "Completed",
        "progress_in_progress": "In Progress",
        "progress_pending": "Pending",
        "progress_percentage": "Progress",
        
        # Calendar
        "calendar_caption": "Click on an event to see email details.",
        "event_details_header": "🔍 SELECTED EVENT DETAILS",
        "extracted_actions": "Extracted actions:",
        "chat_title": "💬 Chat with your Inbox",
        "chat_analyzing": "Analyzing emails...",
        "chat_system_prompt": "You are a corporate assistant. Always respond in the language of the question.",
        
        # Modal window
        "view_details": "View full details",
        "modal_title": "📧 Email Details",
        "modal_from": "From",
        "modal_to": "To",
        "modal_cc": "CC",
        "modal_date": "Date",
        "modal_subject": "Subject",
        "modal_body": "Message Body",
        "modal_close": "Close",
        "modal_note": "Note: Body content is shown exactly as received (original format).",
        
        # Data source
        "source_title": "1. Data Source",
        "source_select": "Select source:",
        "source_csv": "Upload CSV",
        "source_gmail": "Connect Gmail",
        "source_help": "Choose to upload an exported CSV or connect directly to Gmail",
        "gmail_auth_info": "🔐 A Google authentication window will open",
        "gmail_auth_btn": "🔗 Authenticate with Gmail",
        "gmail_authenticating": "Authenticating with Gmail...",
        "gmail_success": "✅ Connected as: {email}",
        "gmail_id": "👤 Identified as: {name}",
        "gmail_error": "❌ Authentication error",
        "gmail_warning_auth": "⚠️ You must authenticate with Gmail first",
        "auto_name_help": "✅ Name automatically detected from email. You can edit it.",
        
        # API KEY
        "api_key_header": "🔑 OpenAI API Key",
        "api_key_missing_info": "No configured API Key found. Enter it manually:",
        "api_key_placeholder": "sk-...",
        "api_key_help": "Enter your OpenAI API Key. It will be saved for this session only.",
        "api_key_success": "✅ API Key loaded successfully",
        "api_key_load_error": "❌ Error loading API Key: {error}",
        
        # Priority inputs
        "priority_rules_label": "4. Priority Rules (Instructions)",
        "priority_rules_placeholder": "Ex: Emails from Marisa are urgent. Project Zeta is low priority.",
        "priority_rules_help": "Natural language instructions for AI priority adjustment.",
        
        # Errors & status
        "no_emails_found": "❌ No emails found",
        "range_all": "The entire period",
        "range_from_to": "from {start} to {end}",
        
        # Filters & tables
        "filters_title": "#### 🔍 Filters",
        "filter_only_overdue": "⚠️ Overdue only",
        "showing_tasks": "📊 Showing {count} of {total} tasks",
        "table_caption": "💡 Check **✓** to view details. Use **Status** column to update.",
        "table_caption_overdue": " Dates with **⚠️** indicate overdue events ({count}).",
        
        # Task statuses
        "status_pending": "📋 Pending",
        "status_progress": "🔵 In Progress",
        "status_done": "✅ Done",
        "status_column_help": "Update task status",
        "check_column_help": "Select to view details",
        
        # Metrics
        "metric_completed": "Completed",
        "metric_progress": "In Progress",
        "metric_pending": "Pending",
        "metric_total_prog": "Progress",
        
        # Calendar (tab 2)
        "calendar_found_events": "📊 Found **{count}** events with deadlines",
        "calendar_legend": "🔴 Immediate/Short-term | 🟠 Medium-term | 🟢 Low Urgency | ⚪ Past Event | ✅ Task Completed",
        "event_completed_msg": "This task is marked as completed.",
        "event_past_msg": "⚠️ This event deadline has passed.",
        
        # Gmail buttons
        "btn_open_thread": "📂 Open Thread in Gmail",
        "help_open_thread": "Opens conversation in account {email}.",
        "btn_reply_new": "↩️ Reply (New Draft)",
        "help_reply_new": "Original thread not found. Creating a new draft."
    }
}


def t(key: str, lang: str = "es", **kwargs) -> str:
    """
    Helper function to get translations
    
    Args:
        key: Translation key
        lang: Language code ('es' or 'en')
        **kwargs: Variables to format into the translation string
        
    Returns:
        Translated text with formatted variables
    """
    text = TRANSLATIONS.get(lang, {}).get(key, TRANSLATIONS["es"].get(key, key))
    return text.format(**kwargs) if kwargs else text
