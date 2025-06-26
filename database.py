"""
Database Management Module

This module handles PostgreSQL database operations for the chatbot application.
It provides functions for initializing the database schema, dropping tables,
and managing database connections. The module uses environment variables
for database configuration and supports both development and production setups.

The database schema includes tables for:
- questions_and_acceptance: Stores interview questions and their acceptance criteria
- results: Stores user answers and conversation data
- states_intro: Stores introductory messages for different conversation states

Author: Thesis Research Project
Date: 2024
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def drop_tables():
    """
    Drop the results table from the database.
    
    This function is used for development and testing purposes to reset
    the conversation data while preserving the question structure.
    It only drops the results table, keeping questions_and_acceptance
    and states_intro tables intact.
    
    Note: This is a destructive operation and should be used with caution.
    """
    # Database connection parameters from environment variables
    db_params = {
        'dbname': os.getenv('PG_NAME', 'pgvector'),
        'user': os.getenv('PG_USER', 'gleb'),
        'password': os.getenv('PG_PASS', '1234'),
        'host': os.getenv('PG_HOST', 'localhost'),
        'port': os.getenv('PG_PORT', '5433')
    }

    try:
        # Establish database connection
        conn = psycopg2.connect(**db_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # Drop only the results table
        # CASCADE ensures that any dependent objects are also dropped
        cur.execute("""
            DROP TABLE IF EXISTS results CASCADE;
        """)
        
        print("Results table dropped successfully")
    except Exception as e:
        print(f"Error dropping results table: {e}")
    finally:
        # Ensure proper cleanup of database connections
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

def init_database():
    """
    Initialize the database schema by creating all necessary tables.
    
    This function creates the complete database schema for the chatbot application.
    It creates three main tables:
    1. questions_and_acceptance: Stores interview questions and criteria
    2. results: Stores user responses and conversation data
    3. states_intro: Stores introductory messages for different states
    
    The function uses environment variables for database configuration
    and provides sensible defaults for development environments.
    """
    # Database connection parameters with fallback defaults
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
        # This table stores the interview questions and their acceptance criteria
        # question_id: Primary key for identifying questions
        # question: The actual question text
        # acceptance_criteria: Criteria that answers must meet
        # state: Integer representing the conversation state/phase
        # created_at: Timestamp for when the question was created
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
        # This table stores all user responses and conversation data
        # answer_id: UUID primary key for each answer
        # answer_content: The user's actual response text
        # related_question_id: Foreign key linking to the question
        # user_id: Identifier for the user providing the answer
        # state: Current conversation state when answer was given
        # created_at: Timestamp for when the answer was recorded
        cur.execute("""
            CREATE TABLE IF NOT EXISTS results (
                answer_id UUID PRIMARY KEY,
                answer_content TEXT NOT NULL,
                related_question_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                state INTEGER NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (related_question_id) REFERENCES questions_and_acceptance(question_id)
            );
        """)

        # Create states_intro table
        # This table stores introductory messages for different conversation states
        # msg_id: UUID primary key for each message
        # state: Integer representing the conversation state
        # intro_message: The introductory text for that state
        cur.execute("""
            CREATE TABLE IF NOT EXISTS states_intro (
                msg_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                state INTEGER NOT NULL,
                intro_message TEXT NOT NULL
            );
        """)
        
        print("Tables created successfully")
    except Exception as e:
        print(f"Error creating tables: {e}")
    finally:
        # Ensure proper cleanup of database connections
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    # Main execution block for database initialization
    # Uncomment the line below to drop existing tables before creating new ones
    # drop_tables()  # First drop existing tables
    init_database()  # Then create new tables with updated schema
