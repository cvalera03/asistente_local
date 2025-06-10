import io
import os
import speech_recognition as sr
import whisper
import time
import subprocess
from datetime import datetime, timedelta
from queue import Queue
from tempfile import NamedTemporaryFile
import gtts
import pygame
import ctypes
import threading
from ollama import chat
import keyboard
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox, Toplevel
import pystray
from PIL import Image
import csv
import uuid
import requests
import google.generativeai as genai 
import logging
import sys
import traceback
import re
# --- INTEGRACIÓN FLASK ---
from flask import Flask, request, jsonify, send_from_directory
import socket

# Configuración de webapp y token
WEBAPP_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'webapp')

app = Flask(__name__)


@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({'status': 'ok'})

@app.route('/webapp/<path:filename>')
def serve_webapp(filename):
    return send_from_directory(WEBAPP_FOLDER, filename)

@app.route('/', methods=['GET', 'POST'])
def root():
    if request.method == 'GET':
        return send_from_directory(WEBAPP_FOLDER, 'index.html')
    elif request.method == 'POST':
        data = request.json
        texto_usuario = data.get('text')
        if not texto_usuario:
            return jsonify({'error': 'No text provided'}), 400
        try:
            result = chat_bot(texto_usuario)
            return jsonify({'result': result})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

def run_flask():
    # Usa la IP local de la máquina
    ip_local = socket.gethostbyname(socket.gethostname())
    app.run(host=ip_local, port=5000, debug=False)

# Ensure the script is running in the correct directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    filename='chatbot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    error_message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logging.error(error_message)
    print(error_message)
    messagebox.showerror("Error no controlado", f"Ha ocurrido un error no controlado:\n\n{error_message}\n\nEl programa se cerrará.")
    cerrar_programa()

def delete_mp3_files():
    directory = os.path.dirname(os.path.abspath(__file__))
    for file in os.listdir(directory):
        if file.endswith(".mp3"):
            file_path = os.path.join(directory, file)
            try:
                os.remove(file_path)
            except Exception as e:
                logging.error(f"Error eliminando {file_path}: {e}")

delete_mp3_files()

def create_image():
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo.ico')
    if os.path.exists(icon_path):
        return Image.open(icon_path).convert("RGBA")

def on_quit(icon, item):
    icon.stop()
    cerrar_programa()

def show_window(icon, item):
    icon.stop()
    root.deiconify()

def minimize_to_tray():
    icon_image = create_image()
    if icon_image:
        icon = pystray.Icon("Chatbot")
        icon.icon = icon_image
        icon.menu = pystray.Menu(
            pystray.MenuItem('Show', show_window),
            pystray.MenuItem('Quit', on_quit)
        )
        icon.run_detached()
        root.withdraw()

