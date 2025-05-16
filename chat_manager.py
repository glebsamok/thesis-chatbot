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

    # ──────────────────────────────────────────────────────────────
    # DB CONNECTION HELPERS
    # ──────────────────────────────────────────────────────────────
    def connect(self):
        """Open a psycopg2 connection using credentials from st.secrets."""
        if self.conn:                      # already connected
            return
        try:
            creds = st.secrets["connections.postgresql"]     # <── defined in secrets.toml
            self.conn = psycopg2.connect(
                host=creds["host"],
                port=creds.get("port", 5432),
                dbname=creds["dbname"],
                user=creds["user"],
                password=creds["password"],
            )
            self.cur = self.conn.cursor()
            # print is visible in Cloud logs
            print("✅ Database connection established.")
        except Exception as e:
            st.error(f"Database connection failed: {e}")
            print(f"❌ Database connection failed: {e}")

    def disconnect(self):
        """Close cursor and connection cleanly."""
        try:
            if self.cur:
                self.cur.close()
            if self.conn:
                self.conn.close()
            self.cur = self.conn = None
            print("🔌 Database connection closed.")
        except Exception as e:
            print(f"Error during disconnect: {e}")

    # ──────────────────────────────────────────────────────────────
    #  ALL BUSINESS-LOGIC METHODS BELOW ARE UNCHANGED
    #  (they still use self.connect(), self.cur, etc.)
    # ──────────────────────────────────────────────────────────────
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
            # fetch question
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

            # store answer
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
            self.conn.rollback()
            return False, None, state
        finally:
            self.disconnect()

    # … ⟨keep the rest of your methods unchanged⟩ …
