#!/bin/bash
# stop_all.sh - 모든 서비스 정지

echo "🛑 Stopping AI Security System..."
echo ""

if [ -d ".pids" ]; then
    for pidfile in .pids/*.pid; do
        if [ -f "$pidfile" ]; then
            PID=$(cat "$pidfile")
            SERVICE=$(basename "$pidfile" .pid)
            
            if kill -0 $PID 2>/dev/null; then
                echo "  Stopping $SERVICE (PID: $PID)..."
                kill $PID
                rm "$pidfile"
            else
                echo "  $SERVICE not running"
                rm "$pidfile"
            fi
        fi
    done
fi

echo ""
echo "✅ All services stopped"
