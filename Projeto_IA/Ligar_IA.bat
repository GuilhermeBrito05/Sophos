@echo off
:: Navega até a pasta onde está o script
cd /d "%~dp0"

:: Substitua o caminho abaixo pelo caminho que você copiou no 'where python'
"C:\Users\guilh\AppData\Local\Microsoft\WindowsApps\python.exe" -m streamlit run meu_chat.py

pause