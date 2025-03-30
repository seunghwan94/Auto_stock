#!/bin/bash

echo "🧠 [start.sh] 실행 시작"

# 가상환경 활성화
source ~/StockAuto/venv/bin/activate

# ENV, LIVE_MODE 설정된 상태로 main.py 실행
echo "ENV=$ENV"
echo "LIVE_MODE=$LIVE_MODE"
echo "📦 현재 디렉토리: $(pwd)"

# 로그 파일 백업
mkdir -p logs
timestamp=$(date +"%Y%m%d_%H%M%S")
cp logs/app.log logs/app_$timestamp.log 2>/dev/null

# 백그라운드 실행 (nohup)
nohup python3 main.py >> logs/app.log 2>&1 &

echo "✅ [start.sh] main.py 백그라운드 실행 완료"
