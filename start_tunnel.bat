@echo off
:start
echo Starting SSH Tunnel... [Local:8000 -> Public:8081]
ssh -o "ExitOnForwardFailure yes" -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" -N -R 0.0.0.0:8081:127.0.0.1:8000 root@47.93.45.198
echo Connection dropped, reconnecting in 5 seconds...
timeout /t 5
goto start
