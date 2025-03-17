#!/bin/bash

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="mobilize-crm"
SERVICE_NAME="mobilize-crm"
REGION="us-central1"

# Function to prompt for confirmation
confirm() {
    read -r -p "${1:-Are you sure?} [y/N] " response
    case "$response" in
        [yY][eE][sS]|[yY]) 
            true
            ;;
        *)
            false
            ;;
    esac
}

# Function to check Python environment
check_python_env() {
    echo -e "${YELLOW}Checking Python environment...${NC}"
    
    # Check for virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        echo -e "${RED}Not running in a virtual environment. Please activate your virtual environment first.${NC}"
        exit 1
    fi
    
    # Check for required packages
    pip install -r requirements.txt
}

# Function to run tests
run_tests() {
    echo -e "${YELLOW}Running tests...${NC}"
    python -m pytest tests/
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Tests failed. Please fix the issues before deploying.${NC}"
        if ! confirm "Do you want to continue anyway?"; then
            exit 1
        fi
    fi
}

# Function to verify deployment configuration
verify_config() {
    local env=$1
    echo -e "${YELLOW}Verifying $env configuration...${NC}"
    
    python3 - <<EOF
from deploy_config import DeploymentConfig
config = DeploymentConfig('$env')

# Check environment variables
missing_vars = config.verify_env_vars()
if missing_vars:
    print(f"Missing environment variables: {', '.join(missing_vars)}")
    exit(1)

# Check database connection and schema
db_ok, db_error = config.verify_database_connection()
if not db_ok:
    print(f"Database verification failed: {db_error}")
    exit(1)

# Verify routes
routes_ok, routes_error = config.verify_routes()
if not routes_ok:
    print(f"Route verification failed: {routes_error}")
    exit(1)

print("Configuration verification successful!")
EOF
}

# Function to handle database operations
handle_database() {
    local env=$1
    echo -e "${YELLOW}Handling database operations for $env...${NC}"
    
    python3 - <<EOF
from deploy_config import DeploymentConfig
config = DeploymentConfig('$env')

# Create backup
backup_ok, backup_file = config.backup_database()
if not backup_ok:
    print(f"Database backup failed: {backup_file}")
    exit(1)
print(f"Database backup created: {backup_file}")

# Run migrations in dry-run mode first
migration_ok, migration_error = config.run_migrations(dry_run=True)
if not migration_ok:
    print(f"Migration dry-run failed: {migration_error}")
    exit(1)

# Run actual migrations
migration_ok, migration_error = config.run_migrations(dry_run=False)
if not migration_ok:
    print(f"Migration failed: {migration_error}")
    exit(1)

print("Database operations completed successfully!")
EOF
}

# Main deployment process
main() {
    local current_branch=$(git branch --show-current)
    
    # 1. Development Environment Deployment
    if [ "$current_branch" = "stable-working-version" ]; then
        echo -e "${YELLOW}Starting development environment deployment...${NC}"
        
        check_python_env
        run_tests
        verify_config "development"
        handle_database "development"
        
        # Deploy to development
        if ! confirm "Development checks passed. Deploy to staging?"; then
            echo -e "${YELLOW}Deployment cancelled.${NC}"
            exit 0
        fi
    fi
    
    # 2. Staging Environment Deployment
    echo -e "${YELLOW}Starting staging environment deployment...${NC}"
    
    # Create and switch to staging branch
    git checkout -b staging
    
    verify_config "staging"
    handle_database "staging"
    
    # Deploy to staging environment
    gcloud config set project ${PROJECT_ID}-staging
    gcloud builds submit --tag gcr.io/${PROJECT_ID}-staging/${SERVICE_NAME}
    
    if ! confirm "Staging deployment successful. Deploy to production?"; then
        echo -e "${YELLOW}Deployment cancelled at staging.${NC}"
        exit 0
    fi
    
    # 3. Production Environment Deployment
    echo -e "${YELLOW}Starting production deployment...${NC}"
    
    # Merge to main
    git checkout main
    git merge staging
    
    verify_config "production"
    handle_database "production"
    
    # Deploy to production
    gcloud config set project ${PROJECT_ID}
    gcloud builds submit --tag gcr.io/${PROJECT_ID}/${SERVICE_NAME}
    
    gcloud run deploy ${SERVICE_NAME} \
        --image gcr.io/${PROJECT_ID}/${SERVICE_NAME} \
        --platform managed \
        --region ${REGION} \
        --allow-unauthenticated
    
    # Tag the deployment
    DEPLOY_DATE=$(date +"%Y-%m-%d_%H-%M-%S")
    git tag "deployment_${DEPLOY_DATE}"
    git push origin "deployment_${DEPLOY_DATE}"
    
    echo -e "${GREEN}Deployment completed successfully!${NC}"
    
    # Clean up
    git branch -d staging
}

# Start the deployment process
if confirm "Ready to start deployment process?"; then
    main
else
    echo -e "${YELLOW}Deployment cancelled.${NC}"
    exit 0
fi 