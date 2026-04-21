$env:CALLSUP_INTELLIGENCE_ENGINE_LLM_ADAPTER_URL = 'http://127.0.0.1:9100'
$env:CALLSUP_INTELLIGENCE_ENGINE_MODEL           = 'gpt-4o'
$env:PYTHONPATH                                  = 'src'
Set-Location 'C:\Users\nyaga\Documents\callsup\consolidated\callsup-intelligence-engine'
& 'C:\Users\nyaga\Documents\.venv\Scripts\python.exe' -m uvicorn 'callsup_intelligence_engine.main:create_app' --factory --host 127.0.0.1 --port 8011
Read-Host 'Press Enter to close'