class AppManager:
    def __init__(self, csv_path='apps.csv'):
        self.csv_path = csv_path
        self.apps = self.load_apps()

    def create_default_apps_csv(self):
        with open(self.csv_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Nombre", "Ruta"])

    def load_apps(self):
        apps = {}
        if not os.path.exists(self.csv_path):
            self.create_default_apps_csv()
        with open(self.csv_path, mode='r', newline='') as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) == 2:
                    apps[row[0].lower()] = [row[1]]
        return apps

    def save_apps(self):
        with open(self.csv_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            for app, path in self.apps.items():
                writer.writerow([app, path[0]])

app_manager = AppManager()
apps = app_manager.apps

def add_app():
    app_name = simpledialog.askstring("Add App", "Enter the app name:")
    app_path = simpledialog.askstring("Add App", "Enter the app path:")
    if app_name and app_path:
        if not os.path.exists(app_path):
            messagebox.showerror("Error", "La ruta especificada no existe.")
            return
        apps[app_name.lower()] = [app_path]
        app_manager.save_apps()
        update_apps_list()
        messagebox.showinfo("Success", f"App '{app_name}' added successfully!")

def edit_app():
    selected = apps_list.curselection()
    if selected:
        app_name = apps_list.get(selected).split()[0].strip().lower()
        new_app_name = simpledialog.askstring("Edit App", "Enter the new app name:", initialvalue=app_name)
        new_app_path = simpledialog.askstring("Edit App", "Enter the new app path:", initialvalue=apps[app_name][0])
        if new_app_name and new_app_path:
            if not os.path.exists(new_app_path):
                messagebox.showerror("Error", "La ruta especificada no existe.")
                return
            del apps[app_name]
            apps[new_app_name.lower()] = [new_app_path]
            app_manager.save_apps()
            update_apps_list()
            messagebox.showinfo("Success", f"App '{new_app_name}' updated successfully!")

def delete_app():
    selected = apps_list.curselection()
    if selected:
        app_name = apps_list.get(selected).split(":")[0].strip().lower()
        if messagebox.askyesno("Delete App", f"Are you sure you want to delete '{app_name}'?"):
            try:
                del apps[app_name]
                app_manager.save_apps()
                update_apps_list()
                messagebox.showinfo("Success", f"App '{app_name}' deleted successfully!")
            except Exception as e:
                logging.error(f"Error eliminando app {app_name}: {e}")

def update_apps_list():
    apps_list.delete(0, tk.END)
    for app, path in apps.items():
        apps_list.insert(tk.END, f"{app.upper():<20} {path[0]}")

def set_taskbar_icon(root):
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo.ico')
    icon = Image.open(icon_path)
    icon_data = icon.tobytes("raw", "BGRA")
    hicon = ctypes.windll.user32.CreateIconFromResourceEx(
        icon_data, len(icon_data), 1, 0x00030000, icon.width, icon.height, 0
    )
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("myappid")
    root.iconbitmap(icon_path)
    ctypes.windll.user32.SendMessageW(root.winfo_id(), 0x80, 1, hicon)

def save_options(model_type, llama_model, whisper_model, start_minimized, city, api_key, gemini_api_key, theme):
    options = {
        "ModelType": model_type,
        "LlamaModel": llama_model,
        "WhisperModel": whisper_model,
        "StartMinimized": "True" if start_minimized else "False",
        "City": city,
        "APIKey": api_key,
        "GeminiAPIKey": gemini_api_key,
        "Theme": theme
    }
    with open('options.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        for key, value in options.items():
            writer.writerow([key, value])

def load_options():
    default_options = {
        "ModelType": "local",
        "LlamaModel": "llama3.2",
        "WhisperModel": "small",
        "StartMinimized": "False",
        "City": "CITY",
        "APIKey": "API_KEY",
        "GeminiAPIKey": "GEMINI_API_KEY",
        "Theme": "light"
    }
    if os.path.exists('options.csv'):
        with open('options.csv', mode='r', newline='') as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) == 2:
                    default_options[row[0]] = row[1]
    if default_options["ModelType"] == "gemini" and default_options["GeminiAPIKey"] != "GEMINI_API_KEY":
        genai.configure(api_key=default_options["GeminiAPIKey"])
    return default_options

temp_file = NamedTemporaryFile().name
transcription = ['']
options = load_options()
llama_model = options["LlamaModel"]
whisper_model = options["WhisperModel"]
city = options["City"]
api_key = options["APIKey"]
audio_model = whisper.load_model(whisper_model)
data_queue = Queue()
recorder = sr.Recognizer()
recorder.energy_threshold = 500
recorder.dynamic_energy_threshold = False
wake_word = ["lumi", "lumie", "lumia", "lummi", "lumii"]
audio_thread = None
stop_audio_event = threading.Event()
chat_history = []
callado = False

THEMES = {
    "light": {
        "BG": "#fff",
        "BG2": "#f5f5f5",
        "FG": "#111",
        "FG2": "#333",
        "BTN_BG": "#fff",
        "BTN_FG": "#111",
        "BTN_BG_HOVER": "#111",
        "BTN_FG_HOVER": "#fff",
        "ENTRY_BG": "#fff",
        "ENTRY_FG": "#111",
        "FRAME_BG": "#f5f5f5",
        "BORDER": "#ccc"
    },
    "dark": {
        "BG": "#181818",
        "BG2": "#232323",
        "FG": "#eee",
        "FG2": "#fff",
        "BTN_BG": "#232323",
        "BTN_FG": "#eee",
        "BTN_BG_HOVER": "#fff",
        "BTN_FG_HOVER": "#181818",
        "ENTRY_BG": "#232323",
        "ENTRY_FG": "#eee",
        "FRAME_BG": "#232323",
        "BORDER": "#444"
    }
}

def apply_theme(theme_name):
    theme = THEMES[theme_name]
    root.configure(bg=theme["BG"])
    title_label.config(bg=theme["BG"], fg=theme["FG2"])
    chat_frame.config(bg=theme["FRAME_BG"], highlightbackground=theme["BORDER"], highlightcolor=theme["BORDER"])
    chat_display.config(bg=theme["ENTRY_BG"], fg=theme["FG"], insertbackground=theme["FG"], highlightthickness=0)
    command_frame.config(bg=theme["BG"])
    command_entry.config(bg=theme["ENTRY_BG"], fg=theme["FG"], highlightbackground=theme["BORDER"])
    execute_button.config(bg=theme["BTN_BG"], fg=theme["BTN_FG"], activebackground=theme["BTN_BG_HOVER"], activeforeground=theme["BTN_FG_HOVER"])
    buttons_frame.config(bg=theme["BG"])
    minimize_button.config(bg=theme["BTN_BG"], fg=theme["BTN_FG"], activebackground=theme["BTN_BG_HOVER"], activeforeground=theme["BTN_FG_HOVER"])
    apps_button.config(bg=theme["BTN_BG"], fg=theme["BTN_FG"], activebackground=theme["BTN_BG_HOVER"], activeforeground=theme["BTN_FG_HOVER"])
    options_button.config(bg=theme["BTN_BG"], fg=theme["BTN_FG"], activebackground=theme["BTN_BG_HOVER"], activeforeground=theme["BTN_FG_HOVER"])
    def make_hover(btn):
        btn.bind("<Enter>", lambda e: btn.config(bg=theme["BTN_BG_HOVER"], fg=theme["BTN_FG_HOVER"]))
        btn.bind("<Leave>", lambda e: btn.config(bg=theme["BTN_BG"], fg=theme["BTN_FG"]))
    for btn in [execute_button, minimize_button, apps_button, options_button]:
        make_hover(btn)

def listen():
    phrase_time = None
    phrase_timeout = 2
    record_timeout = 10
    last_sample = bytes()
    source = sr.Microphone(sample_rate=16000)
    with source:
        recorder.adjust_for_ambient_noise(source)
        recorder.energy_threshold += 25

    def record_callback(_, audio: sr.AudioData):
        data = audio.get_raw_data()
        data_queue.put(data)

    stop_listen = recorder.listen_in_background(source, record_callback, phrase_time_limit=record_timeout)
    while True:
        if not data_queue.empty():
            now = datetime.now()
            phrase_complete = False
            if phrase_time and now - phrase_time > timedelta(seconds=phrase_timeout):
                last_sample = bytes()
                phrase_complete = True
            phrase_time = now
            while not data_queue.empty():
                data = data_queue.get()
                last_sample += data
            audio_data = sr.AudioData(last_sample, source.SAMPLE_RATE, source.SAMPLE_WIDTH)
            wav_data = io.BytesIO(audio_data.get_wav_data())
            with open(temp_file, 'w+b') as f:
                f.write(wav_data.read())
            text = transcribe_audio(temp_file)
            if phrase_complete:
                transcription.append(text)
            else:
                transcription[-1] = text
            if any(word in transcription[-1].lower() for word in wake_word):
                try:
                    pygame.mixer.init()
                    if pygame.mixer.music.get_busy():
                        pygame.mixer.music.stop()
                        pygame.mixer.music.unload()
                    mensaje = transcription[-1].lower()
                    respuesta = accion(mensaje)
                    if not callado:
                        tts(respuesta)
                    update_chat_display(f"User: {mensaje}")
                    update_chat_display(f"Assistant: {respuesta}")
                except Exception as e:
                    logging.error(f"Error en listen/playback: {e}")
        else:
            time.sleep(0.25)

def transcribe_audio(temp_file):
    try:
        result = audio_model.transcribe(temp_file, language='es')
        return result['text'].strip()
    except Exception:
        return ""

def open_app(app_name):
    if app_name in apps:
        try:
            subprocess.Popen(apps[app_name][0], creationflags=subprocess.CREATE_NO_WINDOW)
            return f"Abro {app_name}"
        except Exception:
            return f"No se pudo abrir {app_name}."
    else:
        return f"No tengo configurada la aplicación '{app_name}'."

def lock_workstation():
    ctypes.windll.user32.LockWorkStation()
    return "Hasta luego"

def play_media():
    keyboard.send("play/pause media")
    return "Reproduciendo"

def pause_media():
    keyboard.send("play/pause media")
    return "Pausando"

def next_track():
    keyboard.send("next track")
    return "Siguiente canción"

def previous_track():
    keyboard.send("previous track")
    keyboard.send("previous track")
    return "Canción anterior"

def shutdown():
    os.system("shutdown /s /t 1")
    return "Apagando"

def say_goodbye():
    t = threading.Thread(name='adios', target=cerrar_programa)
    t.daemon = True
    t.start()
    return "Adiós"

def mute_audio():
    stop_audio()
    return "Me callo"

def toggle_silent_mode():
    global callado
    callado = not callado
    respuesta = "Modo callado activado" if callado else "Modo callado desactivado"
    tts(respuesta)
    return respuesta

def get_temperature():
    url = f'http://api.openweathermap.org/data/2.5/weather?appid=' + api_key + '&q=' + city + '&units=metric&lang=es'
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        temp = data['main']['temp']
        description = data['weather'][0]['description']
        return f"El clima en {city} es {description} con una temperatura de {temp}°C"
    except Exception:
        return "No se pudo obtener la temperatura"

commands = {
    "abre": open_app,
    "bloqueate": lock_workstation,
    "pausa": pause_media,
    "reproduce": play_media,
    "siguiente": next_track,
    "anterior": previous_track,
    "duermete": shutdown,
    "apagate": shutdown,
    "adiós": say_goodbye,
    "callate": mute_audio,
    "cállate": mute_audio,
    "modo callado": toggle_silent_mode,
    "temperatura": get_temperature,
}

def accion(texto):
    texto = texto.lower()
    for command, function in commands.items():
        if command in texto:
            if command == "abre":
                for app_name in apps:
                    if app_name in texto:
                        return function(app_name)
                return "No se que abrir"
            elif command in ["callate", "cállate", "modo callado", "temperatura", "adiós"]:
                return function()
            else:
                return function()
    return chat_bot(texto)

def remove_think_tags(text):
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

def process_command_entry(command_entry):
    command = command_entry.get()
    command_entry.delete(0, tk.END)
    if command:
        threading.Thread(target=process_command, args=(command,), daemon=True).start()

def process_command(command):
    try:
        pygame.mixer.init()
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
        respuesta = accion(command)
        subprocess.Popen(["ollama", "stop", llama_model], creationflags=subprocess.CREATE_NO_WINDOW)
        if not callado:
            tts(respuesta)
        update_chat_display(f"User: {command}")
        update_chat_display(f"Assistant: {respuesta}")
    except Exception:
        pass

def chat_bot(texto):
    options = load_options()
    max_history = 10
    if len(chat_history) > max_history * 2:
        chat_history.clear()
    if options["ModelType"] == "local":
        try:
            chat_history.append({'role': 'user', 'content': texto})
            stream = chat(
                model=llama_model,
                messages=[
                    {"role": "system", "content": "Eres una asistenta y te llamas lumi pero te van a llamar de otras formas y no vas a mencionar que te llamen asi, hablas español"},
                    *chat_history[-max_history:]
                ],
                stream=True,
            )
            response = "".join(chunk.message.content for chunk in stream)
            response = remove_think_tags(response)
            chat_history.append({'role': 'assistant', 'content': response})
            return response
        except Exception:
            return "Error al interactuar con el LLM"
    elif options["ModelType"] == "gemini":
        try:
            model = genai.GenerativeModel('gemini-2.0-flash-lite')
            chat_g = model.start_chat(history=[])
            response_g = chat_g.send_message(texto)
            return response_g.text
        except Exception:
            return "Error al interactuar con Gemini"

def tts(texto):
    try:
        filename = generate_audio_file(texto)
        play_audio_threaded(filename)
    except Exception:
        pass

def generate_audio_file(texto):
    try:
        tts = gtts.gTTS(texto, lang='es')
        unique_filename = f'audio_{uuid.uuid4()}.mp3'
        tts.save(unique_filename)
        return unique_filename
    except Exception:
        return None

def play_audio_threaded(filename):
    if filename is None:
        return
    global audio_thread
    if audio_thread and audio_thread.is_alive():
        stop_audio()
    stop_audio_event.clear()
    audio_thread = threading.Thread(target=play_audio, args=(filename,))
    audio_thread.daemon = True
    audio_thread.start()

def play_audio(filename):
    try:
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            if stop_audio_event.is_set():
                pygame.mixer.music.stop()
                break
            pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
    except Exception:
        pass

def stop_audio():
    global audio_thread
    if audio_thread and audio_thread.is_alive():
        stop_audio_event.set()
        audio_thread.join(timeout=2)

def cerrar_programa():
    try:
        time.sleep(2)
        subprocess.Popen(["ollama", "stop", llama_model], creationflags=subprocess.CREATE_NO_WINDOW)
        os._exit(0)
    except Exception:
        os._exit(1)

def show_apps_window():
    theme = THEMES[options["Theme"]]
    apps_window = Toplevel(root)
    apps_window.title("Current Apps")
    apps_window.geometry("600x475")
    apps_window.configure(bg=theme["BG"])
    apps_list_label = tk.Label(apps_window, text="Current Apps:", font=("Segoe UI", 12, "bold"), fg=theme["FG2"], bg=theme["BG"])
    apps_list_label.pack(pady=5)
    global apps_list
    apps_list = tk.Listbox(apps_window, width=60, height=20, font=("Courier", 10), bg=theme["ENTRY_BG"], fg=theme["FG"], bd=1, relief="solid", highlightbackground=theme["BORDER"])
    apps_list.pack(padx=10, pady=10)
    update_apps_list()
    buttons_frame = tk.Frame(apps_window, bg=theme["BG"])
    buttons_frame.pack(pady=5)
    def style_button(btn):
        btn.configure(
            font=("Segoe UI", 10, "bold"),
            bg=theme["BTN_BG"],
            fg=theme["BTN_FG"],
            activebackground=theme["BTN_BG_HOVER"],
            activeforeground=theme["BTN_FG_HOVER"],
            bd=0,
            relief="flat",
            cursor="hand2"
        )
        btn.bind("<Enter>", lambda e: btn.config(bg=theme["BTN_BG_HOVER"], fg=theme["BTN_FG_HOVER"]))
        btn.bind("<Leave>", lambda e: btn.config(bg=theme["BTN_BG"], fg=theme["BTN_FG"]))
    add_button = tk.Button(buttons_frame, text="Add App", command=add_app)
    style_button(add_button)
    add_button.pack(side=tk.LEFT, padx=5)
    edit_button = tk.Button(buttons_frame, text="Edit App", command=edit_app)
    style_button(edit_button)
    edit_button.pack(side=tk.LEFT, padx=5)
    delete_button = tk.Button(buttons_frame, text="Delete App", command=delete_app)
    style_button(delete_button)
    delete_button.pack(side=tk.LEFT, padx=5)

def show_options_window():
    theme = THEMES[options["Theme"]]
    options_window = Toplevel(root)
    options_window.title("Options")
    options_window.geometry("400x600")
    options_window.configure(bg=theme["BG"])
    opts = load_options()
    model_frame = tk.LabelFrame(options_window, text="Model Selection", bg=theme["FRAME_BG"], fg=theme["FG2"], font=("Segoe UI", 10, "bold"), bd=2, relief="groove", highlightbackground=theme["BORDER"])
    model_frame.pack(pady=10, padx=10, fill="x")
    model_type_var = tk.StringVar(options_window)
    model_type_var.set(opts["ModelType"])
    local_model_radio = tk.Radiobutton(
        model_frame, text="Local LLM (oLLama)", variable=model_type_var, value="local",
        bg=theme["FRAME_BG"], fg=theme["FG"], selectcolor=theme["FRAME_BG"], font=("Segoe UI", 10), indicatoron=1, activebackground=theme["FRAME_BG"], activeforeground=theme["FG"]
    )
    local_model_radio.pack(anchor="w", padx=5)
    gemini_model_radio = tk.Radiobutton(
        model_frame, text="Gemini (API)", variable=model_type_var, value="gemini",
        bg=theme["FRAME_BG"], fg=theme["FG"], selectcolor=theme["FRAME_BG"], font=("Segoe UI", 10), indicatoron=1, activebackground=theme["FRAME_BG"], activeforeground=theme["FG"]
    )
    gemini_model_radio.pack(anchor="w", padx=5)
    tk.Label(options_window, text="oLlama Model:", bg=theme["BG"], fg=theme["FG2"], font=("Segoe UI", 10, "bold")).pack(pady=5)
    llama_model_var = tk.StringVar(options_window)
    llama_model_var.set(opts["LlamaModel"])
    llama_model_menu = tk.OptionMenu(options_window, llama_model_var, "llama3.2:3b", "llama3.2:1b", "deepseek-r1:1.5b", "gemma2:2b", "phi3:3.8b", "qwen:0.5b", "qwen:1.8b", "qwen:4b", "granite3.1-moe:3b", "granite3.1-moe:1b")
    llama_model_menu.config(bg=theme["BTN_BG"], fg=theme["BTN_FG"], font=("Segoe UI", 10))
    llama_model_menu["menu"].config(bg=theme["BTN_BG"], fg=theme["BTN_FG"])
    llama_model_menu.pack(pady=5)
    tk.Label(options_window, text="Whisper Model:", bg=theme["BG"], fg=theme["FG2"], font=("Segoe UI", 10, "bold")).pack(pady=5)
    whisper_model_var = tk.StringVar(options_window)
    whisper_model_var.set(opts["WhisperModel"])
    whisper_model_menu = tk.OptionMenu(options_window, whisper_model_var, "tiny", "base", "small", "medium", "large", "turbo")
    whisper_model_menu.config(bg=theme["BTN_BG"], fg=theme["BTN_FG"], font=("Segoe UI", 10))
    whisper_model_menu["menu"].config(bg=theme["BTN_BG"], fg=theme["BTN_FG"])
    whisper_model_menu.pack(pady=5)
    start_minimized_var = tk.BooleanVar(options_window)
    start_minimized_var.set(opts["StartMinimized"] == "True")
    tk.Checkbutton(options_window, text="Start Minimized to Tray", variable=start_minimized_var, bg=theme["BG"], fg=theme["FG"], font=("Segoe UI", 10), selectcolor=theme["BTN_BG"]).pack(pady=5)
    tk.Label(options_window, text="City:", bg=theme["BG"], fg=theme["FG2"], font=("Segoe UI", 10, "bold")).pack(pady=5)
    city_var = tk.StringVar(options_window)
    city_var.set(opts["City"])
    tk.Entry(options_window, textvariable=city_var, bg=theme["ENTRY_BG"], fg=theme["FG"], font=("Segoe UI", 10)).pack(pady=5)
    tk.Label(options_window, text="API Key:", bg=theme["BG"], fg=theme["FG2"], font=("Segoe UI", 10, "bold")).pack(pady=5)
    api_key_var = tk.StringVar(options_window)
    api_key_var.set(opts["APIKey"])
    tk.Entry(options_window, textvariable=api_key_var, bg=theme["ENTRY_BG"], fg=theme["FG"], font=("Segoe UI", 10)).pack(pady=5)
    tk.Label(options_window, text="Gemini API Key:", bg=theme["BG"], fg=theme["FG2"], font=("Segoe UI", 10, "bold")).pack(pady=5)
    gemini_api_key_var = tk.StringVar(options_window)
    gemini_api_key_var.set(opts["GeminiAPIKey"])
    tk.Entry(options_window, textvariable=gemini_api_key_var, bg=theme["ENTRY_BG"], fg=theme["FG"], font=("Segoe UI", 10)).pack(pady=5)
    tk.Label(options_window, text="Tema:", bg=theme["BG"], fg=theme["FG2"], font=("Segoe UI", 10, "bold")).pack(pady=5)
    theme_var = tk.StringVar(options_window)
    theme_var.set(opts.get("Theme", "light"))
    theme_menu = tk.OptionMenu(options_window, theme_var, "light", "dark")
    theme_menu.config(bg=theme["BTN_BG"], fg=theme["BTN_FG"], font=("Segoe UI", 10))
    theme_menu["menu"].config(bg=theme["BTN_BG"], fg=theme["BTN_FG"])
    theme_menu.pack(pady=5)
    def save_and_close():
        save_options(model_type_var.get(), llama_model_var.get(), whisper_model_var.get(), start_minimized_var.get(), city_var.get(), api_key_var.get(), gemini_api_key_var.get(), theme_var.get())
        options_window.destroy()
        messagebox.showinfo("Restart Required", "Para que surja efecto, vuelve a abrir el programa.")
        cerrar_programa()
    save_btn = tk.Button(options_window, text="Guardar", command=save_and_close)
    save_btn.configure(
        font=("Segoe UI", 10, "bold"),
        bg=theme["BTN_BG"],
        fg=theme["BTN_FG"],
        activebackground=theme["BTN_BG_HOVER"],
        activeforeground=theme["BTN_FG_HOVER"],
        bd=0,
        relief="flat",
        cursor="hand2"
    )
    save_btn.pack(pady=10)
    save_btn.bind("<Enter>", lambda e: save_btn.config(bg=theme["BTN_BG_HOVER"], fg=theme["BTN_FG_HOVER"]))
    save_btn.bind("<Leave>", lambda e: save_btn.config(bg=theme["BTN_BG"], fg=theme["BTN_FG"]))

# Initialize the GUI
root = tk.Tk()
root.withdraw()

options = load_options()
theme_name = options.get("Theme", "light")
theme = THEMES[theme_name]

root.geometry("550x550")
root.title("Lumi - Asistente Virtual")
icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'logo.ico'))
root.iconbitmap(icon_path)
set_taskbar_icon(root)

