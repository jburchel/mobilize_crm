# Mobilize CRM

A CRM system designed for non-profit organizations to manage contacts, churches, and communications.

## Features

- Contact management
- Church/organization tracking
- Pipeline management
- Email integration with Gmail
- Dashboard with visualizations
- Task management
- Calendar integration

## Development Setup

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Create a `.env` file based on `.env.example`
5. Initialize the database:
   ```
   flask db upgrade
   ```
6. Run the development server:
   ```
   flask run
   ```

## Deployment with Supabase and Google Cloud Run

### Setting up Supabase

1. Create a Supabase account at [https://supabase.com/](https://supabase.com/)
2. Create a new project
3. Get your database connection details from Project Settings > Database
4. Set the following environment variables:
   ```
   export DB_USER=postgres
   export DB_PASS=your-supabase-password
   export DB_NAME=postgres
   export DB_HOST=db.your-project-ref.supabase.co
   export DB_PORT=5432
   ```
5. Run the migration script to set up your Supabase database:
   ```
   ./migrate_to_supabase.py
   ```

### Deploying to Google Cloud Run

1. Install the Google Cloud SDK: [https://cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)
2. Update the `PROJECT_ID` and `REGION` in `deploy.sh`
3. Make the script executable:
   ```
   chmod +x deploy.sh
   ```
4. Run the deployment script:
   ```
   ./deploy.sh
   ```
5. After the first deployment, set up environment variables in the Cloud Run console
6. For subsequent deployments, uncomment and update the environment variables in `deploy.sh`

## Development Workflow

1. Make changes locally using SQLite database
2. Test thoroughly
3. Commit changes to Git
4. Deploy to Cloud Run using `./deploy.sh`

## Environment Variables

See `.env.example` for a list of required environment variables.

## License

[Your license information here] 