@echo off
chcp 65001 > nul
title Тестирование Auth-Service
color 0A

echo ====================================================
echo         ТЕСТИРОВАНИЕ AUTH-SERVICE MICROSERVICE
echo ====================================================
echo.

REM Проверяем, установлен ли curl
where curl >nul 2>nul
if errorlevel 1 (
    echo ОШИБКА: curl не найден в системе!
    echo Установите curl или используйте PowerShell
    echo Скачать: https://curl.se/windows/
    pause
    exit /b 1
)

REM Проверяем, запущен ли port-forward
echo Проверяем порт 8080...
netstat -an | findstr ":8080" > nul
if errorlevel 1 (
    echo ПРЕДУПРЕЖДЕНИЕ: Port-forward не запущен.
    echo.
    echo Запустите в ДРУГОМ окне CMD/PowerShell:
    echo kubectl port-forward -n user-platform-exam service/auth-service 8080:80
    echo.
    echo Затем вернитесь сюда и нажмите любую клавишу для продолжения...
    pause
)

echo.
echo ============ ТЕСТ 1: Health Checks ============
echo.

echo 1.1 Тестируем /health/live...
curl -s -w "HTTP код: %%{http_code}\n" http://localhost:8080/health/live
echo.

echo 1.2 Тестируем /health/ready...
curl -s -w "HTTP код: %%{http_code}\n" http://localhost:8080/health/ready
echo.

echo ============ ТЕСТ 2: Config UI ============
echo.

echo 2. Тестируем /api/config...
curl -s http://localhost:8080/api/config
echo.

echo ============ ТЕСТ 3: Регистрация ============
echo.

echo 3.1 Регистрация пользователя student1...
curl -s -X POST http://localhost:8080/api/register ^
  -H "Content-Type: application/json" ^
  -d "{\"username\": \"student1\", \"password\": \"password123\"}"
echo.

echo 3.2 Регистрация пользователя student2 с email...
curl -s -X POST http://localhost:8080/api/register ^
  -H "Content-Type: application/json" ^
  -d "{\"username\": \"student2\", \"password\": \"password456\", \"email\": \"student2@example.com\"}"
echo.

echo ============ ТЕСТ 4: Логин ============
echo.

echo 4.1 Логин student2...
set "LOGIN_RESPONSE="
for /f "delims=" %%i in ('curl -s -X POST http://localhost:8080/api/login ^
  -H "Content-Type: application/json" ^
  -d "{\"username\": \"student2\", \"password\": \"password456\"}"') do (
    set "LOGIN_RESPONSE=%%i"
    echo %%i
)
echo.

REM Извлекаем токен из JSON ответа
echo 4.2 Извлекаем токен из ответа...
if defined LOGIN_RESPONSE (
    REM Простой парсинг JSON для получения токена
    set "JSON_RESPONSE=%LOGIN_RESPONSE%"
    set "JSON_RESPONSE=%JSON_RESPONSE:{"=%"
    set "JSON_RESPONSE=%JSON_RESPONSE:}"=%"
    
    REM Ищем токен в ответе
    set "TOKEN="
    for %%a in (%JSON_RESPONSE%) do (
        set "PAIR=%%a"
        if "!PAIR:~0,7!"=="token:" (
            set "TOKEN=!PAIR:~7!"
            set "TOKEN=!TOKEN:"=!"
            set "TOKEN=!TOKEN:,=!"
        )
    )
    
    if defined TOKEN (
        echo Токен получен: !TOKEN:~0,30!...
        echo Токен сохранен в переменной TOKEN
    ) else (
        echo Не удалось извлечь токен из ответа
        echo Создаем тестового пользователя для валидации...
        
        curl -s -X POST http://localhost:8080/api/register ^
          -H "Content-Type: application/json" ^
          -d "{\"username\": \"testuser\", \"password\": \"testpass\"}"
        echo.
        
        for /f "delims=" %%j in ('curl -s -X POST http://localhost:8080/api/login ^
          -H "Content-Type: application/json" ^
          -d "{\"username\": \"testuser\", \"password\": \"testpass\"}"') do (
            set "LOGIN2=%%j"
            echo %%j
        )
        
        REM Парсим токен из второго ответа
        set "LOGIN2=!LOGIN2:{"=!"
        set "LOGIN2=!LOGIN2:}"=!"
        for %%b in (!LOGIN2!) do (
            set "PAIR2=%%b"
            if "!PAIR2:~0,7!"=="token:" (
                set "TOKEN=!PAIR2:~7!"
                set "TOKEN=!TOKEN:"=!"
                set "TOKEN=!TOKEN:,=!"
            )
        )
        
        if defined TOKEN (
            echo Токен получен: !TOKEN:~0,30!...
        )
    )
) else (
    echo Ошибка при логине
)

echo.
echo ============ ТЕСТ 5: Валидация токена ============
echo.

if defined TOKEN (
    echo 5.1 Тестируем /api/validate с токеном...
    curl -s -H "Authorization: Bearer !TOKEN!" http://localhost:8080/api/validate
    echo.
    
    echo 5.2 Тестируем неверный токен...
    curl -s -H "Authorization: Bearer invalid_token_123" http://localhost:8080/api/validate
    echo.
    
    echo 5.3 Тестируем без токена...
    curl -s http://localhost:8080/api/validate
    echo.
) else (
    echo ПРОПУСК: Не удалось получить токен для теста валидации
)

echo.
echo ============ ТЕСТ 6: Дополнительные тесты ============
echo.

echo 6.1 Попытка повторной регистрации (должна быть ошибка)...
curl -s -X POST http://localhost:8080/api/register ^
  -H "Content-Type: application/json" ^
  -d "{\"username\": \"student1\", \"password\": \"password123\"}"
echo.

echo 6.2 Неверный логин...
curl -s -X POST http://localhost:8080/api/login ^
  -H "Content-Type: application/json" ^
  -d "{\"username\": \"nonexistent\", \"password\": \"wrong\"}"
echo.

echo.
echo ====================================================
echo                  РЕЗЮМЕ ТЕСТИРОВАНИЯ
echo ====================================================
echo.
echo Все тесты выполнены!
echo.
echo Для ручного тестирования можете использовать:
echo.
echo 1. Проверка health:
echo    curl http://localhost:8080/health/live
echo    curl http://localhost:8080/health/ready
echo.
echo 2. Проверка конфигурации:
echo    curl http://localhost:8080/api/config
echo.
echo 3. Создание нового пользователя:
echo    curl -X POST http://localhost:8080/api/register ^
echo      -H "Content-Type: application/json" ^
echo      -d "{\"username\": \"newuser\", \"password\": \"pass123\"}"
echo.
echo 4. Вход с существующим пользователем:
echo    curl -X POST http://localhost:8080/api/login ^
echo      -H "Content-Type: application/json" ^
echo      -d "{\"username\": \"student1\", \"password\": \"password123\"}"
echo.
if defined TOKEN (
    echo 5. Валидация токена:
    echo    curl -H "Authorization: Bearer !TOKEN!" http://localhost:8080/api/validate
)
echo.
echo ====================================================
pause