Set-Location 'C:\Users\nyaga\Documents\callsup\svc-llm-adapter'
& 'C:\Users\nyaga\Documents\.venv\Scripts\python.exe' -m uvicorn main:app --host 127.0.0.1 --port 9100
Read-Host 'Press Enter to close'
