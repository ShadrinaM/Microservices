#!/usr/bin/env bash
# Простая утилита: для каждого CronJob берёт последний Job (по label cronjob-name) и выводит логи первого Pod'а.
NAMESPACE="user-platform-exam"
CRONJOBS=(daily-stats-collector notification-sender data-cleanup)

for cj in "${CRONJOBS[@]}"; do
  echo "===== ${cj} ====="
  latest_job=$(kubectl get jobs -n "$NAMESPACE" -o jsonpath="{.items[?(@.metadata.labels['cronjob-name']=='${cj}')].metadata.name}" | awk '{print $NF}')
  if [ -z "$latest_job" ]; then
    echo "No jobs found for ${cj}"
    echo
    continue
  fi
  pod=$(kubectl get pods -n "$NAMESPACE" -l job-name="$latest_job" -o jsonpath="{.items[0].metadata.name}")
  if [ -z "$pod" ]; then
    echo "No pod found for job ${latest_job}"
    echo
    continue
  fi
  echo "Job: $latest_job  Pod: $pod"
  kubectl logs -n "$NAMESPACE" "$pod"
  echo
done