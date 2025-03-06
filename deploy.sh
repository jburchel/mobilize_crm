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