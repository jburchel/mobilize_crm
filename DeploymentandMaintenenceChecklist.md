# Mobilize CRM Enhanced Deployment Process

## Overview

The deployment process now follows a three-environment strategy:
1. Development (Local/Dev Environment)
2. Staging (Pre-Production)
3. Production

## Prerequisites

- Python virtual environment
- PostgreSQL installed
- Google Cloud SDK installed
- Access to all three environments
- Proper environment variables set for each environment

## Environment Setup

1. Development Environment
   ```bash
   cp .env.development .env.local
   # Edit .env.local with your development credentials
   ```

2. Staging Environment
   ```bash
   cp .env.staging .env.staging.local
   # Edit .env.staging.local with your staging credentials
   ```

3. Production Environment
   ```bash
   cp .env.production .env.production.local
   # Edit .env.production.local with your production credentials
   ```

## Deployment Process

### 1. Development Phase

1. Work in `stable-working-version` branch
2. Make and test changes locally
3. Run automated tests: `python -m pytest tests/`
4. Verify all features work in development environment
5. Commit changes with clear messages

### 2. Staging Phase

1. Changes are automatically merged to staging
2. Database migrations are tested in dry-run mode
3. Full application is deployed to staging environment
4. Complete testing in staging environment
5. Verify all integrations work

### 3. Production Phase

1. Changes are merged to main branch
2. Database backup is created
3. Migrations are applied
4. Application is deployed
5. Post-deployment verification is performed

## Using the Enhanced Deployment Script

```bash
# Make the script executable
chmod +x enhanced_deploy.sh

# Run the deployment
./enhanced_deploy.sh
```

The script will:
1. Verify your environment
2. Run tests
3. Check configurations
4. Handle database operations
5. Deploy to each environment sequentially
6. Create deployment tags

## Pre-Deployment Checklist

- [ ] All changes are in `stable-working-version` branch
- [ ] All tests pass
- [ ] Database migrations are prepared
- [ ] Environment variables are configured for all environments
- [ ] Development environment testing is complete
- [ ] Required credentials are available

## Deployment Verification

### For Each Environment

1. **Authentication**
   - [ ] Google login works
   - [ ] Session management is correct
   - [ ] Token refresh works

2. **Database**
   - [ ] Migrations applied correctly
   - [ ] Data integrity maintained
   - [ ] Queries perform well

3. **Core Features**
   - [ ] People management works
   - [ ] Church management works
   - [ ] Task management works
   - [ ] Communications work

4. **Integrations**
   - [ ] Gmail sync functions
   - [ ] Google Calendar integration works
   - [ ] Firebase authentication works

## Monitoring

1. **Error Tracking**
   - Check application logs
   - Monitor error rates
   - Review performance metrics

2. **Database Monitoring**
   - Check query performance
   - Monitor connection pool
   - Verify backup process

3. **Integration Health**
   - Monitor API response times
   - Check authentication flows
   - Verify webhook delivery

## Rollback Procedure

If issues are detected:

1. **Immediate Actions**
   ```bash
   # Get the last stable tag
   git tag -l "deployment_*" --sort=-creatordate | head -n 1
   
   # Rollback to last stable version
   git checkout <last-stable-tag>
   ./enhanced_deploy.sh
   ```

2. **Database Rollback**
   ```bash
   # Restore from backup if needed
   pg_restore -d your_database backup_file.sql
   ```

3. **Verification**
   - Verify application is functioning
   - Check data integrity
   - Test critical features

## Maintenance

### Regular Tasks

1. **Daily**
   - Monitor error logs
   - Check integration status
   - Verify backup completion

2. **Weekly**
   - Review performance metrics
   - Check database health
   - Update documentation

3. **Monthly**
   - Security updates
   - Dependency updates
   - Infrastructure review

### Emergency Contacts

- Technical Lead: [Contact Info]
- Database Admin: [Contact Info]
- Infrastructure Team: [Contact Info]

## Security Considerations

1. **Credentials**
   - Never commit .env files
   - Rotate secrets regularly
   - Use secure secret management

2. **Access Control**
   - Review access permissions
   - Audit user roles
   - Monitor suspicious activity

3. **Data Protection**
   - Regular backups
   - Encryption at rest
   - Secure transmission

Remember: Always test thoroughly before deploying to production, and maintain good documentation of your deployment process and any issues encountered. 

# When ready to deploy
./enhanced_deploy.sh 