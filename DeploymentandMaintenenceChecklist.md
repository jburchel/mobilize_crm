# Mobilize CRM Deployment and Maintenance Checklist

## Pre-Deployment Checklist

- [x] Verify all routes are working locally
- [x] Verify Gmail sync functionality
- [x] Check authentication
- [x] Test database connections
- [x] Verify environment variables
- [x] Test all critical user flows (people, churches, communications, tasks)
- [x] Run the application locally to catch any obvious errors

## Development Environment Testing (REQUIRED)
- [ ] Deploy changes to development environment first
- [ ] Verify landing page loads correctly
- [ ] Test Google authentication flow end-to-end
- [ ] Verify dashboard loads after authentication
- [ ] Check all links on dashboard for correct routes
- [ ] Test people management functionality
- [ ] Test church management functionality
- [ ] Test task management functionality
- [ ] Test communications functionality
- [ ] Check logs for any errors or warnings
- [ ] Verify all new features work as expected
- [ ] Test on different browsers if applicable
- [ ] Test on mobile devices if applicable

## Deployment Process

- [x] Ensure you're on the stable-working-version branch
- [x] Commit any changes with clear, descriptive messages
- [x] Push changes to GitHub: `git push origin stable-working-version`
- [x] Run the deployment script: `./deploy.sh`
- [x] Verify the deployment was successful
- [x] Check the application at https://mobilize-crm.org
- [x] Test critical functionality in the production environment
- [x] Check that the custom domain is properly mapped

## Post-Deployment Verification

- [x] Verify the application is accessible at the custom domain
- [x] Verify login functionality
- [x] Verify dashboard access
- [x] Verify people/churches pages
- [x] Verify Gmail sync
- [x] Verify email sending
- [x] Verify background jobs
- [x] Verify database connections
- [x] Monitor logs for errors
- [x] Fixed route name mismatch: renamed `people` function to `list_people` to match dashboard template references
- [x] Fixed route name mismatch: changed `people_bp.new_person` to `people_bp.add_person_form` in dashboard template
- [x] Fixed route name mismatch: changed `tasks_bp.view_task` to `tasks_bp.get_task` in dashboard template

## Common Issues and Solutions

### Route Name Mismatches
- Check template files for references to non-existent routes
- Ensure route function names match what's referenced in templates
- Use grep to search for url_for references and verify they exist
- After fixing route names, check for other references that might need updating

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

- [x] Use descriptive commit messages
- [x] Keep the stable-working-version branch clean
- [x] Test changes thoroughly before merging to stable-working-version
- [x] Document significant changes
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
- [x] Ensure database backups are configured
- [x] Verify backup restoration process
- [x] Document recovery procedures

## Monitoring and Maintenance

- [x] Regularly check application logs
- [x] Monitor database performance
- [x] Update dependencies periodically
- [x] Schedule regular maintenance windows
- [x] Keep documentation up to date
- [x] Set up monitoring for application health
- [x] Configure alerts for critical errors
- [x] Regularly review logs for issues
- [x] Schedule routine maintenance

## Emergency Rollback Procedure

1. Identify the last stable version
2. Check out that version: `git checkout <stable-commit-hash>`
3. Create a new branch if needed: `git checkout -b rollback-branch`
4. Deploy the stable version: `./deploy.sh`
5. Verify the rollback fixed the issue
6. Document what happened for future reference

Remember: Always test thoroughly before deploying to production, and maintain good documentation of your deployment process and any issues encountered. 