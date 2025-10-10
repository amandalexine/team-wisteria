import subprocess

def execute_command():
    ''' This function will try to open the entire program to begin testing'''
    try:
        result = subprocess.Popen('python gui_test.py', shell=True, text=True)
    except Exception as e:
        print(e)

execute_command()
