from pykern import pksubprocess

def run():
    pksubprocess.check_call_with_signals(["python", "x.py"], output="o.txt")