import logging
import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from urllib.parse import urlparse

# Add project root directory to path to import app package
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.settings import settings

logger = logging.getLogger(__name__)

def create_database():
    db_url = settings.database_url
    if "sqlite" in db_url:
        logger.info("Using SQLite, skipping database creation.", extra={"type": "db_create_skip", "reason": "sqlite"})
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
            logger.info(f"Database '{dbname}' does not exist. Creating...", extra={"type": "db_create_attempt", "dbname": dbname})
            # CREATE DATABASE cannot use parameters, but dbname is from config
            cur.execute(f"CREATE DATABASE {dbname}")
            logger.info(f"Database '{dbname}' created successfully.", extra={"type": "db_create_success", "dbname": dbname})
        else:
            logger.info(f"Database '{dbname}' already exists.", extra={"type": "db_create_skip", "dbname": dbname, "reason": "already_exists"})
            
        cur.close()
        con.close()

    except psycopg2.OperationalError as e:
        logger.warning(f"Could not connect to Postgres server to check database existence: {e}", extra={"type": "db_connection_error", "host": host, "port": port})
        logger.warning("Ensure PostgreSQL is running and credentials are correct.", extra={"type": "db_connection_error"})
    except Exception as e:
        logger.error(f"Error checking/creating database: {e}", exc_info=True, extra={"type": "db_create_error"})

if __name__ == "__main__":
    create_database()
