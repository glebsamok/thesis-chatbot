"""
Chat Manager Module

This module provides the ChatManager class which handles all aspects of
chatbot conversation management. It manages database connections, processes
user answers, tracks conversation states, and coordinates the flow of
questions and responses in the interview process.

The ChatManager integrates with the Question class for answer validation
and uses PostgreSQL for persistent storage of conversation data.

Key Features:
- Database connection management
- Conversation state tracking
- Answer processing and validation
- Question progression management
- Subquestion handling with depth limits

Author: Thesis Research Project
Date: 2024
"""

# chat_manager.py
import streamlit as st
import psycopg2
import uuid
from typing import Optional, Tuple
from question_init import Question
import os
from dotenv import load_dotenv
load_dotenv()

class ChatManager:
    """
    Manages chatbot conversations and database operations.
    
    This class handles all aspects of the chatbot conversation flow,
    including database connections, answer processing, question progression,
    and conversation state management. It serves as the central coordinator
    for the interview process.
    
    Attributes:
        conn: PostgreSQL connection object
        cur: PostgreSQL cursor object
    """
    
    def __init__(self):
        """Initialize ChatManager with empty database connections."""
        self.conn = None
        self.cur = None

    # ───────────────────────────────────────────────
    #  LOW-LEVEL DB CONNECT / DISCONNECT
    # ───────────────────────────────────────────────
    def connect(self):
        """
        Open a psycopg2 connection using credentials from Streamlit secrets.
        
        This method establishes a connection to the PostgreSQL database
        using credentials stored in Streamlit's secrets management system.
        The connection is stored in instance variables for reuse.
        """
        if self.conn:          # already connected
            return
        try:
            # Get database credentials from Streamlit secrets
            creds = st.secrets["postgres"]
            # Alternative: Use environment variables (commented out)
            # creds = {
            #     "host": os.getenv("PG_HOST"),
            #     "port": os.getenv("PG_PORT"),
            #     "dbname": os.getenv("PG_NAME"),
            #     "user": os.getenv("PG_USER"),
            #     "password": os.getenv("PG_PASS")
            # }
            print(f"Connecting to database with params: {creds}")
            self.conn = psycopg2.connect(
                host=creds["host"],
                port=creds.get("port", 5432),
                dbname=creds["dbname"],
                user=creds["user"],
                password=creds["password"],
            )
            self.cur = self.conn.cursor()
            print("✅ Database connection established.")
        except Exception as e:
            st.error(f"Database connection failed: {e}")
            print(f"❌ Database connection failed: {e}")

    def disconnect(self):
        """
        Close cursor & connection gracefully.
        
        This method ensures proper cleanup of database resources
        by closing both the cursor and connection objects.
        """
        try:
            if self.cur:
                self.cur.close()
            if self.conn:
                self.conn.close()
            self.cur = self.conn = None
            print("🔌 Database connection closed.")
        except Exception as e:
            print(f"Error during disconnect: {e}")

    # ───────────────────────────────────────────────
    #  HIGH-LEVEL BUSINESS LOGIC  (unchanged)
    # ───────────────────────────────────────────────
    def get_last_question_id(self, user_id: str) -> int:
        """
        Get the ID of the last question answered by a user.
        
        This method queries the database to find the most recent question
        that the user has answered, which helps determine the next question
        to present.
        
        Args:
            user_id (str): Unique identifier for the user
            
        Returns:
            int: ID of the last answered question, or 0 if no questions answered
        """
        try:
            self.connect()
            self.cur.execute(
                """
                SELECT related_question_id
                FROM results
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id,),
            )
            result = self.cur.fetchone()
            return int(result[0]) if result else 0
        except Exception as e:
            print(f"Error getting last question_id: {e}")
            return 0
        finally:
            self.disconnect()

    def get_next_question(self, user_id: str) -> tuple:
        """
        Get the next question in sequence for a user.
        
        This method determines the next question to ask based on the user's
        progress. It finds the question that follows the last answered question.
        
        Args:
            user_id (str): Unique identifier for the user
            
        Returns:
            tuple: (Question object, question_id, state) or (None, None, None) if no more questions
        """
        last_qid = self.get_last_question_id(user_id)
        try:
            self.connect()
            self.cur.execute(
                """
                SELECT question_id, question, acceptance_criteria, state
                FROM questions_and_acceptance
                WHERE question_id = %s
                """,
                (last_qid + 1,),
            )
            result = self.cur.fetchone()
            if result:
                question_id, question, acceptance_criteria, state = result
                return Question(question, acceptance_criteria), question_id, state
            return None, None, None
        except Exception as e:
            print(f"Error getting next question: {e}")
            return None, None, None
        finally:
            self.disconnect()

    def get_state_intro(self, state: int) -> Optional[str]:
        """
        Get the introductory message for a specific conversation state.
        
        This method retrieves the introductory text that should be displayed
        when transitioning to a new conversation state or phase.
        
        Args:
            state (int): The conversation state number
            
        Returns:
            str or None: Introductory message for the state, or None if not found
        """
        try:
            self.connect()
            self.cur.execute(
                """
                SELECT intro_message
                FROM states_intro
                WHERE state = %s
                """,
                (state,),
            )
            result = self.cur.fetchone()
            return result[0] if result else None
        except Exception as e:
            print(f"Error getting state intro: {e}")
            return None
        finally:
            self.disconnect()

    def get_subquestion_count(self, user_id: str, question_id: int) -> int:
        """
        Get the number of subquestions asked for a specific main question.
        
        This method counts how many follow-up questions have been asked
        for a particular main question, which helps enforce depth limits.
        
        Args:
            user_id (str): Unique identifier for the user
            question_id (int): ID of the main question
            
        Returns:
            int: Number of subquestions asked for this question
        """
        try:
            self.connect()
            self.cur.execute(
                """
                SELECT COUNT(*)
                FROM results
                WHERE user_id = %s
                  AND related_question_id = %s
                  AND subquestion_depth > 0
                """,
                (user_id, question_id),
            )
            result = self.cur.fetchone()
            return int(result[0]) if result else 0
        except Exception as e:
            print(f"Error getting subquestion count: {e}")
            return 0
        finally:
            self.disconnect()

    def get_max_depth(self, question_id: int) -> int:
        """
        Get the maximum allowed depth for subquestions for a specific question.
        
        This method retrieves the maximum number of follow-up questions
        that can be asked for a particular main question.
        
        Args:
            question_id (int): ID of the question
            
        Returns:
            int: Maximum allowed depth for subquestions (default: 1)
        """
        try:
            self.connect()
            self.cur.execute(
                "SELECT max_depth FROM questions_and_acceptance WHERE question_id = %s",
                (question_id,),
            )
            result = self.cur.fetchone()
            return int(result[0]) if result else 1
        except Exception as e:
            print(f"Error getting max_depth: {e}")
            return 1
        finally:
            self.disconnect()

    def process_answer(
        self,
        user_id: str,
        question_id: str,
        answer: str,
        state: int,
        subquestion_depth: int = 0,
    ) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Process a user's answer to a question.
        
        This method handles the complete processing of a user's answer,
        including validation against acceptance criteria, storage in the
        database, and state updates. It also generates follow-up questions
        when answers don't meet the criteria.
        
        Args:
            user_id (str): Unique identifier for the user
            question_id (str): ID of the question being answered
            answer (str): The user's answer text
            state (int): Current conversation state
            subquestion_depth (int): Depth level for subquestions (default: 0)
            
        Returns:
            tuple: (is_accepted, follow_up_question, new_state)
                - is_accepted: Boolean indicating if answer met criteria
                - follow_up_question: Generated follow-up question if needed
                - new_state: Updated conversation state
        """
        try:
            self.connect()
            print(f"Processing answer for user_id: {user_id}, question_id: {question_id}")
            
            # Fetch question details from database
            self.cur.execute(
                """
                SELECT question, acceptance_criteria, state
                FROM questions_and_acceptance
                WHERE question_id = %s
                """,
                (question_id,),
            )
            result = self.cur.fetchone()
            if not result:
                print(f"No question found for question_id: {question_id}")
                return False, None, None
            question, acceptance_criteria, question_state = result
            question_obj = Question(question, acceptance_criteria)

            # Check if answer meets acceptance criteria
            is_accepted, follow_up = question_obj.acceptance_check(answer)

            # Store answer in database
            try:
                self.cur.execute(
                    """
                    INSERT INTO results (
                        answer_id,
                        answer_content,
                        related_question_id,
                        user_id,
                        state,
                        subquestion_depth
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(uuid.uuid4()),
                        answer,
                        question_id,
                        user_id,
                        state,
                        subquestion_depth,
                    ),
                )
                print(f"Successfully inserted answer for user_id: {user_id}")
            except Exception as e:
                print(f"Error inserting answer: {e}")
                raise

            # Update state if answer was accepted
            if is_accepted:
                try:
                    self.cur.execute(
                        """
                        UPDATE results
                        SET state = %s
                        WHERE user_id = %s
                          AND created_at = (
                              SELECT MAX(created_at) FROM results WHERE user_id = %s
                          )
                        """,
                        (question_state, user_id, user_id),
                    )
                    print(f"Successfully updated state for user_id: {user_id}")
                except Exception as e:
                    print(f"Error updating state: {e}")
                    raise

            self.conn.commit()
            return is_accepted, follow_up, question_state if is_accepted else state
        except Exception as e:
            print(f"Error processing answer: {e}")
            if self.conn:
                self.conn.rollback()
            return False, None, state
        finally:
            self.disconnect()

    def get_conversation_state(self, user_id: str) -> int:
        """
        Get the current conversation state for a user.
        
        This method retrieves the most recent conversation state
        for a user from their answer history.
        
        Args:
            user_id (str): Unique identifier for the user
            
        Returns:
            int: Current conversation state (default: 1)
        """
        try:
            self.connect()
            self.cur.execute(
                """
                SELECT state
                FROM results
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id,),
            )
            result = self.cur.fetchone()
            return result[0] if result else 1  # default initial state = 1
        except Exception as e:
            print(f"Error getting conversation state: {e}")
            return 1
        finally:
            self.disconnect()

    def get_next_unanswered_question(self, user_id: str) -> tuple:
        """
        Get the next unanswered question for a user.
        
        This method finds the next question that the user hasn't answered yet,
        regardless of the sequential order. This is useful for resuming
        conversations or handling skipped questions.
        
        Args:
            user_id (str): Unique identifier for the user
            
        Returns:
            tuple: (Question object, question_id, state) or (None, None, None) if no more questions
        """
        try:
            self.connect()
            self.cur.execute(
                """
                SELECT question_id, question, acceptance_criteria, state
                FROM questions_and_acceptance
                WHERE question_id NOT IN (
                    SELECT related_question_id FROM results WHERE user_id = %s
                )
                ORDER BY question_id ASC
                LIMIT 1
                """,
                (user_id,),
            )
            result = self.cur.fetchone()
            if result:
                question_id, question, acceptance_criteria, state = result
                return Question(question, acceptance_criteria), question_id, state
            return None, None, None
        except Exception as e:
            print(f"Error getting next unanswered question: {e}")
            return None, None, None
        finally:
            self.disconnect()

    def continue_conversation(
        self,
        user_id: str,
        answer: str,
        main_question_id: int = None,
        subquestion_depth: int = 0,
    ) -> tuple:
        """
        Continue the conversation with a user's answer.
        
        This is the main method for handling conversation flow. It processes
        the user's answer, generates reactions, handles follow-up questions,
        and determines the next question to ask. It also enforces maximum
        depth limits for subquestions.
        
        Args:
            user_id (str): Unique identifier for the user
            answer (str): The user's answer text
            main_question_id (int, optional): ID of the main question being answered
            subquestion_depth (int): Current depth level for subquestions
            
        Returns:
            tuple: (is_accepted, reactions, next_question, next_question_id, next_state, next_subquestion_depth, next_main_question_id)
        """
        # Handle main question processing
        if main_question_id is not None:
            question_id = main_question_id
            self.connect()
            self.cur.execute(
                """
                SELECT question, acceptance_criteria, state, max_depth
                FROM questions_and_acceptance
                WHERE question_id = %s
                """,
                (main_question_id,),
            )
            result = self.cur.fetchone()
            self.disconnect()
            if not result:
                return False, "No current question found", None, None, None, None, None
            question_text, acceptance_criteria, current_state, max_depth = result
            question = Question(question_text, acceptance_criteria)
        else:
            # Get next unanswered question
            question, question_id, current_state = self.get_next_unanswered_question(
                user_id
            )
            if not question:
                return False, "No current question found", None, None, None, None, None
            self.connect()
            self.cur.execute(
                "SELECT max_depth FROM questions_and_acceptance WHERE question_id = %s",
                (question_id,),
            )
            max_depth = self.cur.fetchone()[0]
            self.disconnect()

        # Process the answer
        is_accepted, follow_up, _ = self.process_answer(
            user_id, question_id, answer, current_state, subquestion_depth
        )
        reactions = question.generate_answer_reactions(answer, user_id)

        # Handle follow-up questions if answer failed and depth limit not exceeded
        if follow_up and (subquestion_depth + 1) <= max_depth:
            follow_up_question = Question(follow_up, question.acceptance_criteria)
            return (
                is_accepted,
                reactions,
                follow_up_question,
                None,
                question_id,
                subquestion_depth + 1,
                main_question_id or question_id,
            )

        # Move to next main question
        next_question, next_question_id, next_state = self.get_next_unanswered_question(
            user_id
        )
        state_intro = (
            self.get_state_intro(next_state)
            if next_state and next_state != current_state
            else None
        )
        if next_question:
            if state_intro:
                next_question.question = (
                    f"{state_intro}\n\n{next_question.question}"
                )
            return (
                is_accepted,
                reactions,
                next_question,
                next_question_id,
                next_state,
                0,
                None,
            )
        else:
            return is_accepted, reactions, None, None, next_state, 0, None

    def start_conversation(self, user_id: str) -> tuple:
        """
        Start a new conversation for a user.
        
        This method initializes a new conversation by finding the first
        unanswered question and preparing it with any introductory message.
        
        Args:
            user_id (str): Unique identifier for the user
            
        Returns:
            tuple: (Question object, question_id, state)
        """
        question, question_id, state = self.get_next_unanswered_question(user_id)
        if question:
            intro_message = self.get_state_intro(state) if state else None
            if intro_message:
                question.question = f"{intro_message}\n\n{question.question}"
        return question, question_id, state

    def get_next_question_by_id(self, question_id: int) -> tuple:
        """
        Fetch a specific question by ID.
        
        This method retrieves a question directly by its ID, which is useful
        for jumping to specific questions or handling question references.
        
        Args:
            question_id (int): ID of the question to retrieve
            
        Returns:
            tuple: (Question object, question_id, state) or (None, None, None) if not found
        """
        try:
            self.connect()
            self.cur.execute(
                """
                SELECT question_id, question, acceptance_criteria, state
                FROM questions_and_acceptance
                WHERE question_id = %s
                """,
                (question_id,),
            )
            result = self.cur.fetchone()
            if result:
                qid, question, acceptance_criteria, state = result
                return Question(question, acceptance_criteria), qid, state
            return None, None, None
        except Exception as e:
            print(f"Error getting next question: {e}")
            return None, None, None
        finally:
            self.disconnect()
