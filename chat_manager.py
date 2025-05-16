# chat_manager.py
import streamlit as st
import psycopg2
import uuid
from typing import Optional, Tuple
from question_init import Question


class ChatManager:
    def __init__(self):
        self.conn = None
        self.cur = None

    # ───────────────────────────────────────────────
    #  LOW-LEVEL DB CONNECT / DISCONNECT
    # ───────────────────────────────────────────────
    def connect(self):
        """Open a psycopg2 connection (credentials from st.secrets)."""
        if self.conn:          # already connected
            return
        try:
            creds = st.secrets["connections"]["postgresql"]
            self.conn = psycopg2.connect(
                host=creds["host"],
                port=creds.get("port", 5432),
                dbname=creds["database"],
                user=creds["username"],
                password=creds["password"],
            )
            self.cur = self.conn.cursor()
            print("✅ Database connection established.")
        except Exception as e:
            st.error(f"Database connection failed: {e}")
            print(f"❌ Database connection failed: {e}")

    def disconnect(self):
        """Close cursor & connection gracefully."""
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
        try:
            self.connect()
            # Fetch question
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
                return False, None, None
            question, acceptance_criteria, question_state = result
            question_obj = Question(question, acceptance_criteria)

            is_accepted, follow_up = question_obj.acceptance_check(answer)

            # Store answer
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

            if is_accepted:
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
        Continue the conversation with a user's answer,
        enforcing max_depth for subquestions.
        """
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

        is_accepted, follow_up, _ = self.process_answer(
            user_id, question_id, answer, current_state, subquestion_depth
        )
        reactions = question.generate_answer_reactions(answer)

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
        """Start a new conversation for a user."""
        question, question_id, state = self.get_next_unanswered_question(user_id)
        if question:
            intro_message = self.get_state_intro(state) if state else None
            if intro_message:
                question.question = f"{intro_message}\n\n{question.question}"
        return question, question_id, state

    def get_next_question_by_id(self, question_id: int) -> tuple:
        """Fetch a specific question by ID."""
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
