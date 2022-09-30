import sys
import subprocess

# pksubprocess.check_call_with_signals(
#     ["python", "x.py"],
#     output=sys.stderr,
# )

sub = subprocess.Popen(
    ["python", "x.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)
output, error_output = sub.communicate()

assert error_output == b"this is a message"