title_label = tk.Label(
    root,
    text="Lumi - Asistente Virtual",
    font=("Segoe UI", 20, "bold"),
    fg=theme["FG2"],
    bg=theme["BG"]
)
title_label.pack(pady=(18, 5))

chat_frame = tk.Frame(root, bg=theme["FRAME_BG"], bd=2, relief="groove", highlightbackground=theme["BORDER"], highlightcolor=theme["BORDER"])
chat_frame.pack(padx=15, pady=5, fill="both", expand=True)

chat_display = scrolledtext.ScrolledText(
    chat_frame, 
    wrap=tk.WORD, 
    width=54, 
    height=18, 
    font=("Segoe UI", 11), 
    bg=theme["ENTRY_BG"], 
    fg=theme["FG"], 
    bd=0, 
    relief="flat", 
    highlightthickness=0,
    insertbackground=theme["FG"]
)
chat_display.pack(padx=8, pady=8, fill="both", expand=True)

command_frame = tk.Frame(root, bg=theme["BG"])
command_frame.pack(pady=(5, 10))

command_entry = tk.Entry(
    command_frame, 
    width=38, 
    font=("Segoe UI", 11), 
    bg=theme["ENTRY_BG"], 
    fg=theme["FG"], 
    bd=1, 
    relief="solid", 
    highlightthickness=1, 
    highlightbackground=theme["BORDER"]
)
command_entry.pack(side=tk.LEFT, padx=5, ipady=4)
command_entry.bind('<Return>', lambda event: process_command_entry(command_entry))

