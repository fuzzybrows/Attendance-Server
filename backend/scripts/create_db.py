import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from urllib.parse import urlparse

# Add parent directory to path to import settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from settings import settings

def create_database():
    db_url = settings.database_url
    if "sqlite" in db_url:
        print("Using SQLite, skipping database creation.")
        return

    # Parse the database URL
    # Format: postgresql://user:password@host:port/dbname
    try:
        url = urlparse(db_url)
        dbname = url.path[1:]
        user = url.username
        password = url.password
        host = url.hostname
        port = url.port
        
        # Default port if not specified
        if not port:
            port = 5432

        # Connect to default 'postgres' database to check/create target db
        con = psycopg2.connect(
            dbname='postgres',
            user=user,
            host=host,
            password=password,
            port=port
        )
        con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = con.cursor()
        
        # Check if database exists
        cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (dbname,))
        exists = cur.fetchone()
        
        if not exists:
            print(f"Database '{dbname}' does not exist. Creating...")
            # CREATE DATABASE cannot use parameters, but dbname is from config
            cur.execute(f"CREATE DATABASE {dbname}")
            print(f"Database '{dbname}' created successfully.")
        else:
            print(f"Database '{dbname}' already exists.")
            
        cur.close()
        con.close()

    except psycopg2.OperationalError as e:
        print(f"Warning: Could not connect to Postgres server to check database existence: {e}")
        print("Ensure PostgreSQL is running and credentials are correct.")
    except Exception as e:
        print(f"Error checking/creating database: {e}")

if __name__ == "__main__":
    create_database()
