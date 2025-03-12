# Mobilize CRM Deployment and Maintenance Checklist

## Pre-Deployment Checks

### Database
- [ ] Verify database connections are working
  - [ ] PostgreSQL connection
  - [ ] SQLite connection
- [ ] Run database synchronization
  ```bash
  python scripts/direct_sync.py
  ```
- [ ] Create a database backup
  ```bash
  python scripts/backup_database.py
  ```

### Authentication
- [ ] Verify Google OAuth credentials are valid
- [ ] Check authentication flow works end-to-end
- [ ] Verify user permissions and roles

### Routes
- [ ] Test all routes are working locally
  - [ ] `/` - Home page
  - [ ] `/login` - Login page
  - [ ] `/dashboard` - Dashboard
  - [ ] `/people` - People list
  - [ ] `/churches` - Churches list
  - [ ] `/contacts` - Contacts list
  - [ ] `/communications` - Communications list
  - [ ] `/tasks` - Tasks list
  - [ ] `/settings` - Settings page
- [ ] Run data retrieval check
  ```bash
  python scripts/check_data_retrieval.py
  ```

### Gmail Sync
- [ ] Verify Gmail API credentials are valid
- [ ] Test Gmail sync functionality
  - [ ] Check for `include_history` parameter errors
  - [ ] Check for `timedelta.minutes` errors
- [ ] Verify background jobs are running correctly

### Environment Variables
- [ ] Verify all environment variables are properly set
  - [ ] `DB_CONNECTION_STRING` - PostgreSQL connection string
  - [ ] `GOOGLE_CLIENT_ID` - Google OAuth client ID
  - [ ] `GOOGLE_CLIENT_SECRET` - Google OAuth client secret
  - [ ] `SECRET_KEY` - Flask secret key
  - [ ] `MAIL_*` - Email configuration variables

## Deployment Process

### Version Control
- [ ] Ensure you're on the stable branch
  ```bash
  git checkout stable-working-version
  ```
- [ ] Commit all changes with descriptive messages
  ```bash
  git add .
  git commit -m "Descriptive message about changes"
  ```

### Server Preparation
- [ ] Update server packages
  ```bash
  sudo apt update && sudo apt upgrade -y
  ```
- [ ] Check disk space
  ```bash
  df -h
  ```
- [ ] Check memory usage
  ```bash
  free -h
  ```

### Application Deployment
- [ ] Pull latest changes on the server
  ```bash
  git pull
  ```
- [ ] Install/update dependencies
  ```bash
  pip install -r requirements.txt
  ```
- [ ] Run database migrations (if applicable)
- [ ] Sync databases
  ```bash
  python scripts/direct_sync.py
  ```
- [ ] Restart application
  ```bash
  sudo systemctl restart mobilize_crm
  ```

## Post-Deployment Verification

### Application Check
- [ ] Verify application is running
  ```bash
  sudo systemctl status mobilize_crm
  ```
- [ ] Check application logs for errors
  ```bash
  sudo journalctl -u mobilize_crm -n 100
  ```

### Functionality Check
- [ ] Verify people/churches pages show data
- [ ] Test Gmail sync functionality
- [ ] Verify authentication works
- [ ] Test email sending
- [ ] Check background jobs are running

## Emergency Rollback Procedure

If deployment fails or critical issues are found:

1. Stop the application
   ```bash
   sudo systemctl stop mobilize_crm
   ```

2. Restore from the latest backup
   ```bash
   cp backups/[latest_backup].db instance/mobilize_crm.db
   ```

3. Checkout the previous stable version
   ```bash
   git checkout [previous_stable_tag]
   ```

4. Restart the application
   ```bash
   sudo systemctl start mobilize_crm
   ```

5. Document the issue and rollback in the project log

## Routine Maintenance

### Daily
- [ ] Check application logs for errors
- [ ] Verify database backups are being created

### Weekly
- [ ] Check disk space usage
- [ ] Verify all functionality is working
- [ ] Test data retrieval

### Monthly
- [ ] Update dependencies (in development environment first)
- [ ] Review and clean up old backups
- [ ] Check for security updates

## Troubleshooting Common Issues

### Database Connection Issues
- Check environment variables
- Verify PostgreSQL server is running
- Check network connectivity

### Authentication Problems
- Verify Google OAuth credentials
- Check redirect URIs in Google Developer Console
- Clear browser cookies and try again

### Gmail Sync Issues
- Check Gmail API credentials
- Verify user has granted necessary permissions
- Look for API quota limits

### Application Not Showing Data
- Run data retrieval check script
- Verify database synchronization
- Check application logs for errors 