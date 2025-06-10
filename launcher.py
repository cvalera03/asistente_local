import subprocess
import os
import sys

script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main.py')
startupinfo = subprocess.STARTUPINFO()
startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

subprocess.Popen([sys.executable, script_path], startupinfo=startupinfo)
#subprocess.Popen([sys.executable, script_path], startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW)