#!/bin/bash
# Football Career Quiz - Deployment Script
# This script deploys the application to either Render or Fly.io

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
PLATFORM="fly"  # Default to Fly.io
ENV="production"
APP_NAME="footy-career-quiz"
REGION="iad"  # Default to US East (Virginia)

# Display usage information
usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -p, --platform PLATFORM    Platform to deploy to (fly or render) [default: fly]"
    echo "  -e, --env ENVIRONMENT      Environment to deploy to (production or staging) [default: production]"
    echo "  -n, --name APP_NAME        Application name [default: footy-career-quiz]"
    echo "  -r, --region REGION        Region to deploy to [default: iad (US East)]"
    echo "  -h, --help                 Display this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --platform fly --env production"
    echo "  $0 --platform render --name my-quiz-app"
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -p|--platform)
            PLATFORM="$2"
            shift 2
            ;;
        -e|--env)
            ENV="$2"
            shift 2
            ;;
        -n|--name)
            APP_NAME="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate platform
if [[ "$PLATFORM" != "fly" && "$PLATFORM" != "render" ]]; then
    echo -e "${RED}Error: Platform must be either 'fly' or 'render'${NC}"
    usage
fi

# Check if we're in the project root (look for app.py)
if [[ ! -f "app.py" ]]; then
    echo -e "${RED}Error: app.py not found. Please run this script from the project root.${NC}"
    exit 1
fi

# Ensure we have a .env file for production
if [[ ! -f ".env" && "$ENV" == "production" ]]; then
    if [[ -f ".env.example" ]]; then
        echo -e "${YELLOW}Warning: .env file not found. Creating from .env.example${NC}"
        cp .env.example .env
        echo -e "${YELLOW}Please edit .env with your production settings!${NC}"
        echo -e "${YELLOW}Press Enter to continue or Ctrl+C to abort...${NC}"
        read
    else
        echo -e "${RED}Error: Neither .env nor .env.example found. Please create a .env file.${NC}"
        exit 1
    fi
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Deploy to Fly.io
deploy_to_fly() {
    echo -e "${GREEN}Deploying to Fly.io...${NC}"
    
    # Check if flyctl is installed
    if ! command_exists flyctl; then
        echo -e "${YELLOW}flyctl not found. Installing...${NC}"
        curl -L https://fly.io/install.sh | sh
        export PATH="$HOME/.fly/bin:$PATH"
    fi
    
    # Check if logged in
    if ! flyctl auth whoami &> /dev/null; then
        echo -e "${YELLOW}Not logged in to Fly.io. Please log in:${NC}"
        flyctl auth login
    fi
    
    # Check if app exists
    if ! flyctl apps list | grep -q "$APP_NAME"; then
        echo -e "${YELLOW}App '$APP_NAME' not found. Creating...${NC}"
        
        # Create fly.toml if it doesn't exist
        if [[ ! -f "fly.toml" ]]; then
            echo -e "${YELLOW}Creating fly.toml configuration...${NC}"
            cat > fly.toml << EOF
app = "$APP_NAME"
primary_region = "$REGION"

[build]
  dockerfile = "Dockerfile"

[env]
  FLASK_ENV = "$ENV"
  PORT = "8000"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0
  processes = ["app"]

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 512
EOF
        fi
        
        # Launch the app
        flyctl launch --name "$APP_NAME" --region "$REGION" --no-deploy
    fi
    
    # Set secrets from .env if it exists
    if [[ -f ".env" ]]; then
        echo -e "${GREEN}Setting secrets from .env file...${NC}"
        while IFS= read -r line || [[ -n "$line" ]]; do
            # Skip comments and empty lines
            [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
            
            # Extract key and value
            key=$(echo "$line" | cut -d '=' -f 1)
            value=$(echo "$line" | cut -d '=' -f 2-)
            
            # Set secret
            echo -e "${GREEN}Setting secret: $key${NC}"
            flyctl secrets set "$key=$value" --app "$APP_NAME"
        done < .env
    fi
    
    # Deploy the app
    echo -e "${GREEN}Deploying app to Fly.io...${NC}"
    flyctl deploy --app "$APP_NAME" --region "$REGION"
    
    # Show app info
    echo -e "${GREEN}Deployment complete! App information:${NC}"
    flyctl info --app "$APP_NAME"
    
    echo -e "${GREEN}Your app is available at: https://$APP_NAME.fly.dev${NC}"
}

# Deploy to Render
deploy_to_render() {
    echo -e "${GREEN}Deploying to Render...${NC}"
    
    # Check if render CLI is installed
    if ! command_exists render; then
        echo -e "${YELLOW}Render CLI not found.${NC}"
        echo -e "${YELLOW}For Render deployments, we'll create a render.yaml file for Blueprint deployments.${NC}"
    fi
    
    # Create render.yaml if it doesn't exist
    if [[ ! -f "render.yaml" ]]; then
        echo -e "${YELLOW}Creating render.yaml configuration...${NC}"
        cat > render.yaml << EOF
services:
  - type: web
    name: $APP_NAME
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    envVars:
      - key: FLASK_ENV
        value: $ENV
      - key: PORT
        value: 8000
      - key: PYTHON_VERSION
        value: 3.10.0
EOF
        
        # Add secrets from .env if it exists
        if [[ -f ".env" ]]; then
            echo -e "${GREEN}Adding environment variables from .env file to render.yaml...${NC}"
            while IFS= read -r line || [[ -n "$line" ]]; do
                # Skip comments and empty lines
                [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
                
                # Extract key and value
                key=$(echo "$line" | cut -d '=' -f 1)
                value=$(echo "$line" | cut -d '=' -f 2-)
                
                # Add to render.yaml
                echo "      - key: $key" >> render.yaml
                echo "        value: $value" >> render.yaml
            done < .env
        fi
    fi
    
    # If Render CLI is installed, deploy using CLI
    if command_exists render; then
        echo -e "${GREEN}Deploying using Render CLI...${NC}"
        render deploy
    else
        echo -e "${YELLOW}Render CLI not installed. Manual deployment steps:${NC}"
        echo -e "1. Create a new Web Service on Render and connect your GitHub repository"
        echo -e "2. Render will automatically use the render.yaml file for configuration"
        echo -e "3. Or use Render Blueprints: https://render.com/docs/blueprint-spec"
        echo -e "${GREEN}Your render.yaml file is ready for deployment.${NC}"
    fi
}

# Main deployment logic
echo -e "${GREEN}Starting deployment of Football Career Quiz to $PLATFORM...${NC}"

# Run tests before deployment
echo -e "${GREEN}Running tests before deployment...${NC}"
if command_exists pytest; then
    pytest -xvs || { echo -e "${RED}Tests failed. Aborting deployment.${NC}"; exit 1; }
else
    echo -e "${YELLOW}pytest not found. Skipping tests.${NC}"
fi

# Build static assets if needed
# (This app doesn't have a complex frontend build process, but you could add it here)

# Deploy to the selected platform
case "$PLATFORM" in
    "fly")
        deploy_to_fly
        ;;
    "render")
        deploy_to_render
        ;;
esac

echo -e "${GREEN}Deployment process completed!${NC}"
