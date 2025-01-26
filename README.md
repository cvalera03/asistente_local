# Asistente Virtual Local
Proyecto para poder correr un asistente virtual de manera local. Integra distintos modelos de machine learning para poder brindar distintas funcionalidades.
Actualmente el asistente corre en local sin necesidad de internet con un modelo de LLM basico para su uso. Se puede cambiar por cualquiera de Ollama.

# Requisitos

Para instalar dependencias ejecutar:
```
pip install -r requirements.txt
```
Instalar aplicación [`Ollama`](https://ollama.com/) y ejecutar este comando en terminal:
```
ollama run llama3.2
```

Una vez dentro del repositorio usar:
```
python main.py
```

Whisper también requiere la herramienta de línea de comandos [`ffmpeg`](https://ffmpeg.org/) para ser instalado en su sistema, está disponible en la mayoría de los administradores de paquetes:

```
# on Ubuntu or Debian
sudo apt update && sudo apt install ffmpeg

# on Arch Linux
sudo pacman -S ffmpeg

# on MacOS using Homebrew (https://brew.sh/)
brew install ffmpeg

# on Windows using Chocolatey (https://chocolatey.org/)
choco install ffmpeg

# on Windows using Scoop (https://scoop.sh/)
scoop install ffmpeg
```

Para mas información sobre Whisper visita: https://github.com/openai/whisper

# Objetivos
- [X] Transcripción en tiempo real 
- [X] Detectar palabra clave para que el asistente sepa que se le esta hablando y ejecutar acciones
- [X] Interfaz
- [X] Opciones de mas modelos
- [X] Correr en segundo plano
- [X] Añadir lista de aplicaciones
- [X] Conectarlo a un chatbot
- [X] Control de multimedia local

# Créditos y aportaciones
Lista de repositorios y recursos consultados o usados para este asistente virtual. 
* Base del proyecto. [Github Puigalex](https://github.com/puigalex/asistente_local)
* Implementación con mejoras para correr Whisper cercano a en tiempo real. [Github Davase](https://github.com/davabase/whisper_real_time)
