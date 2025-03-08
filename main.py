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
import re
import requests
import sys
import traceback
import google.generativeai as genai 


# Ensure the script is running in the correct directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    error_message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(error_message)  # Print the traceback to the console for debugging
    messagebox.showerror("Unhandled Error", f"An unhandled error has occurred:\n\n{error_message}\n\nThe program will now close.")
    cerrar_programa()



def delete_mp3_files():
    try:
        for file in os.listdir():
            if file.endswith(".mp3"):
                os.remove(file)
    except OSError as e:
        print(f"Error al eliminar archivos mp3: {e}")
    except Exception as e:
        print(f"Error inesperado al eliminar archivos mp3: {e}")

delete_mp3_files()  # Call the function to delete .mp3 files at the start

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
        
def create_default_apps_csv():
    try:
        with open('apps.csv', mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Nombre", "Ruta"])
    except OSError as e:
        print(f"Error al crear apps.csv: {e}")
        messagebox.showerror("Error", f"No se pudo crear el archivo apps.csv: {e}")
    except Exception as e:
        print(f"Error inesperado al crear apps.csv: {e}")
        messagebox.showerror("Error", f"Error inesperado al crear apps.csv: {e}")

def load_apps():
    apps = {}
    try:
        if not os.path.exists('apps.csv'):
            create_default_apps_csv()
        with open('apps.csv', mode='r', newline='') as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) == 2:
                    apps[row[0].lower()] = [row[1]]
    except FileNotFoundError as e:
        print(f"Error: No se encontró el archivo apps.csv: {e}")
        messagebox.showerror("Error", f"No se encontró el archivo apps.csv: {e}")
    except csv.Error as e:
        print(f"Error al leer apps.csv: {e}")
        messagebox.showerror("Error", f"Error al leer apps.csv: {e}")
    except OSError as e:
        print(f"Error de sistema al cargar apps.csv: {e}")
        messagebox.showerror("Error", f"Error de sistema al cargar apps.csv: {e}")
    except Exception as e:
        print(f"Error inesperado al cargar apps: {e}")
        messagebox.showerror("Error", f"Error inesperado al cargar apps: {e}")
    return apps

def save_apps():
    try:
        with open('apps.csv', mode='w', newline='') as file:
            writer = csv.writer(file)
            for app, path in apps.items():
                writer.writerow([app, path[0]])
    except OSError as e:
        print(f"Error al guardar apps: {e}")
        messagebox.showerror("Error", f"Error al guardar apps: {e}")
    except csv.Error as e:
        print(f"Error al escribir apps.csv: {e}")
        messagebox.showerror("Error", f"Error al escribir apps.csv: {e}")
    except Exception as e:
        print(f"Error inesperado al guardar apps: {e}")
        messagebox.showerror("Error", f"Error inesperado al guardar apps: {e}")


def add_app():
    app_name = simpledialog.askstring("Add App", "Enter the app name:")
    app_path = simpledialog.askstring("Add App", "Enter the app path:")
    if app_name and app_path:
        apps[app_name.lower()] = [app_path]
        save_apps()
        update_apps_list()
        messagebox.showinfo("Success", f"App '{app_name}' added successfully!")

def edit_app():
    selected = apps_list.curselection()
    if selected:
        app_name = apps_list.get(selected).split()[0].strip().lower()
        new_app_name = simpledialog.askstring("Edit App", "Enter the new app name:", initialvalue=app_name)
        new_app_path = simpledialog.askstring("Edit App", "Enter the new app path:", initialvalue=apps[app_name][0])
        if new_app_name and new_app_path:
            del apps[app_name]
            apps[new_app_name.lower()] = [new_app_path]
            save_apps()
            update_apps_list()
            messagebox.showinfo("Success", f"App '{new_app_name}' updated successfully!")

def delete_app():
    selected = apps_list.curselection()
    if selected:
        app_name = apps_list.get(selected).split(":")[0].strip().lower()
        if messagebox.askyesno("Delete App", f"Are you sure you want to delete '{app_name}'?"):
            del apps[app_name]
            save_apps()
            update_apps_list()
            messagebox.showinfo("Success", f"App '{app_name}' deleted successfully!")

def update_apps_list():
    apps_list.delete(0, tk.END)
    for app, path in apps.items():
        apps_list.insert(tk.END, f"{app.upper():<20} {path[0]}")

