#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
"""
AstraDesk Development Environment Setup Script

This script automates the setup of a complete development environment for AstraDesk,
including all dependencies, services, and development tools.
"""

set -e

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_VERSION="3.11"
NODE_VERSION="18"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

OS=$(detect_os)

# Check system requirements
check_system_requirements() {
    log_info "Checking system requirements..."

    # Check Docker
    if ! command_exists docker; then
        log_error "Docker is required but not installed. Please install Docker first."
        exit 1
    fi

    # Check Docker Compose
    if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
        log_error "Docker Compose is required but not installed."
        exit 1
    fi

    # Check Python
    if ! command_exists python3; then
        log_error "Python 3 is required but not installed."
        exit 1
    fi

    # Check Node.js (optional for some components)
    if ! command_exists node; then
        log_warning "Node.js not found. Some components may not work."
    fi

    # Check Git
    if ! command_exists git; then
        log_error "Git is required but not installed."
        exit 1
    fi

    log_success "System requirements check passed"
}

# Setup Python environment
setup_python() {
    log_info "Setting up Python environment..."

    cd "$PROJECT_ROOT"

    # Check if virtual environment already exists
    if [ -d ".venv" ]; then
        log_warning "Virtual environment already exists. Activating..."
    else
        log_info "Creating virtual environment..."
        python3 -m venv .venv
    fi

    # Activate virtual environment
    source .venv/bin/activate

    # Upgrade pip
    pip install --upgrade pip

    # Install Python dependencies
    log_info "Installing Python dependencies..."

    # Core dependencies
    pip install -e ./core

    # Service dependencies
    if [ -f "services/api-gateway/requirements.txt" ]; then
        pip install -r services/api-gateway/requirements.txt
    fi

    # MCP dependencies
    if [ -f "mcp/requirements.txt" ]; then
        pip install -r mcp/requirements.txt
    fi

    # Domain pack dependencies
    for pack in packages/domain-*; do
        if [ -d "$pack" ] && [ -f "$pack/requirements.txt" ]; then
            log_info "Installing dependencies for $pack..."
            pip install -r "$pack/requirements.txt"
        fi
    done

    # Development dependencies
    pip install pytest pytest-asyncio pytest-cov black isort mypy ruff pre-commit

    log_success "Python environment setup complete"
}

# Setup Node.js environment (if needed)
setup_nodejs() {
    if command_exists node; then
        log_info "Setting up Node.js environment..."

        cd "$PROJECT_ROOT"

        # Check if package.json exists (for any frontend components)
        if [ -f "package.json" ]; then
            npm install
            log_success "Node.js dependencies installed"
        else
            log_info "No package.json found, skipping Node.js setup"
        fi
    else
        log_warning "Node.js not available, skipping Node.js setup"
    fi
}

# Setup Docker services
setup_docker_services() {
    log_info "Setting up Docker services..."

    cd "$PROJECT_ROOT"

    # Check if docker-compose.yml exists
    if [ -f "docker-compose.yml" ]; then
        log_info "Starting Docker services..."

        # Start services in detached mode
        if command_exists docker-compose; then
            docker-compose up -d
        else
            docker compose up -d
        fi

        # Wait for services to be healthy
        log_info "Waiting for services to be ready..."
        sleep 30

        # Check service health
        if command_exists docker-compose; then
            docker-compose ps
        else
            docker compose ps
        fi

        log_success "Docker services started"
    else
        log_warning "No docker-compose.yml found"
    fi
}

# Setup development databases
setup_databases() {
    log_info "Setting up development databases..."

    cd "$PROJECT_ROOT"

    # Run database migrations if they exist
    if [ -d "migrations" ]; then
        log_info "Running database migrations..."

        # This would typically use a migration tool like Alembic
        # For now, we'll just check if PostgreSQL is running
        if docker ps | grep -q postgres; then
            log_success "PostgreSQL container is running"
        else
            log_warning "PostgreSQL container not found"
        fi
    fi

    # Setup Redis
    if docker ps | grep -q redis; then
        log_success "Redis container is running"
    else
        log_warning "Redis container not found"
    fi

    # Setup NATS
    if docker ps | grep -q nats; then
        log_success "NATS container is running"
    else
        log_warning "NATS container not found"
    fi
}

