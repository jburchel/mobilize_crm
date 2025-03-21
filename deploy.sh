#!/bin/bash

# Exit on error
set -e

# Configuration
PROJECT_ID="mobilize-crm"  # Replace with your GCP project ID
SERVICE_NAME="mobilize-crm"
# Choose a region where Cloud Run is available: us-central1 (Iowa), us-east1 (S. Carolina), 
# us-west1 (Oregon), europe-west1 (Belgium), asia-east1 (Taiwan)
REGION="us-central1"  

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting deployment process...${NC}"

# Check current branch
CURRENT_BRANCH=$(git branch --show-current)

# If on stable-working-version, offer to merge to main
if [ "$CURRENT_BRANCH" = "stable-working-version" ]; then
    echo -e "${YELLOW}You are on the 'stable-working-version' branch.${NC}"
    read -p "Do you want to merge 'stable-working-version' into 'main' before deploying? (Y/n): " merge_branch
    
    if [[ ! "$merge_branch" =~ ^[Nn]$ ]]; then
        # Check for uncommitted changes
        if ! git diff-index --quiet HEAD --; then
            echo -e "${RED}You have uncommitted changes. Please commit or stash them before merging.${NC}"
            exit 1
        fi
        
        echo -e "${YELLOW}Switching to 'main' branch...${NC}"
        git checkout main
        
        # Make sure main is up to date
        echo -e "${YELLOW}Pulling latest changes from remote main...${NC}"
        git pull origin main
        
        echo -e "${YELLOW}Merging 'stable-working-version' into 'main'...${NC}"
        if git merge stable-working-version -m "Merge stable-working-version for deployment"; then
            echo -e "${GREEN}Successfully merged 'stable-working-version' into 'main'.${NC}"
            
            echo -e "${YELLOW}Pushing changes to remote 'main'...${NC}"
            git push --no-verify origin main
            echo -e "${GREEN}Successfully pushed to remote 'main'.${NC}"
        else
            echo -e "${RED}Merge conflict occurred. Please resolve conflicts manually and try again.${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}Switching to 'main' branch without merging...${NC}"
        
        # Check for uncommitted changes
        if ! git diff-index --quiet HEAD --; then
            echo -e "${RED}You have uncommitted changes. Please commit or stash them before switching branches.${NC}"
            exit 1
        fi
        
        git checkout main
        echo -e "${GREEN}Switched to 'main' branch.${NC}"
    fi