def show_apps_window():
    apps_window = Toplevel(root)
    apps_window.title("Current Apps")
    apps_window.geometry("600x475")
    apps_list_label = tk.Label(apps_window, text="Current Apps:")
    apps_list_label.pack(pady=5)
    global apps_list
    apps_list = tk.Listbox(apps_window, width=60, height=20, font=("Courier", 10))
    apps_list.pack(padx=10, pady=10)
    update_apps_list()
    
    buttons_frame = tk.Frame(apps_window)
    buttons_frame.pack(pady=5)
    
    add_button = tk.Button(buttons_frame, text="Add App", command=add_app)
    add_button.pack(side=tk.LEFT, padx=5)
    edit_button = tk.Button(buttons_frame, text="Edit App", command=edit_app)
    edit_button.pack(side=tk.LEFT, padx=5)
    delete_button = tk.Button(buttons_frame, text="Delete App", command=delete_app)
    delete_button.pack(side=tk.LEFT, padx=5)

def set_taskbar_icon(root):
    # Load the icon
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo.ico')
    icon = Image.open(icon_path)
    
    # Convert the icon to a format that can be used by ctypes
    icon_data = icon.tobytes("raw", "BGRA")
    hicon = ctypes.windll.user32.CreateIconFromResourceEx(
        icon_data, len(icon_data), 1, 0x00030000, icon.width, icon.height, 0
    )
    
    # Set the icon for the taskbar
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("myappid")
    root.iconbitmap(icon_path)
    ctypes.windll.user32.SendMessageW(root.winfo_id(), 0x80, 1, hicon)

def save_options(model_type, llama_model, whisper_model, start_minimized, city, api_key, gemini_api_key):
    options = {
        "ModelType": model_type,
        "LlamaModel": llama_model,
        "WhisperModel": whisper_model,
        "StartMinimized": "True" if start_minimized else "False",
        "City": city,
        "APIKey": api_key,
        "GeminiAPIKey": gemini_api_key,
    }
    try:
        with open('options.csv', mode='w', newline='') as file:
            writer = csv.writer(file)
            for key, value in options.items():
                writer.writerow([key, value])
    except OSError as e:
        print(f"Error al guardar opciones: {e}")
        messagebox.showerror("Error", f"Error al guardar opciones: {e}")
    except csv.Error as e:
        print(f"Error al escribir options.csv: {e}")
        messagebox.showerror("Error", f"Error al escribir options.csv: {e}")
    except Exception as e:
        print(f"Error inesperado al guardar opciones: {e}")
        messagebox.showerror("Error", f"Error inesperado al guardar opciones: {e}")


def load_options():
    global genai
    options = {"ModelType": "local", "LlamaModel": "llama3.2", "WhisperModel": "small", "StartMinimized": "False", "City": "CITY", "APIKey": "API_KEY", "GeminiAPIKey": "GEMINI_API_KEY"}
    try:
        if os.path.exists('options.csv'):
            with open('options.csv', mode='r', newline='') as file:
                reader = csv.reader(file)
                for row in reader:
                    if len(row) == 2:
                        options[row[0]] = row[1]
        if options["ModelType"] == "gemini" and options["GeminiAPIKey"] != "GEMINI_API_KEY":
            genai.configure(api_key=options["GeminiAPIKey"])
    except FileNotFoundError as e:
        print(f"Error: No se encontró el archivo options.csv: {e}")
        messagebox.showerror("Error", f"No se encontró el archivo options.csv: {e}")
    except csv.Error as e:
        print(f"Error al leer options.csv: {e}")
        messagebox.showerror("Error", f"Error al leer options.csv: {e}")
    except OSError as e:
        print(f"Error de sistema al cargar options.csv: {e}")
        messagebox.showerror("Error", f"Error de sistema al cargar options.csv: {e}")
    except Exception as e:
        print(f"Error inesperado al cargar opciones: {e}")
        messagebox.showerror("Error", f"Error inesperado al cargar opciones: {e}")
    return options