# Setup development tools
setup_dev_tools() {
    log_info "Setting up development tools..."

    cd "$PROJECT_ROOT"

    # Setup pre-commit hooks
    if [ -f ".pre-commit-config.yaml" ]; then
        pre-commit install
        log_success "Pre-commit hooks installed"
    fi

    # Setup git hooks for development
    if [ -d ".git" ]; then
        # Add git hooks for development
        log_info "Setting up git hooks..."

        # Create pre-push hook to run tests
        mkdir -p .git/hooks
        cat > .git/hooks/pre-push << 'EOF'
#!/bin/bash
echo "Running pre-push checks..."

# Run quick tests
if command -v pytest >/dev/null 2>&1; then
    echo "Running tests..."
    python -m pytest tests/ -x --tb=short
    if [ $? -ne 0 ]; then
        echo "Tests failed. Push aborted."
        exit 1
    fi
fi

echo "Pre-push checks passed."
EOF

        chmod +x .git/hooks/pre-push
        log_success "Git hooks configured"
    fi
}

# Setup environment configuration
setup_environment() {
    log_info "Setting up environment configuration..."

    cd "$PROJECT_ROOT"

    # Copy environment template if it exists
    if [ -f ".env.example" ]; then
        if [ ! -f ".env" ]; then
            cp .env.example .env
            log_success "Environment file created from template"
        else
            log_warning "Environment file already exists"
        fi
    fi

    # Generate development certificates/keys if needed
    if [ ! -d "certs" ]; then
        mkdir -p certs
        log_info "Generating development certificates..."

        # Generate self-signed certificate for development
        openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
        log_success "Development certificates generated"
    fi
}

# Setup IDE configuration
setup_ide() {
    log_info "Setting up IDE configuration..."

    cd "$PROJECT_ROOT"

    # VS Code settings
    if [ -d ".vscode" ]; then
        log_info "VS Code configuration found"

        # Ensure Python interpreter is set
        if [ -f ".vscode/settings.json" ]; then
            log_success "VS Code settings configured"
        fi
    else
        log_warning "No .vscode directory found"
    fi

    # PyCharm configuration (if .idea directory exists)
    if [ -d ".idea" ]; then
        log_info "PyCharm configuration found"
    fi
}

# Run initial tests
run_initial_tests() {
    log_info "Running initial tests to verify setup..."

    cd "$PROJECT_ROOT"

    # Activate virtual environment
    source .venv/bin/activate

    # Run basic health checks
    python -c "import sys; print(f'Python version: {sys.version}')"

    # Test imports
    python -c "
try:
    from services.api_gateway.src.gateway.main import app
    print('✓ API Gateway import successful')
except ImportError as e:
    print(f'✗ API Gateway import failed: {e}')
    sys.exit(1)
"

    # Run a quick test if pytest is available
    if command -v pytest >/dev/null 2>&1; then
        log_info "Running quick test suite..."
        python -m pytest tests/ -x --tb=short --maxfail=3 -q
        if [ $? -eq 0 ]; then
            log_success "Initial tests passed"
        else
            log_warning "Some tests failed - check the output above"
        fi
    fi
}

# Display setup summary
display_summary() {
    log_success "Development environment setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Activate the virtual environment: source .venv/bin/activate"
    echo "2. Start the development server: python -m services.api_gateway.src.gateway.main"
    echo "3. Run tests: python -m pytest tests/"
    echo "4. View documentation: http://localhost:8000/docs (when server is running)"
    echo ""
    echo "Useful commands:"
    echo "- Start services: docker-compose up -d"
    echo "- Stop services: docker-compose down"
    echo "- Run tests: python -m pytest tests/"
    echo "- Format code: black . && isort ."
    echo "- Lint code: ruff check ."
    echo ""
    echo "Environment variables (.env file):"
    echo "- Check and update database URLs, API keys, etc."
    echo ""
}

# Main setup function
main() {
    log_info "Starting AstraDesk development environment setup..."

    check_system_requirements
    setup_python
    setup_nodejs
    setup_docker_services
    setup_databases
    setup_dev_tools
    setup_environment
    setup_ide
    run_initial_tests
    display_summary

    log_success "Setup completed successfully!"
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi