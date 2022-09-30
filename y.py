from pykern import pksubprocess

pksubprocess.check_call_with_signals(
    ["python", "x.py"],
    output="res.txt",
)

