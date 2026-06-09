#!/usr/bin/env bash
# Batched HCS10 gold-corpus amplifier.
#
# research_hcs10_amplify generates (target_count - current) gold responses in ONE
# call, so a big jump (e.g. 350->1000) exceeds the 600s tool budget and returns
# empty. This runner grows the corpus in SMALL increments so every call finishes
# inside the budget, looping until the final target (or a stall) is reached.
#
# Usage:  nohup bash scripts/hcs10_batch_amplify.sh [FINAL_TARGET] [STEP] &
# Author: Ahmed Adel Bakr Alderai
set -u
FINAL_TARGET=${1:-1000}
STEP=${2:-20}
LOG=${HCS10_LOG:-/tmp/hcs10_batch.log}
QDRANT=http://localhost:6333/collections/ummro_hcs10_responses
API=http://localhost:8788/api/v1/tools/research_hcs10_amplify

count() {
  curl -s -m 10 "$QDRANT" 2>/dev/null \
    | python3 -c 'import sys,json;print(json.load(sys.stdin).get("result",{}).get("points_count",0))' 2>/dev/null \
    || echo 0
}

echo "$(date '+%F %T') START target=$FINAL_TARGET step=$STEP" >> "$LOG"
stall=0
while : ; do
  cur=$(count)
  echo "$(date '+%F %T') current=$cur" >> "$LOG"
  if [ "$cur" -ge "$FINAL_TARGET" ]; then
    echo "$(date '+%F %T') DONE reached=$cur" >> "$LOG"; break
  fi
  tgt=$(( cur + STEP ))
  [ "$tgt" -gt "$FINAL_TARGET" ] && tgt=$FINAL_TARGET
  curl -s -m 580 -X POST "$API" -H 'Content-Type: application/json' \
    -d "{\"target_count\":$tgt}" >/dev/null 2>>"$LOG"
  new=$(count)
  if [ "$new" -le "$cur" ]; then
    stall=$(( stall + 1 ))
    echo "$(date '+%F %T') no-progress new=$new stall=$stall/3" >> "$LOG"
    if [ "$stall" -ge 3 ]; then
      echo "$(date '+%F %T') STOP 3 consecutive stalls (Groq quota or generation failures)" >> "$LOG"; break
    fi
    sleep 30
  else
    stall=0
    echo "$(date '+%F %T') +$(( new - cur )) -> $new" >> "$LOG"
  fi
done
echo "$(date '+%F %T') EXIT final=$(count)" >> "$LOG"
