@echo off
REM Provability Fabric Testbed - Windows Batch Commands

if "%1"=="" goto help
if "%1"=="up" goto up
if "%1"=="down" goto down
if "%1"=="status" goto status
if "%1"=="build" goto build
if "%1"=="test" goto test
if "%1"=="report" goto report
if "%1"=="seed" goto seed
if "%1"=="soak" goto soak
if "%1"=="redteam" goto redteam
if "%1"=="evidence" goto evidence
if "%1"=="metering" goto metering
if "%1"=="clean" goto clean
if "%1"=="dev" goto dev
if "%1"=="lint" goto lint
if "%1"=="format" goto format
if "%1"=="docker:build" goto docker_build
if "%1"=="docker:run" goto docker_run
if "%1"=="docker:stop" goto docker_stop
goto unknown

:help
echo.
echo Provability Fabric Testbed - Available Commands:
echo.
echo Core Operations:
echo   up          - Start all services
echo   down        - Stop all services
echo   status      - Show service status
echo   seed        - Seed data and populate indices
echo   soak        - Load testing and performance validation
echo   redteam     - Security testing and adversarial validation
echo   test        - Run all tests
echo   report      - Generate testbed reports
echo   clean       - Clean build artifacts
echo.
echo New Capabilities:
echo   evidence    - Generate evidence pack export
echo   metering    - Generate billing and usage reports
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
echo   run.bat evidence
echo   run.bat soak
echo.
exit /b 0

:up
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
exit /b 0

:down
echo Stopping all services...
docker-compose down
echo Services stopped.
exit /b 0

:status
echo Service Status:
docker-compose ps
echo.
echo Note: Health checks require PowerShell and may not work in all environments
exit /b 0

:build
echo Building TypeScript components...
npm run build
echo Build completed!
exit /b 0

:test
echo Running all tests...
npm test
echo.
echo Running Python tests...
pytest testbed/tools/reporter/
echo.
echo Tests completed!
exit /b 0

:report
echo Generating testbed report...
npm run report:generate
echo.
echo Report generated! Check the reports/ directory.
exit /b 0

:seed
echo Seeding data and populating indices...
echo Running data generator...
cd testbed/data && python generator.py --tenant acme --count 100
cd testbed/data && python generator.py --tenant globex --count 100
echo.
echo Running honeytoken generator...
cd testbed/data && python honeytoken-generator.py --count 50
echo.
echo Data seeding completed!
exit /b 0

:soak
echo Running soak/load testing...
echo Installing k6 if not present...
where k6 >nul 2>&1 || echo Please install k6 from https://k6.io/docs/getting-started/installation/
echo.
echo Running edge load test...
cd external/provability-fabric/tests/load && k6 run edge_load.js
echo.
echo Running ledger load test...
cd external/provability-fabric/tests/load && k6 run ledger_load.js
echo.
echo Soak testing completed!
exit /b 0

:redteam
echo Running redteam security testing...
echo Installing Python dependencies...
cd external/provability-fabric/tests/redteam && pip install -r requirements.txt 2>nul || echo Requirements already installed
echo.
echo Running redteam tests...
cd external/provability-fabric/tests/redteam && python redteam_runner.py --kube-config ~/.kube/config --ledger-url http://localhost:4000
echo.
echo Redteam testing completed!
exit /b 0

:evidence
echo Generating evidence pack export...
echo Installing Python dependencies...
cd testbed/tools/reporter && pip install -r requirements.txt 2>nul || echo Requirements already installed
echo.
echo Generating evidence pack...
cd testbed && python tools/reporter/generate_testbed_report.py --config tools/reporter/config.yaml --output ./evidence --format both --time-range 168 --include-art-comparison --include-redteam-analysis
echo.
echo Evidence pack generated in testbed/evidence/
exit /b 0

:metering
echo Generating metering and billing reports...
echo Installing Node.js dependencies...
cd testbed/tools/metering && npm install
echo.
echo Simulating usage for ACME Corp...
cd testbed/tools/metering && npm start -- simulate-usage acme-corp 50 --period 2025-01
echo.
echo Simulating usage for Globex Corp...
cd testbed/tools/metering && npm start -- simulate-usage globex-corp 50 --period 2025-01
echo.
echo Generating invoices...
cd testbed/tools/metering && npm start -- generate-invoice acme-corp 2025-01 -o ../../evidence/acme-invoice.json
cd testbed/tools/metering && npm start -- generate-invoice globex-corp 2025-01 -o ../../evidence/globex-invoice.json
echo.
echo Exporting metrics...
cd testbed/tools/metering && npm start -- export-metrics -o ../../evidence/usage-metrics.prom
echo.
echo Metering reports generated in testbed/evidence/
exit /b 0

:clean
echo Cleaning build artifacts...
npm run clean
echo Cleanup completed!
exit /b 0

:dev
echo Starting development environment...
npm run dev
exit /b 0

:lint
echo Running linting...
npm run lint
echo Linting completed!
exit /b 0

:format
echo Formatting code...
npm run format
echo Formatting completed!
exit /b 0

:docker_build
echo Building Docker images...
npm run docker:build
echo Docker build completed!
exit /b 0

:docker_run
echo Starting Docker services...
npm run docker:run
echo Docker services started!
exit /b 0

:docker_stop
echo Stopping Docker services...
npm run docker:stop
echo Docker services stopped!
exit /b 0

:unknown
echo Unknown command: %1
echo Run 'run.bat' without arguments to see available commands.
exit /b 1