# If not on main, offer to switch
elif [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${YELLOW}Currently on branch '$CURRENT_BRANCH'. Deployment should be done from 'main' branch.${NC}"
    read -p "Do you want to switch to 'main' branch? (Y/n): " switch_branch
    if [[ "$switch_branch" =~ ^[Nn]$ ]]; then
        echo -e "${RED}Deployment aborted. Please switch to 'main' branch manually and try again.${NC}"
        exit 1
    fi
    
    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD --; then
        echo -e "${RED}You have uncommitted changes. Please commit or stash them before switching branches.${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Switching to 'main' branch...${NC}"
    git checkout main
    echo -e "${GREEN}Switched to 'main' branch.${NC}"
fi

# Verify main branch is up to date
echo -e "${YELLOW}Verifying 'main' branch is up to date with remote...${NC}"
git fetch origin
LOCAL=$(git rev-parse main)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo -e "${YELLOW}Local 'main' branch is not in sync with remote.${NC}"
    read -p "Do you want to pull the latest changes? (Y/n): " pull_changes
    if [[ "$pull_changes" =~ ^[Nn]$ ]]; then
        echo -e "${RED}Deployment aborted. Please update your 'main' branch and try again.${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Pulling latest changes from remote...${NC}"
    git pull origin main
    echo -e "${GREEN}Successfully updated 'main' branch.${NC}"
fi

# Run pre-deployment checks
echo -e "${YELLOW}Running pre-deployment checks...${NC}"

# Verify routes
echo -e "${YELLOW}Verifying route definitions...${NC}"
if ! python verify_routes.py; then
    echo -e "${RED}Route verification failed. Please fix the issues before deploying.${NC}"
    echo -e "${YELLOW}You can run './verify_routes.py' manually to see the details.${NC}"
    
    # Ask if user wants to continue anyway
    read -p "Do you want to continue with deployment anyway? (y/N): " continue_deploy
    if [[ ! "$continue_deploy" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Deployment aborted.${NC}"
        exit 1
    fi
    echo -e "${YELLOW}Continuing with deployment despite route verification issues...${NC}"
fi

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if user is logged in to gcloud
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo -e "${YELLOW}You need to log in to Google Cloud first.${NC}"
    gcloud auth login
fi

# Set the project
echo -e "${YELLOW}Setting GCP project to ${PROJECT_ID}...${NC}"
gcloud config set project ${PROJECT_ID}

# Build the container image
echo -e "${YELLOW}Building container image...${NC}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
gcloud builds submit --tag ${IMAGE_NAME}

# Deploy to Cloud Run
echo -e "${YELLOW}Deploying to Cloud Run...${NC}"
echo -e "${YELLOW}Note: For the first deployment, you'll need to set environment variables in the Cloud Run console after deployment.${NC}"
echo -e "${YELLOW}For subsequent deployments, uncomment and update the --set-env-vars section in this script.${NC}"

gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --memory 512Mi \
  --set-env-vars="FLASK_ENV=production,\
BASE_URL=https://mobilize-crm.org,\
SECRET_KEY=$(openssl rand -hex 24)"

# Uncomment and update these environment variables for subsequent deployments
# --set-env-vars="FLASK_ENV=production,\
# DB_CONNECTION_STRING=YOUR_DB_CONNECTION_STRING,\
# SECRET_KEY=$(openssl rand -hex 24),\
# BASE_URL=https://mobilize-crm.org,\
# FIREBASE_API_KEY=YOUR_FIREBASE_API_KEY,\
# FIREBASE_AUTH_DOMAIN=YOUR_FIREBASE_AUTH_DOMAIN,\
# FIREBASE_PROJECT_ID=YOUR_FIREBASE_PROJECT_ID,\
# FIREBASE_STORAGE_BUCKET=YOUR_FIREBASE_STORAGE_BUCKET,\
# FIREBASE_MESSAGING_SENDER_ID=YOUR_FIREBASE_MESSAGING_SENDER_ID,\
# FIREBASE_APP_ID=YOUR_FIREBASE_APP_ID,\
# FIREBASE_MEASUREMENT_ID=YOUR_FIREBASE_MEASUREMENT_ID,\
# GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID,\
# GOOGLE_CLIENT_SECRET=YOUR_GOOGLE_CLIENT_SECRET,\
# LOG_LEVEL=INFO,\
# LOG_TO_STDOUT=True" \

# Note: SMTP settings are removed as they're not needed with Google OAuth
# Note: SECRET_KEY is generated using openssl for security

# Get the URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --platform managed --region ${REGION} --format="value(status.url)")

echo -e "${GREEN}Deployment complete!${NC}"
echo -e "${GREEN}Your application is available at: ${SERVICE_URL}${NC}" 

# Set up custom domain mapping
echo -e "${YELLOW}Setting up custom domain mapping...${NC}"
gcloud beta run domain-mappings create \
  --service ${SERVICE_NAME} \
  --domain mobilize-crm.org \
  --region ${REGION} \
  --platform managed

echo -e "${GREEN}Domain mapping created. Please set up the following DNS records:${NC}"
gcloud beta run domain-mappings describe \
  --domain mobilize-crm.org \
  --region ${REGION} \
  --platform managed

# Add a tag to the deployment
DEPLOY_DATE=$(date +"%Y-%m-%d_%H-%M-%S")
git tag "deployment_${DEPLOY_DATE}"
git push origin "deployment_${DEPLOY_DATE}"
echo -e "${GREEN}Created deployment tag: deployment_${DEPLOY_DATE}${NC}"