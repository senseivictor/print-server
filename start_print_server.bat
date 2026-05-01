@echo off
set PORT=5000

:: Verifică dacă portul este deja utilizat
netstat -ano | findstr :%PORT% | findstr LISTENING >nul
if %errorlevel% == 0 (
    echo Serverul ruleaza deja pe portul %PORT%. Nu se va porni o noua instanta.
    timeout /t 3
    exit /b
)

:: Dacă portul este liber, pornește serverul
cd /d "C:\Users\victo.DESKTOPPAV\Desktop\print_server"

:: Activăm mediul virtual și pornim python în mod "pythonw" (fără consolă)
:: Folosim start /b pentru a nu bloca scriptul bat
call ".venv\Scripts\activate"
start /b "" ".venv\Scripts\pythonw.exe" app.py

echo Serverul a fost pornit in background pe portul %PORT%.
timeout /t 3