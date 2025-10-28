#!/bin/bash
# restart_all.sh - 모든 서비스 재시작

echo "🔄 Restarting AI Security System..."
echo ""

./stop_all.sh
sleep 3
./start_all.sh