execute_button = tk.Button(
    command_frame, 
    text="Enviar", 
    command=lambda: process_command_entry(command_entry),
    font=("Segoe UI", 10, "bold"),
    bg=theme["BTN_BG"], 
    fg=theme["BTN_FG"], 
    activebackground=theme["BTN_BG_HOVER"], 
    activeforeground=theme["BTN_FG_HOVER"], 
    bd=0, 
    relief="flat", 
    cursor="hand2"
)
execute_button.pack(side=tk.LEFT, padx=5, ipadx=10, ipady=3)

buttons_frame = tk.Frame(root, bg=theme["BG"])
buttons_frame.pack(pady=5)

minimize_button = tk.Button(
    buttons_frame, 
    text="Minimizar", 
    command=minimize_to_tray,
    font=("Segoe UI", 10, "bold"),
    bg=theme["BTN_BG"], 
    fg=theme["BTN_FG"], 
    activebackground=theme["BTN_BG_HOVER"], 
    activeforeground=theme["BTN_FG_HOVER"], 
    bd=0, 
    relief="flat", 
    cursor="hand2"
)
minimize_button.pack(side=tk.LEFT, padx=8, ipadx=10, ipady=3)

apps_button = tk.Button(
    buttons_frame, 
    text="Apps", 
    command=show_apps_window,
    font=("Segoe UI", 10, "bold"),
    bg=theme["BTN_BG"], 
    fg=theme["BTN_FG"], 
    activebackground=theme["BTN_BG_HOVER"], 
    activeforeground=theme["BTN_FG_HOVER"], 
    bd=0, 
    relief="flat", 
    cursor="hand2"
)
apps_button.pack(side=tk.LEFT, padx=8, ipadx=10, ipady=3)

options_button = tk.Button(
    buttons_frame, 
    text="Opciones", 
    command=show_options_window,
    font=("Segoe UI", 10, "bold"),
    bg=theme["BTN_BG"], 
    fg=theme["BTN_FG"], 
    activebackground=theme["BTN_BG_HOVER"], 
    activeforeground=theme["BTN_FG_HOVER"], 
    bd=0, 
    relief="flat", 
    cursor="hand2"
)
options_button.pack(side=tk.LEFT, padx=8, ipadx=10, ipady=3, fill="x", expand=True)

apply_theme(theme_name)

options = load_options()
if options["StartMinimized"] == "True":
    root.after(2000, minimize_to_tray)
else:
    root.after(2000, lambda: root.deiconify())

root.update_idletasks()

def update_chat_display(text):
    chat_display.insert(tk.END, text + "\n")
    chat_display.see(tk.END)

def main():
    sys.excepthook = handle_unhandled_exception
    # Arranca el servidor Flask en un hilo
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    escucha_thread = threading.Thread(target=listen, daemon=True)
    escucha_thread.start()
    root.mainloop()


if __name__ == "__main__":
    main()