def show_options_window():
    options_window = Toplevel(root)
    options_window.title("Options")
    options_window.geometry("400x500") #Se aumenta la ventana

    options = load_options()

    # --- Model Selection ---
    model_frame = tk.LabelFrame(options_window, text="Model Selection")
    model_frame.pack(pady=10, padx=10, fill="x")

    model_type_var = tk.StringVar(options_window)
    model_type_var.set(options["ModelType"])
    
    local_model_radio = tk.Radiobutton(model_frame, text="Local LLM (oLLama)", variable=model_type_var, value="local")
    local_model_radio.pack(anchor="w", padx=5)

    gemini_model_radio = tk.Radiobutton(model_frame, text="Gemini (API)", variable=model_type_var, value="gemini")
    gemini_model_radio.pack(anchor="w", padx=5)

    # --- oLlama Model Selection ---
    tk.Label(options_window, text="oLlama Model:").pack(pady=5)
    llama_model_var = tk.StringVar(options_window)
    llama_model_var.set(options["LlamaModel"])
    llama_model_menu = tk.OptionMenu(options_window, llama_model_var, "llama3.2:3b", "llama3.2:1b", "deepseek-r1:1.5b", "gemma2:2b", "phi3:3.8b", "qwen:0.5b", "qwen:1.8b", "qwen:4b", "granite3.1-moe:3b", "granite3.1-moe:1b")
    llama_model_menu.pack(pady=5)

    # --- Whisper Model Selection ---
    tk.Label(options_window, text="Whisper Model:").pack(pady=5)
    whisper_model_var = tk.StringVar(options_window)
    whisper_model_var.set(options["WhisperModel"])
    whisper_model_menu = tk.OptionMenu(options_window, whisper_model_var, "tiny", "base", "small", "medium", "large", "turbo")
    whisper_model_menu.pack(pady=5)

    # --- Other Options ---
    start_minimized_var = tk.BooleanVar(options_window)
    start_minimized_var.set(options["StartMinimized"] == "True")
    tk.Checkbutton(options_window, text="Start Minimized to Tray", variable=start_minimized_var).pack(pady=5)

    tk.Label(options_window, text="City:").pack(pady=5)
    city_var = tk.StringVar(options_window)
    city_var.set(options["City"])
    tk.Entry(options_window, textvariable=city_var).pack(pady=5)

    tk.Label(options_window, text="API Key:").pack(pady=5)
    api_key_var = tk.StringVar(options_window)
    api_key_var.set(options["APIKey"])
    tk.Entry(options_window, textvariable=api_key_var).pack(pady=5)

    tk.Label(options_window, text="Gemini API Key:").pack(pady=5)
    gemini_api_key_var = tk.StringVar(options_window)
    gemini_api_key_var.set(options["GeminiAPIKey"])
    tk.Entry(options_window, textvariable=gemini_api_key_var).pack(pady=5)

    def save_and_close():
        save_options(model_type_var.get(), llama_model_var.get(), whisper_model_var.get(), start_minimized_var.get(), city_var.get(), api_key_var.get(), gemini_api_key_var.get())
        options_window.destroy()
        messagebox.showinfo("Restart Required", "Para que surja efecto, vuelve a abrir el programa.")
        cerrar_programa()

    tk.Button(options_window, text="Save", command=save_and_close).pack(pady=10)


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
apps = load_apps()

def write_file(data, filename, extension):
    try:
        with open(f"{filename}.{extension}", "w", encoding="utf-8") as file:
            file.write(data)
    except OSError as e:
        print(f"Error al escribir el archivo {filename}.{extension}: {e}")
        messagebox.showerror("Error", f"Error al escribir el archivo {filename}.{extension}: {e}")
    except Exception as e:
        print(f"Error inesperado al escribir el archivo {filename}.{extension}: {e}")
        messagebox.showerror("Error", f"Error inesperado al escribir el archivo {filename}.{extension}: {e}")


def listen():
    phrase_time = None
    phrase_timeout = 2
    record_timeout = 10
    last_sample = bytes()
    source = sr.Microphone(sample_rate=16000)
    try:
        with source:
            recorder.adjust_for_ambient_noise(source)
            recorder.energy_threshold += 25

            def record_callback(_, audio: sr.AudioData):
                data = audio.get_raw_data()
                data_queue.put(data)

        recorder.listen_in_background(source, record_callback, phrase_time_limit=record_timeout)
        start = datetime.now()
        while True:
            now = datetime.now()
            if (now - start).total_seconds() % 18 == 0:
                write_transcript()
            if not data_queue.empty():
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
                        subprocess.Popen(["ollama", "stop", llama_model], creationflags=subprocess.CREATE_NO_WINDOW)
                        if not callado:
                            tts(respuesta)
                        update_chat_display(f"User: {mensaje}")
                        update_chat_display(f"Assistant: {respuesta}")
                    except Exception as e:
                        print(f"Error al procesar el comando: {e}")
                        messagebox.showerror("Error", f"Error al procesar el comando: {e}")
    except sr.UnknownValueError as e:
        print(f"No se pudo entender el audio: {e}")
    except sr.RequestError as e:
        print(f"Error de servicio de reconocimiento de voz: {e}")
        messagebox.showerror("Error", f"Error de servicio de reconocimiento de voz: {e}")
    except OSError as e:
        print(f"Error del sistema: {e}")
        messagebox.showerror("Error", f"Error del sistema: {e}")
    except Exception as e:
        print(f"Error inesperado en la escucha: {e}")
        messagebox.showerror("Error", f"Error inesperado en la escucha: {e}")

def transcribe_audio(temp_file):
    try:
        result = audio_model.transcribe(temp_file, language='es')
        return result['text'].strip()
    except Exception as e:
        print(f"Error al transcribir audio: {e}")
        messagebox.showerror("Error", f"Error al transcribir audio: {e}")
        return ""


def write_transcript():
    for line in transcription:
        write_file(line, "transcript", "txt")

def open_app(app_name):
    if app_name in apps:
        try:
            subprocess.Popen(apps[app_name][0], creationflags=subprocess.CREATE_NO_WINDOW)
            return f"Abro {app_name}"
        except FileNotFoundError:
            return f"No se encontró la ruta de {app_name}."
        except OSError:
            return f"No se pudo abrir {app_name}."
        except Exception as e:
            return f"Error al abrir {app_name}: {e}"
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
    return get_temperature()

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
    command_entry.delete(0, tk.END)  # Clear the entry field
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
    except Exception as e:
        print(f"Error al procesar el comando: {e}")
        messagebox.showerror("Error", f"Error al procesar el comando: {e}")

def chat_bot(texto):
    options = load_options()
    if options["ModelType"] == "local":
        try:
            chat_history.append({'role': 'user', 'content': texto})
            stream = chat(
                model=llama_model,
                messages=[
                    {"role": "system", "content": "Eres una asistenta y te llamas lumi pero te van a llamar de otras formas y no vas a mencionar que te llamen asi, hablas español"},
                    *chat_history
                ],
                stream=True,
            )
            response = "".join(chunk.message.content for chunk in stream)
            response = remove_think_tags(response)
            chat_history.append({'role': 'assistant', 'content': response})
            return response
        except Exception as e:
            print(f"Error al interactuar con el LLM: {e}")
            messagebox.showerror("Error", f"Error al interactuar con el LLM: {e}")
            return "Error al interactuar con el LLM"
    elif options["ModelType"] == "gemini":
        try:
            model = genai.GenerativeModel('gemini-2.0-flash-lite')
            chat_g = model.start_chat(history=[])
            response_g = chat_g.send_message(texto)
            return response_g.text
        except Exception as e:
            print(f"Error al interactuar con Gemini: {e}")
            messagebox.showerror("Error", f"Error al interactuar con Gemini: {e}")
            return "Error al interactuar con Gemini"

def tts(texto):
    try:
        filename = generate_audio_file(texto)
        play_audio_threaded(filename)
    except Exception as e:
        print(f"Error al generar o reproducir audio: {e}")
        messagebox.showerror("Error", f"Error al generar o reproducir audio: {e}")


def generate_audio_file(texto):
    try:
        tts = gtts.gTTS(texto, lang='es')
        unique_filename = f'audio_{uuid.uuid4()}.mp3'
        tts.save(unique_filename)
        return unique_filename
    except Exception as e:
        print(f"Error al generar el archivo de audio: {e}")
        messagebox.showerror("Error", f"Error al generar el archivo de audio: {e}")
        return None  # Indicate failure to generate audio


def play_audio_threaded(filename):
    if filename is None:
        print("No se ha generado ningún archivo de audio para reproducir.")
        return  # Don't try to play if there's no file

    stop_audio_event.clear()
    global audio_thread
    audio_thread = threading.Thread(target=play_audio, args=(filename,))
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
    except pygame.error as e:
        print(f"Error de Pygame al reproducir audio: {e}")
        messagebox.showerror("Error", f"Error de Pygame al reproducir audio: {e}")
    except Exception as e:
        print(f"Error inesperado al reproducir audio: {e}")
        messagebox.showerror("Error", f"Error inesperado al reproducir audio: {e}")


