"""
Question Management Module

This module defines the Question class which handles interview questions,
acceptance criteria validation, and conversation management. It provides
functionality for checking if user answers meet acceptance criteria,
generating follow-up questions, and creating answer reactions.

The module integrates with a PostgreSQL database to store conversation
history and uses OpenAI's API for natural language processing tasks.

Author: Thesis Research Project
Date: 2024
"""

from utils import get_file_content
from llm_text_generation import generate_text_json, generate_text
import json
import psycopg2
import streamlit as st


class Question:
    """
    A class to represent an interview question with acceptance criteria.
    
    This class manages individual questions in the interview process, including
    validation of user answers against acceptance criteria, generation of
    follow-up questions, and creation of contextual reactions to user responses.
    
    Attributes:
        question (str): The interview question text
        acceptance_criteria (str): Criteria that user answers must meet
    """
    
    def __init__(self, question, acceptance_criteria):
        """
        Initialize a Question instance.
        
        Args:
            question (str): The interview question to be asked
            acceptance_criteria (str): Criteria for accepting user answers
        """
        print(f"Initializing Question with: \nQuestion: {question}\nAcceptance Criteria: {acceptance_criteria}")
        self.question = question
        self.acceptance_criteria = acceptance_criteria

    def get_conversation_history(self, user_id: str) -> str:
        """
        Fetch conversation history from the database for a given user.
        
        This method retrieves all previous questions and answers for a specific
        user from the PostgreSQL database. The history is used to provide
        context for generating more relevant reactions and follow-up questions.
        
        Args:
            user_id (str): Unique identifier for the user
            
        Returns:
            str: Formatted conversation history as a string, or empty string if error
        """
        try:
            # Get database credentials from Streamlit secrets
            creds = st.secrets["postgres"]
            conn = psycopg2.connect(
                host=creds["host"],
                port=creds.get("port", 5432),
                dbname=creds["dbname"],
                user=creds["user"],
                password=creds["password"],
            )
            cur = conn.cursor()

            # Fetch all previous questions and answers for this user
            # Results are ordered by creation time to maintain conversation flow
            cur.execute("""
                SELECT q.question, r.answer_content
                FROM results r
                JOIN questions_and_acceptance q ON r.related_question_id = q.question_id
                WHERE r.user_id = %s
                ORDER BY r.created_at ASC
            """, (user_id,))
            
            # Format the conversation history
            history = []
            for question, answer in cur.fetchall():
                history.append(f"Question: {question}\nAnswer: {answer}\n")
            
            return "\n".join(history)
        except Exception as e:
            print(f"Error fetching conversation history: {e}")
            return ""
        finally:
            # Ensure database connections are properly closed
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

    def acceptance_check(self, answer):
        """
        Check if a user's answer meets the acceptance criteria.
        
        This method uses OpenAI's API to evaluate whether the provided answer
        satisfies the question's acceptance criteria. If the answer fails,
        it generates a follow-up question to help the user provide a better response.
        
        Args:
            answer (str): The user's answer to evaluate
            
        Returns:
            tuple: (bool, str or None) - (accepted, follow_up_question)
                - accepted: True if answer meets criteria, False otherwise
                - follow_up_question: Generated follow-up question if answer failed, None if passed
        """
        print(f"Starting acceptance check for answer: {answer}")
        
        # Load system prompts for acceptance checking and follow-up generation
        print("Loading system prompts...")
        system_prompt_check = get_file_content('prompts/acceptance_general.txt')
        system_prompt_generate = get_file_content('prompts/generate_sub_question.txt')
        
        # Prepare messages for the acceptance check
        print("Preparing messages for acceptance check...")
        messages_check = [
            {"role": "system", "content": system_prompt_check},
            {"role": "user", "content": f"Question: {self.question}\nAcceptance Criteria: {self.acceptance_criteria}\nAnswer: {answer}"}
        ]
        
        # Generate acceptance check response using OpenAI
        print("Generating acceptance check response...")
        response = generate_text_json(messages_check)
        
        # Parse the JSON response to determine if answer passed
        print("Parsing check result...")
        check_result = json.loads(response)

        if check_result['result'] == 'failed':
            print(f"Answer failed acceptance check. Reason: {check_result['reason']}")
            print("Generating follow-up question...")
            # Generate a follow-up question to help the user provide a better answer
            messages_sub_question = [
                {"role": "system", "content": system_prompt_generate},
                {"role": "user", "content": f"Question: {self.question}\nAnswer: {answer}\nReason: {check_result['reason']}"}
            ]
            extra_question = generate_text(messages_sub_question)
            print(f"Generated follow-up question: {extra_question}")
            return False, extra_question
        else:
            print("Answer passed acceptance check")
            return True, None
        
    def generate_answer_reactions(self, answer, user_id: str = None):
        """
        Generate contextual reactions to user answers.
        
        This method creates personalized reactions to user responses based on
        the current question and optionally the user's conversation history.
        The reactions provide feedback and encouragement to maintain engagement.
        
        Args:
            answer (str): The user's answer to react to
            user_id (str, optional): User identifier for accessing conversation history
            
        Returns:
            str: Generated reaction text
        """
        print(f"Generating reaction for answer: {answer}")
        
        # Load the reaction generation prompt
        print("Loading reaction prompt...")
        system_prompt_generate = get_file_content('prompts/generate_answer_reactions.txt')
        
        # Get conversation history if user_id is provided
        # This provides context for more personalized reactions
        conversation_history = ""
        if user_id:
            conversation_history = self.get_conversation_history(user_id)
        
        # Prepare messages for reaction generation
        print("Preparing messages for reaction generation...")
        messages_generate = [
            {"role": "system", "content": system_prompt_generate},
            {"role": "user", "content": f"{conversation_history}Question: {self.question}\nAnswer: {answer}"}
        ]
        
        # Generate the reaction using OpenAI
        print("Generating reaction...")
        response = generate_text(messages_generate)
        print(f"Generated reaction: {response}")
        return response
