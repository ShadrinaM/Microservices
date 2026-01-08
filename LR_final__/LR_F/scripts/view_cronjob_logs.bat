@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM Простая утилита для Windows: для каждого CronJob берёт последний Job и выводит логи первого Pod'а
set "NAMESPACE=user-platform-exam"
set "CRONJOBS=daily-stats-collector notification-sender data-cleanup"

echo =========================================
echo    Мониторинг CronJob - Windows версия
echo =========================================
echo.

REM Проверяем, установлен ли kubectl
where kubectl >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: kubectl не найден в PATH!
    echo Установите kubectl и добавьте его в переменную окружения PATH.
    pause
    exit /b 1
)

REM Проверяем подключение к кластеру
kubectl cluster-info >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Не удалось подключиться к кластеру Kubernetes!
    echo Убедитесь, что kubectl настроен правильно.
    pause
    exit /b 1
)

for %%C in (%CRONJOBS%) do (
    echo ===== %%C =====
    
    REM Получаем последний Job для CronJob
    for /f "tokens=*" %%J in ('kubectl get jobs -n "%NAMESPACE%" -o jsonpath^="{.items[?(@.metadata.labels['cronjob-name']^=='%%C')].metadata.name}" 2^>nul') do (
        set "latest_job=%%J"
    )
    
    if "!latest_job!"=="" (
        echo Нет запусков для %%C
        echo.
        goto :next_cronjob
    )
    
    REM Получаем Pod для этого Job
    for /f "tokens=*" %%P in ('kubectl get pods -n "%NAMESPACE%" -l job-name^="!latest_job!" -o jsonpath^="{.items[0].metadata.name}" 2^>nul') do (
        set "pod=%%P"
    )
    
    if "!pod!"=="" (
        echo Не найден Pod для Job: !latest_job!
        echo.
        goto :next_cronjob
    )
    
    echo Job: !latest_job!  Pod: !pod!
    echo -------------------------
    
    REM Получаем логи Pod'а
    kubectl logs -n "%NAMESPACE%" "!pod!"
    
    :next_cronjob
    echo.
)

echo =========================================
echo    Проверка завершена
echo =========================================

REM Дополнительная информация о статусе CronJob
echo.
echo Дополнительная информация:
echo -------------------------
kubectl get cronjobs -n "%NAMESPACE%"
echo.
kubectl get jobs -n "%NAMESPACE%" --sort-by=.metadata.creationTimestamp

pause