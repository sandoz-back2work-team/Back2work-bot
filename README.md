# 📧 Back2Work Bot

Asistente inteligente basado en IA para la priorización y gestión automática de correos electrónicos tras períodos de ausencia.

## Descripción

Back2Work Bot es una aplicación de Streamlit que utiliza OpenAI GPT-4 para analizar, clasificar y priorizar automáticamente tu bandeja de entrada después de vacaciones o ausencias prolongadas. Genera resúmenes ejecutivos, identifica acciones pendientes y crea un plan de trabajo personalizado.

### Características Principales

- **Análisis inteligente con IA**: Clasificación automática por prioridad, urgencia y tipo
- **Dashboard interactivo**: Visualización de emails por remitente, proyecto, prioridad
- **Calendario de vencimientos**: Detección automática de deadlines y reuniones
- **Gestión de tareas**: Extracción y seguimiento de acciones pendientes
- **Integración con Gmail**: Conexión directa con tu cuenta de Gmail
- **Asistente conversacional**: Chat IA para consultas sobre tus correos
- **Multiidioma**: Soporte para español e inglés
- **Priorización personalizada**: Configuración de remitentes VIP y proyectos clave

## Estructura del Proyecto
```
Back2work-bot/
├── app/
│   ├── main.py                 # Aplicación principal Streamlit
│   ├── gmail_connector.py      # Integración con Gmail API
│   └── ...
├── docs/
│   └── manual_usuario.pdf      # 📘 Documentación completa (TFM)
├── local/secrets/              # ⚠️ Crear localmente (ver abajo)
├── .gitignore                  # Archivos excluidos de Git
│   ├── .env                    # Tu OpenAI API Key
│   └── credentials.json        # Gmail OAuth (opcional)
├── requirements.txt
├── iniciar_bot.bat             # Script de inicio Windows
└── README.md
```

### Sobre `local/secrets/`

Estos archivos **NO están en GitHub** por seguridad y debes crearlos manualmente.

**Consulta**:
- La sección [**Instalación**](#-instalación) más abajo para configuración rápida
- El [**Manual de Usuario**](docs/manual_usuario.pdf) para guía detallada paso a paso

> Los archivos de credenciales están protegidos en `.gitignore` y nunca se subirán al repositorio.

---

## Instalación

### Requisitos Previos

- Python 3.8 o superior
- Cuenta de OpenAI con API Key
- (Opcional) Cuenta de Gmail para integración directa

### Pasos de Instalación

1. **Clonar el repositorio**
```bash
git clone https://github.com/sandoz-back2work-team/Back2work-bot.git
cd Back2work-bot
```

2. **Crear entorno virtual**
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar API Key de OpenAI**

Opción A: Crear archivo `.streamlit/secrets.toml`
```toml
OPENAI_API_KEY = "sk-..."
```

Opción B: Crear archivo `local/secrets/.env`
```
OPENAI_API_KEY=sk-...
```

5. **Configurar Gmail (Opcional)**

Para usar la integración con Gmail:
- Crear proyecto en Google Cloud Console
- Habilitar Gmail API
- Descargar credenciales OAuth 2.0
- Guardar como `credentials.json` en `local/secrets/`

## Uso

### Iniciar la aplicación

**Windows**: 
```bash
iniciar_bot.bat
```
(doble clic o desde terminal)

**Mac / Linux**: 
```bash
source venv/bin/activate
python -m streamlit run app/main.py
```

La aplicación se abrirá en tu navegador en `http://localhost:8501`

### Flujo de Trabajo

1. **Seleccionar fuente de datos**
   - Cargar archivo CSV exportado desde Gmail
   - O conectar directamente con Gmail

2. **Configurar período de ausencia**
   - Seleccionar fechas de inicio y fin

3. **Personalizar prioridades**
   - Añadir remitentes VIP
   - Especificar proyectos clave
   - Definir reglas personalizadas

4. **Ejecutar análisis**
   - El bot procesará los emails con IA
   - Generará resumen ejecutivo
   - Clasificará y priorizará automáticamente

5. **Revisar resultados**
   - **Resumen y Tareas**: Vista de acciones pendientes con deadlines
   - **Calendario**: Visualización de vencimientos
   - **Bandeja Priorizada**: Emails ordenados por importancia
   - **Gráficas**: Dashboard interactivo
   - **Chat IA**: Consultas sobre tus correos
  
## Documentación

Este proyecto incluye documentación completa del Trabajo de Fin de Grado:

📘 **[Manual de Usuario Completo (PDF)](docs/manual_usuario.pdf)**

El manual incluye:
- Guía de instalación paso a paso
- Configuración de OpenAI API y Gmail
- Casos de uso y ejemplos
- Arquitectura del sistema

Para un inicio rápido, sigue las instrucciones abajo. Para información detallada, consulta el manual.

---

## Seguridad y Privacidad

- Las credenciales nunca se almacenan en el código
- Autenticación OAuth 2.0 para Gmail
- Detección automática de phishing y spam
- Los datos se procesan localmente
- No se almacenan emails en servidores externos

## Tecnologías Utilizadas

- **Frontend**: Streamlit
- **IA**: OpenAI GPT-4
- **Visualización**: Plotly, Streamlit-Calendar
- **Email**: Gmail API, OAuth 2.0
- **Procesamiento**: Pandas, Python

## Formato CSV (si no usas Gmail)

Si prefieres cargar un CSV, debe tener estas columnas:
```
Subject, Body, From: (Name), From: (Address), To: (Address), 
CC: (Address), Received_date, Importance, threadId
```

Exporta tus emails desde Gmail usando Google Takeout o extensiones de Chrome.

## Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## Licencia

Este proyecto está bajo la Licencia Apache 2.0. Ver archivo `LICENSE` para más detalles.

**En resumen**: Puedes usar, modificar y distribuir este código libremente, 
incluso con fines comerciales, siempre que incluyas el aviso de copyright y la licencia.

## Autores

- **Valery Alfaro** - *Colaborador* - [GitHub](https://github.com/valalfaro1997)
- **Maria Cristina Mohor** - *Colaborador* - [GitHub](https://github.com/CristinaMohor)
- **Alejandra Motta** - *Colaborador* - [GitHub](https://github.com/alejandra-motta)
- **David Orrego** - *Colaborador* - [GitHub](https://github.com/davidorrego96)
- **Meliza Perneth** - *Colaborador* - [GitHub](https://github.com/MelizaPerneth)


## Agradecimientos

- Proyecto de Fin de Grado
- OpenAI por GPT-4
- Comunidad de Streamlit

Para preguntas o soporte: [Abrir un Issue](https://github.com/sandoz-back2work-team/Back2work-bot/issues)

---

⭐ Si este proyecto te resulta útil, considera darle una estrella en GitHub
