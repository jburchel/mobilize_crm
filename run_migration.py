from migrations.rename_role_to_church_role import run_migration

if __name__ == "__main__":
    print("Running migration to rename 'role' to 'church_role'...")
    run_migration()
    print("Migration completed.") 