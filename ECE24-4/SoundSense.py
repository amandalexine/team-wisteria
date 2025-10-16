import subprocess

def execute_command():
    try:
        result = subprocess.Popen('python gui_app.py', shell=True, text=True)
    except Exception as e:
        print(e)

execute_command()