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

# Ensure the script is running in the correct directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def delete_mp3_files():
    for file in os.listdir():
        if file.endswith(".mp3"):
            os.remove(file)

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
    with open('apps.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Nombre", "Ruta"])

def load_apps():
    apps = {}
    if not os.path.exists('apps.csv'):
        create_default_apps_csv()
    with open('apps.csv', mode='r', newline='') as file:
        reader = csv.reader(file)
        for row in reader:
            if len(row) == 2:
                apps[row[0].lower()] = [row[1]]
    return apps

def save_apps():
    with open('apps.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        for app, path in apps.items():
            writer.writerow([app, path[0]])

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

def save_options(llama_model, whisper_model, start_minimized):
    with open('options.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["LlamaModel", llama_model])
        writer.writerow(["WhisperModel", whisper_model])
        writer.writerow(["StartMinimized", start_minimized])

def load_options():
    options = {"LlamaModel": "llama3.2", "WhisperModel": "small", "StartMinimized": "False"}
    if os.path.exists('options.csv'):
        with open('options.csv', mode='r', newline='') as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) == 2:
                    options[row[0]] = row[1]
    return options

def show_options_window():
    options_window = Toplevel(root)
    options_window.title("Options")
    options_window.geometry("400x250")

    options = load_options()

    tk.Label(options_window, text="oLlama Model:").pack(pady=5)
    llama_model_var = tk.StringVar(options_window)
    llama_model_var.set(options["LlamaModel"])
    llama_model_menu = tk.OptionMenu(options_window, llama_model_var, "llama3.2:3b", "llama3.2:1b", "deepseek-r1:1.5b", "gemma2:2b", "phi3:3.8b", "qwen:0.5b", "qwen:1.8b", "qwen:4b", "granite3.1-moe:3b", "granite3.1-moe:1b")
    llama_model_menu.pack(pady=5)

    tk.Label(options_window, text="Whisper Model:").pack(pady=5)
    whisper_model_var = tk.StringVar(options_window)
    whisper_model_var.set(options["WhisperModel"])
    whisper_model_menu = tk.OptionMenu(options_window, whisper_model_var, "tiny", "base", "small", "medium", "large", "turbo")
    whisper_model_menu.pack(pady=5)

    start_minimized_var = tk.BooleanVar(options_window)
    start_minimized_var.set(options["StartMinimized"] == "True")
    tk.Checkbutton(options_window, text="Start Minimized to Tray", variable=start_minimized_var).pack(pady=5)

    def save_and_close():
        save_options(llama_model_var.get(), whisper_model_var.get(), start_minimized_var.get())
        options_window.destroy()
        messagebox.showinfo("Restart Required", "Para que surja efecto, vuelve a abrir el programa.")
        cerrar_programa()

    tk.Button(options_window, text="Save", command=save_and_close).pack(pady=10)

temp_file = NamedTemporaryFile().name
transcription = ['']
options = load_options()
llama_model = options["LlamaModel"]
whisper_model = options["WhisperModel"]
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
    with open(f"{filename}.{extension}", "w", encoding="utf-8") as file:
        file.write(data)

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

            transcription_thread = threading.Thread(target=lambda: transcribe_audio(temp_file))
            transcription_thread.start()
            transcription_thread.join()

            text = transcribe_audio(temp_file)

            if phrase_complete:
                transcription.append(text)
            else:
                transcription[-1] = text

            if any(word in transcription[-1].lower() for word in wake_word):
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

def transcribe_audio(temp_file):
    result = audio_model.transcribe(temp_file, language='es')
    return result['text'].strip()

def write_transcript():
    for line in transcription:
        write_file(line, "transcript", "txt")

def accion(texto):
    respuesta = ""
    if "abre" in texto:
        for app, path in apps.items():
            if app in texto:
                subprocess.Popen(path, creationflags=subprocess.CREATE_NO_WINDOW)
                respuesta = f"Abro {app}"
                break
        else:
            respuesta = "No se que abrir"
    elif "bloqueate" in texto:
        ctypes.windll.user32.LockWorkStation()
        respuesta = "Hasta Luego"
    elif "adiós" in texto:
        t = threading.Thread(name='adios', target=cerrar_programa)
        t.daemon = True
        t.start()
        respuesta = "Adios"
    elif "callate" in texto or "cállate" in texto:
        stop_audio()
        respuesta = "Me callo"
    elif "modo callado" in texto:
        global callado
        callado = not callado
        respuesta = "Modo callado activado" if callado else "Modo callado desactivado"
        tts(respuesta)
    elif "pausa canción" in texto or "pausa música" in texto or "pausa cancion" in texto or "pausa musica" in texto:
        keyboard.send("play/pause media")
        respuesta = "Pausando reproducción"
    elif "reproduce canción" in texto or "reproduce música" in texto or "reproduce cancion" in texto or "reproduce musica" in texto:
        keyboard.send("play/pause media")
        respuesta = "Reproduciendo"
    elif "siguiente canción" in texto or "siguiente música" in texto or "siguiente cancion" in texto or "siguiente musica" in texto:
        keyboard.send("next track")
        respuesta = "Siguiente canción"
    elif "anterior canción" in texto or "anterior música" in texto or "anterior cancion" in texto or "anterior musica" in texto:
        keyboard.send("previous track")
        keyboard.send("previous track")
        respuesta = "Canción anterior"
    elif "duermete" in texto or "apagate" in texto or "duérmete" in texto or "apágate" in texto:
        os.system("shutdown /s /t 1")
        respuesta = "Apagando"
    else:
        respuesta = chat_bot(texto)
    return respuesta

def remove_think_tags(text):
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

def chat_bot(texto):
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

def tts(texto):
    filename = generate_audio_file(texto)
    play_audio_threaded(filename)

def generate_audio_file(texto):
    tts = gtts.gTTS(texto, lang='es')
    unique_filename = f'audio_{uuid.uuid4()}.mp3'
    tts.save(unique_filename)
    return unique_filename

def play_audio_threaded(filename):
    stop_audio_event.clear()
    audio_thread = threading.Thread(target=play_audio, args=(filename,))
    audio_thread.start()

def play_audio(filename):
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        if stop_audio_event.is_set():
            pygame.mixer.music.stop()
            break
        pygame.time.Clock().tick(10)
    pygame.mixer.music.unload()

def stop_audio():
    if audio_thread and audio_thread.is_alive():
        stop_audio_event.set()
        audio_thread.join()

def cerrar_programa():
    time.sleep(2)
    subprocess.Popen(["ollama", "stop", llama_model], creationflags=subprocess.CREATE_NO_WINDOW)
    os._exit(0)

# Initialize the GUI
root = tk.Tk()
root.withdraw()  # Hide the window initially

# Set the size of the main window
root.geometry("500x400")

# Set the title and icon of the main window
root.title("Chatbot Interface")
icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'logo.ico'))
root.iconbitmap(icon_path)

# Set the taskbar icon
set_taskbar_icon(root)

# Create a scrolled text widget for displaying the chat
chat_display = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=50, height=20)
chat_display.pack(padx=10, pady=10)

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
    threading.Thread(target=listen, daemon=True).start()
    root.mainloop()

if __name__ == "__main__":
    main()
