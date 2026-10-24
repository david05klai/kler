# Kler

Asistente personal de escritorio para Windows con activación local por voz, automatización e interfaz reactiva.

## 🌟 Características Principales

* **Interfaz Kler:** Orbe reactivo y paleta cian con paneles translúcidos.
* **Activación por voz:** Di «Kler» mientras está en suspensión. El reconocimiento local usa Vosk y requiere el modelo en `config/vosk_model`. También puedes usar `Insert` como atajo.
* **Control Contextual del Entorno:** Control autónomo del volumen, brillo, energía y *Focus Assist* basado en tus hábitos y la ventana activa en pantalla.
* **Programación Autónoma en Sandbox:** KLER puede escribirse sus propios scripts de habilidades (`auto_programmer`), compilarlos en frío y ejecutarlos con un timeout seguro en un entorno de pruebas, para inyectar su propio código en tiempo real si tiene éxito.
* **Navegación Web (YouTube):** Capacidad nativa de buscar música y videos invisibles y reproducirlos automáticamente a través del navegador web.
* **Organizador y Gestor de Archivos:** Abre, visualiza y edita documentos, sumado al análisis de archivos con clasificación inteligente y eliminación de duplicados exactos usando sumas `MD5`.
* **Comunicaciones Unificadas:** Envía información centralizada usando correos, Telegram, Discord, y WhatsApp desde una sola interfaz base.

## 🛠️ Tecnologías

* **Python 3.12**
* **PyQt6** (Para la interfaz holográfica dinámica y el QWebEngineView)
* **LLMs** (Soporte integrado para Gemini y OpenRouter)
* Integraciones de SO: `pycaw`, `pygetwindow`, `psutil`, `WMI`, `winreg` y llamadas directas al Win32 Kernel (`ctypes`) para el atajo global inteligente.

## 🚀 Instalación y Uso

1. Instala [Python 3.12](https://www.python.org/downloads/) asegurándote de marcar "Add Python to PATH".
2. Clona este repositorio en tu escritorio:
   ```bash
   git clone https://github.com/david05klai/kler.git
   ```
3. Descarga el modelo de voz local con `python download_vosk.py` para activar Kler por voz.
4. Ejecuta el archivo `Instalar_Kler.bat` para construir el entorno virtual (`.venv`) e instalar automáticamente todas las dependencias (`requirements.txt`).
5. Para iniciarlo rápidamente (y en segundo plano), puedes utilizar **`Iniciar Kler Beta.vbs`**.

## 🛡️ Notas de Seguridad
Este proyecto usa tu configuración local en `config/api_keys.json` para gestionar llaves maestras de API. Este archivo **no debe subirse** a GitHub bajo ningún concepto, por lo cual ya viene protegido automáticamente por el `.gitignore` nativo de esta rama.

---
*Desarrollado y mantenido con IA & 2PAC.*


