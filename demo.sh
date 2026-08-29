#!/usr/bin/env bash
set -euo pipefail
command -v jq >/dev/null || { echo "jq is required: https://jqlang.github.io/jq/"; exit 1; }
BASE_URL="${1:-https://nikhil-webhook-relay.fly.dev}"
DEST="https://httpbin.org/post"
curl -s "$BASE_URL"/health >/dev/null
source_response=$(curl -s -X POST "$BASE_URL/sources" -H "Content-Type: application/json" -d '{"name": "demo"}')
token=$(echo "$source_response" | jq -r '.token')
webhook_response=$(curl -s -X POST "$BASE_URL/in/$token" -H "Content-Type: application/json" -d '{"event": "user.created", "id": 42}')
event_id=$(echo "$webhook_response" | jq -r '.event_id')
replay_request_response=$(curl -s -X POST "$BASE_URL/events/$event_id/replay" -H "Content-Type: application/json" -d "{\"destination_url\": \"$DEST\"}")
job_id=$(echo "$replay_request_response" | jq -r '.job_id')
echo "Waiting for the worker to deliver..."
for i in $(seq 1 15); do
    attempts=$(curl -s "$BASE_URL/events/$event_id/attempts")
    count=$(echo "$attempts" | jq 'length')
    if [ "$count" -gt 0 ]; then
        break
    fi
    sleep 1
done

if [ "$count" -eq 0 ]; then
    echo "No delivery attempt recorded after 15s — is the worker running?"
    exit 1
fi

echo "$attempts" | jq .