def stop_audio():
    global audio_thread
    if audio_thread and audio_thread.is_alive():
        stop_audio_event.set()
        audio_thread.join()


def cerrar_programa():
    try:
        time.sleep(2)
        subprocess.Popen(["ollama", "stop", llama_model], creationflags=subprocess.CREATE_NO_WINDOW)
        os._exit(0)
    except Exception as e:
        print(f"Error inesperado al cerrar el programa: {e}")
        messagebox.showerror("Error", f"Error inesperado al cerrar el programa: {e}")
        os._exit(1)


def get_temperature():
    url = f'http://api.openweathermap.org/data/2.5/weather?appid=' + api_key + '&q=' + city + '&units=metric&lang=es'
    try:
        response = requests.get(url, timeout=5)  # Timeout de 5 segundos
        response.raise_for_status()  # Lanza una excepción para códigos de error HTTP
        data = response.json()
        temp = data['main']['temp']
        description = data['weather'][0]['description']
        return f"El clima en {city} es {description} con una temperatura de {temp}°C"
    except requests.exceptions.Timeout as e:
        print(f"Tiempo de espera agotado: {e}")
        messagebox.showerror("Error", f"Tiempo de espera agotado: {e}")
        return "No se pudo obtener la temperatura (tiempo agotado)"
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener la temperatura: {e}")
        messagebox.showerror("Error", f"Error al obtener la temperatura: {e}")
        return "No se pudo obtener la temperatura"
    except KeyError as e:
        print(f"Error al procesar la respuesta del clima: {e}")
        messagebox.showerror("Error", f"Error al procesar la respuesta del clima: {e}")
        return "No se pudo obtener la temperatura"
    except Exception as e:
        print(f"Error inesperado al obtener la temperatura: {e}")
        messagebox.showerror("Error", f"Error inesperado al obtener la temperatura: {e}")
        return "No se pudo obtener la temperatura"


# Initialize the GUI
root = tk.Tk()
root.withdraw()  # Hide the window initially

# Set the size of the main window
root.geometry("500x450")

# Set the title and icon of the main window
root.title("Chatbot Interface")
icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'logo.ico'))
root.iconbitmap(icon_path)

# Set the taskbar icon
set_taskbar_icon(root)

# Create a scrolled text widget for displaying the chat
chat_display = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=50, height=20)
chat_display.pack(padx=10, pady=10)

# Add a frame for the command entry
command_frame = tk.Frame(root)
command_frame.pack(pady=10)

# Add an entry field for commands
command_entry = tk.Entry(command_frame, width=40)
command_entry.pack(side=tk.LEFT, padx=5)

command_entry.bind('<Return>', lambda event: process_command_entry(command_entry))

# Add a button to execute commands
execute_button = tk.Button(command_frame, text="Execute", command=lambda: process_command_entry(command_entry))
execute_button.pack(side=tk.LEFT, padx=5)

# Add a frame for buttons
buttons_frame = tk.Frame(root)
buttons_frame.pack(pady=10)

# Add a button to minimize to tray
minimize_button = tk.Button(buttons_frame, text="Minimize to Tray", command=minimize_to_tray)
minimize_button.pack(side=tk.LEFT, padx=5)

# Add a button to view and manage apps
apps_button = tk.Button(buttons_frame, text="Manage Apps", command=show_apps_window)
apps_button.pack(side=tk.LEFT, padx=5)

# Add a button to open options window
options_button = tk.Button(buttons_frame, text="Options", command=show_options_window)
options_button.pack(side=tk.LEFT, padx=5)

# Schedule the delayed start
options = load_options()
if options["StartMinimized"] == "True":
    root.after(2000, minimize_to_tray)  # Delay for 2000 milliseconds (2 seconds)
else:
    root.after(2000, lambda: root.deiconify())  # Delay for 2000 milliseconds (2 seconds)

# Force update the window to ensure all widgets are displayed correctly
root.update_idletasks()

def update_chat_display(text):
    chat_display.insert(tk.END, text + "\n")
    chat_display.see(tk.END)

def main():
    sys.excepthook = handle_unhandled_exception
    threading.Thread(target=listen, daemon=True).start()
    root.mainloop()

if __name__ == "__main__":
    main()
