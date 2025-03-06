# Setting Up GitHub Integration with Google Cloud Build

This guide will walk you through the process of setting up automatic deployments from GitHub to Google Cloud Run using Google Cloud Build.

## Prerequisites

1. Your code is hosted in a GitHub repository
2. You have a Google Cloud Platform (GCP) account
3. You have the necessary permissions to create and manage Cloud Build triggers

## Step 1: Connect GitHub to Cloud Build

1. Go to the [Cloud Build Triggers page](https://console.cloud.google.com/cloud-build/triggers) in the Google Cloud Console
2. Select your project (`mobilize-crm`)
3. Click "Connect Repository"
4. Select "GitHub (Cloud Build GitHub App)" as the source
5. Click "Continue"
6. Authenticate with GitHub if prompted
7. Select your GitHub account
8. Select the repository containing your Mobilize CRM code
9. Click "Connect"

## Step 2: Create a Build Trigger

1. Click "Create Trigger"
2. Enter a name for your trigger (e.g., "mobilize-crm-main-branch-deploy")
3. Set the Event to "Push to a branch"
4. Set the Source to your GitHub repository
5. Set the Branch to "^main$" (to only trigger on pushes to the main branch)
6. Under Build Configuration, select "Cloud Build configuration file (yaml or json)"
7. Set the location to "Repository" and the file path to "cloudbuild.yaml"
8. Click "Create"

## Step 3: Test the Trigger

1. Make a small change to your code
2. Commit and push the change to the main branch of your GitHub repository
3. Go to the [Cloud Build History page](https://console.cloud.google.com/cloud-build/builds) to see your build in progress
4. Once the build completes successfully, your application will be automatically deployed to Cloud Run

## Step 4: Set Up Environment Variables (Optional)

If you need to set environment variables for your deployment:

1. Go to the [Cloud Run page](https://console.cloud.google.com/run) in the Google Cloud Console
2. Select your service (`mobilize-crm`)
3. Click "Edit & Deploy New Revision"
4. Under "Container, Networking, Security", expand the "Variables & Secrets" section
5. Add your environment variables
6. Click "Deploy"

## Troubleshooting

If your build fails, check the build logs for error messages. Common issues include:

- Missing permissions for Cloud Build service account
- Errors in your cloudbuild.yaml file
- Errors in your application code

For more detailed information, refer to the [Cloud Build documentation](https://cloud.google.com/build/docs/automating-builds/github/build-repos-from-github). 