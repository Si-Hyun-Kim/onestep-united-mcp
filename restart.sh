#!/bin/bash
# restart.sh - 서비스 재시작

echo "🔄 재시작 중..."
./stop.sh
sleep 2
./start.sh
