@echo off
echo Starting Secure Messenger...
start "" http://localhost:8000
uvicorn server.main:app --reload
