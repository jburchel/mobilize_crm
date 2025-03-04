#!/bin/bash
# Complete migration script for Render PostgreSQL to new database

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print header
echo -e "${YELLOW}=========================================================${NC}"
echo -e "${YELLOW}   Database Migration: Render PostgreSQL to New Database   ${NC}"
echo -e "${YELLOW}=========================================================${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please create a .env file with your database credentials."
    exit 1
fi

# Function to check if a command was successful
check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Success!${NC}"
    else
        echo -e "${RED}✗ Failed!${NC}"
        echo -e "${RED}Migration process stopped due to an error.${NC}"
        exit 1
    fi
}

# Step 1: Check dependencies
echo -e "\n${YELLOW}Step 1: Checking dependencies...${NC}"
pip install -q sqlalchemy psycopg2-binary python-dotenv tabulate
check_status

# Step 2: Run the migration
echo -e "\n${YELLOW}Step 2: Running data migration...${NC}"
echo "This will migrate data from your Render PostgreSQL database to your new database."
read -p "Do you want to proceed? (y/n): " confirm
if [[ $confirm != [yY] ]]; then
    echo "Migration cancelled."
    exit 0
fi

# Parse command line arguments
MIGRATE_ARGS=""
RESET_ARGS=""
VERIFY_ARGS=""

# Check for --tables argument
if [[ "$*" == *"--tables"* ]]; then
    for arg in "$@"; do
        if [[ $arg == --tables=* ]]; then
            TABLES=${arg#*=}
            MIGRATE_ARGS="$MIGRATE_ARGS --tables $TABLES"
            RESET_ARGS="$RESET_ARGS --tables $TABLES"
            VERIFY_ARGS="$VERIFY_ARGS --tables $TABLES"
        fi
    done
fi

# Check for --source argument
if [[ "$*" == *"--source"* ]]; then
    for arg in "$@"; do
        if [[ $arg == --source=* ]]; then
            SOURCE=${arg#*=}
            MIGRATE_ARGS="$MIGRATE_ARGS --source $SOURCE"
            VERIFY_ARGS="$VERIFY_ARGS --source $SOURCE"
        fi
    done
fi

# Check for --clear-target-tables argument
if [[ "$*" == *"--clear-target-tables"* ]]; then
    MIGRATE_ARGS="$MIGRATE_ARGS --clear-target-tables"
fi

# Run the migration script
python migrate_from_render.py $MIGRATE_ARGS
check_status

# Step 3: Reset sequences
echo -e "\n${YELLOW}Step 3: Resetting PostgreSQL sequences...${NC}"
python reset_sequences.py $RESET_ARGS
check_status

# Step 4: Verify migration
echo -e "\n${YELLOW}Step 4: Verifying migration...${NC}"
python verify_migration.py $VERIFY_ARGS
VERIFY_STATUS=$?

# Print summary
echo -e "\n${YELLOW}=========================================================${NC}"
if [ $VERIFY_STATUS -eq 0 ]; then
    echo -e "${GREEN}Migration completed successfully!${NC}"
    echo -e "${GREEN}All tables have matching record counts.${NC}"
else
    echo -e "${YELLOW}Migration completed with verification warnings.${NC}"
    echo -e "${YELLOW}Some tables have different record counts.${NC}"
    echo "Please check the verification report above for details."
fi
echo -e "${YELLOW}=========================================================${NC}"

# Next steps
echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Update your application's environment variables to point to the new database"
echo "2. Test your application thoroughly with the migrated data"
echo "3. Once confirmed working, you can decommission your old Render database"

exit $VERIFY_STATUS 