from utils import get_file_content
from llm_text_generation import generate_text_json, generate_text
import json
import psycopg2
import streamlit as st


class Question:
    def __init__(self, question, acceptance_criteria):
        print(f"Initializing Question with: \nQuestion: {question}\nAcceptance Criteria: {acceptance_criteria}")
        self.question = question
        self.acceptance_criteria = acceptance_criteria

    def get_conversation_history(self, user_id: str) -> str:
        """Fetch conversation history from the database for a given user."""
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
            cur.execute("""
                SELECT q.question, r.answer_content
                FROM results r
                JOIN questions_and_acceptance q ON r.related_question_id = q.question_id
                WHERE r.user_id = %s
                ORDER BY r.created_at ASC
            """, (user_id,))
            
            history = []
            for question, answer in cur.fetchall():
                history.append(f"Question: {question}\nAnswer: {answer}\n")
            
            return "\n".join(history)
        except Exception as e:
            print(f"Error fetching conversation history: {e}")
            return ""
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

    def acceptance_check(self, answer):
        print(f"Starting acceptance check for answer: {answer}")
        
        print("Loading system prompts...")
        system_prompt_check = get_file_content('prompts/acceptance_general.txt')
        system_prompt_generate = get_file_content('prompts/generate_sub_question.txt')
        
        print("Preparing messages for acceptance check...")
        messages_check = [
            {"role": "system", "content": system_prompt_check},
            {"role": "user", "content": f"Question: {self.question}\nAcceptance Criteria: {self.acceptance_criteria}\nAnswer: {answer}"}
        ]
        
        print("Generating acceptance check response...")
        response = generate_text_json(messages_check)
        
        print("Parsing check result...")
        check_result = json.loads(response)

        if check_result['result'] == 'failed':
            print(f"Answer failed acceptance check. Reason: {check_result['reason']}")
            print("Generating follow-up question...")
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
        print(f"Generating reaction for answer: {answer}")
        
        print("Loading reaction prompt...")
        system_prompt_generate = get_file_content('prompts/generate_answer_reactions.txt')
        
        # Get conversation history if user_id is provided
        conversation_history = ""
        if user_id:
            conversation_history = self.get_conversation_history(user_id)
        
        print("Preparing messages for reaction generation...")
        messages_generate = [
            {"role": "system", "content": system_prompt_generate},
            {"role": "user", "content": f"{conversation_history}Question: {self.question}\nAnswer: {answer}"}
        ]
        
        print("Generating reaction...")
        response = generate_text(messages_generate)
        print(f"Generated reaction: {response}")
        return response
