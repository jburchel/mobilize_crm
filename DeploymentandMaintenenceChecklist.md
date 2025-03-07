# Mobilize CRM Deployment and Maintenance Checklist

## Pre-Deployment Checklist

- [ ] Ensure all routes are working correctly locally
- [ ] Verify Gmail sync functionality is working
- [ ] Check that authentication is working properly
- [ ] Ensure database connections are functioning
- [ ] Test all critical user flows (people, churches, communications, tasks)
- [ ] Verify that environment variables are properly set
- [ ] Run the application locally to catch any obvious errors

## Deployment Process

- [ ] Make sure you're on the stable branch: `git checkout stable-working-version`
- [ ] Commit any changes with clear, descriptive messages
- [ ] Push changes to GitHub: `git push origin stable-working-version`
- [ ] Run the deployment script: `./deploy.sh`
- [ ] Verify the deployment was successful
- [ ] Check the application at https://mobilize-crm.org
- [ ] Test critical functionality in the production environment

## Post-Deployment Verification

- [ ] Verify people and churches pages are accessible
- [ ] Check that Gmail sync is working without errors
- [ ] Verify authentication and user sessions are working
- [ ] Test email sending functionality
- [ ] Check background jobs are running properly
- [ ] Verify database connections and queries are working
- [ ] Monitor logs for any unexpected errors

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

- [ ] Create feature branches for new development
- [ ] Make small, focused commits with clear messages
- [ ] Use pull requests for code review
- [ ] Maintain a stable main branch
- [ ] Tag stable releases for easy rollback

## Backup and Recovery

- [ ] Regularly backup the database
- [ ] Document all environment variables
- [ ] Keep a record of deployment history
- [ ] Maintain a stable branch that's known to work

## Monitoring and Maintenance

- [ ] Regularly check application logs
- [ ] Monitor database performance
- [ ] Update dependencies periodically
- [ ] Schedule regular maintenance windows
- [ ] Keep documentation up to date

## Emergency Rollback Procedure

1. Identify the last stable version
2. Check out that version: `git checkout <stable-commit-hash>`
3. Create a new branch if needed: `git checkout -b rollback-branch`
4. Deploy the stable version: `./deploy.sh`
5. Verify the rollback fixed the issue
6. Document what happened for future reference

Remember: Always test thoroughly before deploying to production, and maintain good documentation of your deployment process and any issues encountered. 