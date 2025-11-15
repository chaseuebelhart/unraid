# Python Virtual Environment Setup

1. Create a virtual environment (run in project root):
   
   ```powershell
   python -m venv venv
   ```

2. Activate the virtual environment:
   
   - **Windows (PowerShell):**
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - **Windows (cmd):**
     ```cmd
     .\venv\Scripts\activate.bat
     ```
   - **macOS/Linux:**
     ```bash
     source venv/bin/activate
     ```

3. Install dependencies:
   
   ```powershell
   pip install -r requirements.txt
   ```

4. Deactivate when done:
   
   ```powershell
   deactivate
   ```

---

For more info, see the official Python docs: https://docs.python.org/3/library/venv.html
