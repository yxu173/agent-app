#!/bin/bash

# Agent App Deployment Script
# Usage: ./scripts/deploy.sh [dev|prd]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if uv is installed
    if ! command -v uv &> /dev/null; then
        print_error "uv is not installed. Please install it first:"
        echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    
    # Check if agno is installed
    if ! command -v ag &> /dev/null; then
        print_error "Agno CLI is not installed. Please install it first:"
        echo "pip install agno"
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker Desktop first."
        exit 1
    fi
    
    print_success "All prerequisites are met!"
}

# Function to setup development environment
setup_dev() {
    print_status "Setting up development environment..."
    
    # Run dev setup script
    if [ -f "./scripts/dev_setup.sh" ]; then
        chmod +x ./scripts/dev_setup.sh
        ./scripts/dev_setup.sh
    else
        print_error "dev_setup.sh not found!"
        exit 1
    fi
    
    print_success "Development environment setup complete!"
}

# Function to check environment variables
check_env_vars() {
    print_status "Checking environment variables..."
    
    local has_openai=false
    local has_openrouter=false

    if [ -n "$OPENAI_API_KEY" ]; then
        has_openai=true
        print_success "OPENAI_API_KEY is set"
    else
        print_warning "OPENAI_API_KEY is not set"
    fi

    if [ -n "$OPENROUTER_API_KEY" ]; then
        has_openrouter=true
        print_success "OPENROUTER_API_KEY is set"
    else
        print_warning "OPENROUTER_API_KEY is not set"
    fi

    if [ "$has_openai" = false ] && [ "$has_openrouter" = false ]; then
        print_warning "No LLM provider keys detected. Set at least one of:"
        echo "  export OPENAI_API_KEY='sk-...'"
        echo "  export OPENROUTER_API_KEY='or-...'"
        print_warning "Continuing without keys may limit functionality."
    fi
}

# Function to deploy development environment
deploy_dev() {
    print_status "Deploying development environment..."
    
    check_prerequisites
    setup_dev
    check_env_vars
    
    print_status "Starting development workspace..."
    ag ws up --env dev
    
    print_success "Development deployment complete!"
    echo
    echo "Access your application:"
    echo "  - Streamlit UI: http://localhost:8501"
    echo "  - FastAPI docs: http://localhost:8000/docs"
    echo
    echo "To stop the workspace: ag ws down"
}

# Function to deploy production environment
deploy_prd() {
    print_status "Deploying production environment..."
    
    check_prerequisites
    check_env_vars
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    # Check if secrets file exists
    if [ ! -f "workspace/secrets/prd_app_secrets.yml" ]; then
        print_error "Production secrets file not found: workspace/secrets/prd_app_secrets.yml"
        print_status "Please create it based on workspace/example_secrets/prd_app_secrets.yml"
        exit 1
    fi
    
    print_status "Deploying to AWS ECS..."
    ag ws up --env prd
    
    print_success "Production deployment complete!"
    echo
    echo "Check deployment status: ag ws config --env prd"
    echo "View logs: ag ws logs --env prd"
    echo "Stop deployment: ag ws down --env prd"
}

# Function to show help
show_help() {
    echo "Agent App Deployment Script"
    echo
    echo "Usage: $0 [dev|prd]"
    echo
    echo "Commands:"
    echo "  dev     Deploy development environment (local Docker)"
    echo "  prd     Deploy production environment (AWS ECS)"
    echo "  help    Show this help message"
    echo
    echo "Examples:"
    echo "  $0 dev    # Deploy development environment"
    echo "  $0 prd    # Deploy production environment"
}

# Main script logic
case "${1:-help}" in
    "dev")
        deploy_dev
        ;;
    "prd")
        deploy_prd
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        print_error "Invalid command: $1"
        echo
        show_help
        exit 1
        ;;
esac

