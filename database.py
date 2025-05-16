import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def init_database():
    # Database connection parameters
    db_params = {
        'dbname': os.getenv('PG_NAME', 'pgvector'),  # Your database name
        'user': os.getenv('PG_USER', 'gleb'),  # Your username
        'password': os.getenv('PG_PASS', '1234'),  # Your password
        'host': os.getenv('PG_HOST', 'localhost'),  # Your host
        'port': os.getenv('PG_PORT', '5433')  # Your port
    }

    try:
        # Connect to PostgreSQL server
        conn = psycopg2.connect(**db_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # Create questions_and_acceptance table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS questions_and_acceptance (
                question_id INTEGER PRIMARY KEY,
                question TEXT NOT NULL,
                acceptance_criteria TEXT NOT NULL,
                state INTEGER NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Create results table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS results (
                answer_id UUID PRIMARY KEY,
                answer_content TEXT NOT NULL,
                related_question_id INTEGER NOT NULL,
                user_id UUID NOT NULL,
                state INTEGER NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (related_question_id) REFERENCES questions_and_acceptance(question_id)
            );
        """)

        # Create states_intro table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS states_intro (
                msg_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                state INTEGER NOT NULL,
                intro_message TEXT NOT NULL
            );
        """)

        print("Database tables created successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    init_database()
