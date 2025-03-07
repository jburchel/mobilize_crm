# Mobilize CRM Deployment and Maintenance Checklist

## Pre-Deployment Checklist

- [x] Ensure all routes are working correctly locally
- [x] Verify Gmail sync functionality is working
- [x] Check that authentication is working properly
- [x] Ensure database connections are functioning
- [x] Test all critical user flows (people, churches, communications, tasks)
- [x] Verify that environment variables are properly set
- [x] Run the application locally to catch any obvious errors

## Deployment Process

- [x] Make sure you're on the stable branch: `git checkout stable-working-version`
- [x] Commit any changes with clear, descriptive messages
- [x] Push changes to GitHub: `git push origin stable-working-version`
- [x] Run the deployment script: `./deploy.sh`
- [x] Verify the deployment was successful
- [x] Check the application at https://mobilize-crm.org
- [x] Test critical functionality in the production environment

## Post-Deployment Verification

- [x] Verify people and churches pages are accessible
- [x] Check that Gmail sync is working without errors
- [x] Verify authentication and user sessions are working
- [x] Test email sending functionality
- [x] Check background jobs are running properly
- [x] Verify database connections and queries are working
- [x] Monitor logs for any unexpected errors

## Common Issues and Solutions

### 404 Errors on Pages

- Check blueprint registrations in app.py
- Ensure URL prefixes are correctly set
- Verify route definitions in blueprint files don't duplicate prefixes

### Gmail Sync Issues

- If "include_history" parameter error occurs, remove it from list_messages() calls
- If timedelta.minutes error occurs, use total_seconds() method and convert to minutes

### Database Connection Issues

- Verify environment variables for database connection
- Check database credentials and access permissions
- Ensure database schema is up to date

## Version Control Best Practices

- [x] Create feature branches for new development
- [x] Make small, focused commits with clear messages
- [x] Use pull requests for code review
- [x] Maintain a stable main branch
- [x] Tag stable releases for easy rollback

## Backup and Recovery

- [x] Regularly backup the database
- [x] Document all environment variables
- [x] Keep a record of deployment history
- [x] Maintain a stable branch that's known to work

## Monitoring and Maintenance

- [x] Regularly check application logs
- [x] Monitor database performance
- [x] Update dependencies periodically
- [x] Schedule regular maintenance windows
- [x] Keep documentation up to date

## Emergency Rollback Procedure

1. Identify the last stable version
2. Check out that version: `git checkout <stable-commit-hash>`
3. Create a new branch if needed: `git checkout -b rollback-branch`
4. Deploy the stable version: `./deploy.sh`
5. Verify the rollback fixed the issue
6. Document what happened for future reference

Remember: Always test thoroughly before deploying to production, and maintain good documentation of your deployment process and any issues encountered. 