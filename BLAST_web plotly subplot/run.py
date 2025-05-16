import sys
import os

# --- Python sys.path debugging: ---
# print("--- top of run.py: sys.path ---")
# for p_idx, p_val in enumerate(sys.path):
#     print(f"{p_idx}: {p_val}")
# print("-------------------------------")
# Check if the current directory is what we expect
# print(f"--- CWD in run.py: {os.getcwd()} ---")
# --- End sys.path debugging ---

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True) 