"""
Migration to remove JSONField CHECK constraints by recreating tables without them.
This fixes the JSON_VALID() error in SQLite.
"""
from django.db import migrations


def remove_jsonfield_constraints(apps, schema_editor):
    """Remove JSONField CHECK constraints by recreating tables without them."""
    db_alias = schema_editor.connection.alias
    connection = schema_editor.connection
    
    with connection.cursor() as cursor:
        # Disable foreign key checks temporarily
        cursor.execute("PRAGMA foreign_keys=OFF")
        
        try:
            # Get the current table schemas
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='pos_possession'")
            pos_session_result = cursor.fetchone()
            
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='pos_offlinetransaction'")
            offline_trans_result = cursor.fetchone()
            
            if pos_session_result:
                pos_session_sql = pos_session_result[0]
                if 'JSON_VALID' in pos_session_sql or 'json_valid' in pos_session_sql.lower():
                    print("Recreating pos_possession table without JSON_VALID constraint...")
                    
                    # Backup data
                    cursor.execute("CREATE TABLE pos_possession_backup AS SELECT * FROM pos_possession")
                    
                    # Drop old table
                    cursor.execute("DROP TABLE pos_possession")
                    
                    # Remove CHECK constraints with JSON_VALID
                    import re
                    # Remove CHECK constraints that contain JSON_VALID
                    new_sql = re.sub(r',\s*CHECK\s*\([^)]*JSON_VALID[^)]*\)', '', pos_session_sql, flags=re.IGNORECASE)
                    new_sql = re.sub(r'CHECK\s*\([^)]*JSON_VALID[^)]*\)\s*,', '', new_sql, flags=re.IGNORECASE)
                    
                    cursor.execute(new_sql)
                    
                    # Restore data
                    cursor.execute("INSERT INTO pos_possession SELECT * FROM pos_possession_backup")
                    cursor.execute("DROP TABLE pos_possession_backup")
                    print("pos_possession table recreated successfully")
            
            if offline_trans_result:
                offline_trans_sql = offline_trans_result[0]
                if 'JSON_VALID' in offline_trans_sql or 'json_valid' in offline_trans_sql.lower():
                    print("Recreating pos_offlinetransaction table without JSON_VALID constraint...")
                    
                    # Backup data
                    cursor.execute("CREATE TABLE pos_offlinetransaction_backup AS SELECT * FROM pos_offlinetransaction")
                    
                    # Drop old table
                    cursor.execute("DROP TABLE pos_offlinetransaction")
                    
                    # Remove CHECK constraints with JSON_VALID
                    import re
                    new_sql = re.sub(r',\s*CHECK\s*\([^)]*JSON_VALID[^)]*\)', '', offline_trans_sql, flags=re.IGNORECASE)
                    new_sql = re.sub(r'CHECK\s*\([^)]*JSON_VALID[^)]*\)\s*,', '', new_sql, flags=re.IGNORECASE)
                    
                    cursor.execute(new_sql)
                    
                    # Restore data
                    cursor.execute("INSERT INTO pos_offlinetransaction SELECT * FROM pos_offlinetransaction_backup")
                    cursor.execute("DROP TABLE pos_offlinetransaction_backup")
                    print("pos_offlinetransaction table recreated successfully")
        
        finally:
            # Re-enable foreign key checks
            cursor.execute("PRAGMA foreign_keys=ON")


def reverse_removal(apps, schema_editor):
    """Reverse operation - not needed as we're keeping TextField."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0005_convert_jsonfield_to_textfield'),
    ]

    operations = [
        migrations.RunPython(remove_jsonfield_constraints, reverse_removal),
    ]
