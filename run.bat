@echo off
REM Provability Fabric Testbed - Windows Batch Commands
REM Usage: run.bat [command]

if "%1"=="" (
    echo.
    echo Provability Fabric Testbed - Available Commands:
    echo.
    echo Quick Commands:
    echo   up          - Start all services
    echo   down        - Stop all services
    echo   logs        - View service logs
    echo   status      - Show service status
    echo   test        - Run all tests
    echo   report      - Generate reports
    echo   clean       - Clean build artifacts
    echo.
    echo Development:
    echo   dev         - Start development environment
    echo   build       - Build TypeScript components
    echo   lint        - Run linting
    echo   format      - Format code
    echo.
    echo Docker:
    echo   docker:build - Build Docker images
    echo   docker:run   - Run with Docker Compose
    echo   docker:stop  - Stop Docker services
    echo.
    echo Examples:
    echo   run.bat up
    echo   run.bat test
    echo   run.bat logs
    echo.
    exit /b 1
)

if "%1"=="up" (
    echo Starting all services...
    docker-compose up -d
    echo.
    echo Services started! Access at:
    echo   - Testbed Gateway: http://localhost:3003
    echo   - Self-Serve Ingress: http://localhost:3001
    echo   - Grafana Dashboard: http://localhost:3100
    echo   - Prometheus Metrics: http://localhost:9090
    echo   - Ledger Service: http://localhost:3002
    echo.
    echo To view logs: run.bat logs
    echo To stop services: run.bat down
    goto :eof
)

if "%1"=="down" (
    echo Stopping all services...
    docker-compose down
    echo Services stopped.
    goto :eof
)

if "%1"=="logs" (
    echo Viewing service logs (Ctrl+C to exit)...
    docker-compose logs -f
    goto :eof
)

if "%1"=="status" (
    echo Service Status:
    docker-compose ps
    echo.
    echo Health Checks:
    echo Checking Gateway...
    curl -s http://localhost:3003/health >nul 2>&1 && echo   Gateway: OK || echo   Gateway: DOWN
    echo Checking Ingress...
    curl -s http://localhost:3001/health >nul 2>&1 && echo   Ingress: OK || echo   Ingress: DOWN
    echo Checking Ledger...
    curl -s http://localhost:3002/health >nul 2>&1 && echo   Ledger: OK || echo   Ledger: DOWN
    echo Checking Grafana...
    curl -s http://localhost:3100/api/health >nul 2>&1 && echo   Grafana: OK || echo   Grafana: DOWN
    echo Checking Prometheus...
    curl -s http://localhost:9090/-/healthy >nul 2>&1 && echo   Prometheus: OK || echo   Prometheus: DOWN
    goto :eof
)

if "%1"=="test" (
    echo Running all tests...
    npm test
    echo.
    echo Running Python tests...
    pytest testbed/tools/reporter/
    echo.
    echo Tests completed!
    goto :eof
)

if "%1"=="report" (
    echo Generating testbed report...
    npm run report:generate
    echo.
    echo Report generated! Check the reports/ directory.
    goto :eof
)

if "%1"=="clean" (
    echo Cleaning build artifacts...
    npm run clean
    echo Cleanup completed!
    goto :eof
)

if "%1"=="dev" (
    echo Starting development environment...
    npm run dev
    goto :eof
)

if "%1"=="build" (
    echo Building TypeScript components...
    npm run build
    echo Build completed!
    goto :eof
)

if "%1"=="lint" (
    echo Running linting...
    npm run lint
    echo Linting completed!
    goto :eof
)

if "%1"=="format" (
    echo Formatting code...
    npm run format
    echo Formatting completed!
    goto :eof
)

if "%1"=="docker:build" (
    echo Building Docker images...
    npm run docker:build
    echo Docker build completed!
    goto :eof
)

if "%1"=="docker:run" (
    echo Starting Docker services...
    npm run docker:run
    echo Docker services started!
    goto :eof
)

if "%1"=="docker:stop" (
    echo Stopping Docker services...
    npm run docker:stop
    echo Docker services stopped!
    goto :eof
)

echo Unknown command: %1
echo Run 'run.bat' without arguments to see available commands.
exit /b 1
