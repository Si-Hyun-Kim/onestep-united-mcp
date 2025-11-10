# vulnerable_app/start_vulnerable_server.sh
#!/bin/bash
# 취약한 서버 시작 스크립트

echo "⚠️  Starting Vulnerable Web Application"
echo "========================================="
echo ""
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:5000"
echo ""
echo "WARNING: This server is intentionally vulnerable!"
echo "Do NOT expose to the internet!"
echo ""

# 백엔드 시작 (5000번 포트)
cd backend
python3 server.py &
BACKEND_PID=$!

# 프론트엔드 시작 (3000번 포트)
cd ../frontend
python3 -m http.server 3000 &
FRONTEND_PID=$!

echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "Press Ctrl+C to stop both servers"

# Ctrl+C 핸들러
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT

wait