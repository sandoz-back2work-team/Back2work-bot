import os
import pickle
from pathlib import Path
from typing import List, Dict, Optional
import base64
from email.mime.text import MIMEText
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import streamlit as st
import pandas as pd

# Scopes necesarios (solo lectura)
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GmailConnector:
    """Conector para la API de Gmail"""
    
    def __init__(self, credentials_path: str = 'client_secret.json'):
        self.credentials_path = credentials_path
        self.service = None
        self.creds = None
        
    def authenticate(self) -> bool:
        """
        Gestiona el flujo de autenticación OAuth 2.0
        Retorna True si la autenticación es exitosa
        """
        token_path = 'token.pickle'
        
        # Verificar si ya existe un token guardado
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                self.creds = pickle.load(token)
        
        # Si no hay credenciales válidas, solicitar login
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    st.error(f"Error al refrescar token: {e}")
                    # Si falla el refresh, forzar nuevo login
                    os.remove(token_path)
                    return self.authenticate()
            else:
                if not os.path.exists(self.credentials_path):
                    st.error(f"❌ No se encuentra el archivo {self.credentials_path}")
                    st.info("💡 Descarga las credenciales OAuth desde Google Cloud Console")
                    return False
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES)
                    self.creds = flow.run_local_server(port=0)
                except Exception as e:
                    st.error(f"Error en autenticación: {e}")
                    return False
            
            # Guardar credenciales para futuras ejecuciones
            with open(token_path, 'wb') as token:
                pickle.dump(self.creds, token)
        
        try:
            self.service = build('gmail', 'v1', credentials=self.creds)
            return True
        except Exception as e:
            st.error(f"Error al construir servicio Gmail: {e}")
            return False
    
    def get_user_email(self) -> str:
        """Obtiene el email del usuario autenticado"""
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            return profile.get('emailAddress', 'Unknown')
        except HttpError as e:
            st.error(f"Error al obtener perfil: {e}")
            return "Unknown"
    
    def fetch_emails(self, 
                 start_date: Optional[datetime] = None, 
                 end_date: Optional[datetime] = None,
                 max_results: int = 200,
                 query: str = "",
                 lang: str = "es") -> List[Dict]:
        """
        Descarga emails de Gmail con filtros opcionales
        
        Args:
            start_date: Fecha inicial (None = sin filtro)
            end_date: Fecha final (None = sin filtro)
            max_results: Máximo número de emails a descargar
            query: Query adicional de Gmail (ej: "from:jefe@empresa.com")
        
        Returns:
            Lista de diccionarios con los datos del email
        """
        if not self.service:
            st.error("❌ Debes autenticarte primero")
            return []
        
        # Construir query de búsqueda
        search_query = query
        if start_date:
            search_query += f" after:{start_date.strftime('%Y/%m/%d')}"
        if end_date:
            search_query += f" before:{end_date.strftime('%Y/%m/%d')}"
        
        emails_data = []
        
        try:
            # Obtener lista de IDs de mensajes
            results = self.service.users().messages().list(
                userId='me',
                q=search_query.strip(),
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                if lang == "es":
                    st.warning("No se encontraron emails con los filtros aplicados")
                else:
                    st.warning("No emails found with the applied filters")
                return []
            
            # Barra de progreso
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, msg in enumerate(messages):
                try:
                    # Obtener detalles completos del mensaje
                    message = self.service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    
                    # Extraer campos
                    email_data = self._parse_message(message)
                    emails_data.append(email_data)
                    
                    # Actualizar progreso
                    progress = (i + 1) / len(messages)
                    progress_bar.progress(progress)
                    if lang == "es":
                        status_text.text(f"Descargando email {i+1}/{len(messages)}")
                    else:
                        status_text.text(f"Downloading email {i+1}/{len(messages)}")
                    
                except HttpError as e:
                    st.warning(f"Error al descargar mensaje {msg['id']}: {e}")
                    continue
            
            progress_bar.empty()
            status_text.empty()
            
            if lang == "es":
                st.success(f"✅ Descargados {len(emails_data)} emails correctamente")
            else:
                st.success(f"✅ Successfully downloaded {len(emails_data)} emails")
            
            return emails_data
            
        except HttpError as e:
            st.error(f"Error al buscar emails: {e}")
            return []
    
    def _parse_message(self, message: Dict) -> Dict:
        """Parsea un mensaje de Gmail a formato compatible con tu app"""
        
        headers = {h['name']: h['value'] for h in message['payload']['headers']}
        
        # Extraer cuerpo del mensaje
        body = self._get_message_body(message['payload'])
        
        # Parsear fecha
        timestamp = int(message['internalDate']) / 1000
        received_date = datetime.fromtimestamp(timestamp)
        
        # Extraer importancia (si existe)
        importance = headers.get('Importance', headers.get('X-Priority', ''))
        if importance:
            if '1' in str(importance) or 'high' in str(importance).lower():
                importance = 'High'
            else:
                importance = 'Normal'
        else:
            importance = 'Normal'
        
        return {
            'Subject': headers.get('Subject', '(Sin asunto)'),
            'From: (Name)': self._extract_name(headers.get('From', '')),
            'From: (Address)': self._extract_email(headers.get('From', '')),
            'To: (Name)': self._extract_name(headers.get('To', '')),
            'To: (Address)': headers.get('To', ''),
            'CC: (Name)': self._extract_name(headers.get('Cc', '')),
            'CC: (Address)': headers.get('Cc', ''),
            'BCC: (Address)': headers.get('Bcc', ''),
            'Received_date': received_date.strftime('%Y-%m-%d %H:%M:%S'),
            'Importance': importance,
            'Body': body,
            'gmail_id': message['id'],
            'thread_id': message['threadId']
        }
    
    def _get_message_body(self, payload: Dict) -> str:
        """Extrae el cuerpo del mensaje (texto plano preferido)"""
        
        if 'body' in payload and payload['body'].get('data'):
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if part['body'].get('data'):
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                
                # Si no hay text/plain, intentar con text/html
                if part['mimeType'] == 'text/html':
                    if part['body'].get('data'):
                        html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                        # Aquí podrías usar BeautifulSoup para limpiar HTML, pero por simplicidad:
                        return html
        
        return ""
    
    def _extract_name(self, email_str: str) -> str:
        """Extrae el nombre de un string 'Name <email@domain.com>'"""
        if '<' in email_str:
            return email_str.split('<')[0].strip().strip('"')
        return ""
    
    def _extract_email(self, email_str: str) -> str:
        """Extrae el email de un string 'Name <email@domain.com>'"""
        if '<' in email_str and '>' in email_str:
            return email_str.split('<')[1].split('>')[0].strip()
        return email_str.strip()

    def get_user_display_name(self) -> str:
        """
        Extrae un nombre legible del email del usuario autenticado.
        Ej: john.doe@company.com -> John Doe
        """
        try:
            email = self.get_user_email()
            if not email or email == 'Unknown':
                return "Usuario"
            
            # Tomar la parte antes del @
            local_part = email.split('@')[0]
            
            # Reemplazar separadores por espacios
            name = local_part.replace('.', ' ').replace('_', ' ').replace('-', ' ')
            
            # Capitalizar cada palabra
            return name.title()
        except Exception as e:
            print(f"Error extrayendo nombre: {e}")
            return "Usuario"