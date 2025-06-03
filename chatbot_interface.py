import streamlit as st
import uuid
from chat_manager import ChatManager
from datetime import datetime

# Initialize session state
if 'user_id' not in st.session_state:
    # Try to get user_id from URL query parameters
    if 'user_id' in st.query_params:
        st.session_state.user_id = st.query_params['user_id']
    else:
        st.session_state.user_id = str(uuid.uuid4())
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'current_question' not in st.session_state:
    st.session_state.current_question = None
if 'current_question_id' not in st.session_state:
    st.session_state.current_question_id = None
if 'current_state' not in st.session_state:
    st.session_state.current_state = None
if 'main_question_id' not in st.session_state:
    st.session_state.main_question_id = None
if 'subquestion_depth' not in st.session_state:
    st.session_state.subquestion_depth = 0
if 'chat_manager' not in st.session_state:
    st.session_state.chat_manager = ChatManager()

def format_message(role, content):
    """Format a message for display in the chat."""
    if role == "assistant":
        return f"🤖 {content}"
    return f"👤 {content}"

def add_to_history(role, content):
    """Add a message to the chat history."""
    st.session_state.chat_history.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now()
    })

def get_chat_history_text():
    """Get formatted chat history for the prompt."""
    history_text = ""
    for msg in st.session_state.chat_history:
        role = "Assistant" if msg["role"] == "assistant" else "User"
        history_text += f"{role}: {msg['content']}\n"
    return history_text

# Set page config
st.set_page_config(
    page_title="Work situations interview",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS for a modern look
st.markdown("""
    <style>
    .stTextInput>div>div>input {
        background-color: #f0f2f6;
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .chat-message.user {
        background-color: #2b313e;
    }
    .chat-message.assistant {
        background-color: #475063;
    }
    .chat-message .content {
        display: flex;
        margin-top: 0.5rem;
    }
    .sidebar-section {
        margin-bottom: 2rem;
    }
    .sidebar-header {
        font-weight: bold;
        font-size: 1.2rem;
        margin-bottom: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# Title
st.title("🤖 xSurvey Demo Chatbot")

# Welcome message for new sessions
# if not st.session_state.chat_history:
#     st.markdown(
#         """
#         <div style='margin-bottom: 1.5rem; font-size: 1.1rem;'>
#         This AI-supported interviewer will help you think deeper about work situations. Your responses are private and not used outside of the scope of this study. Please type your answer below to begin.
#         </div>
#         """,
#         unsafe_allow_html=True
#     )

# Initialize chat if not started
if not st.session_state.current_question:
    question, question_id, state = st.session_state.chat_manager.start_conversation(st.session_state.user_id)
    if question:
        st.session_state.current_question = question
        st.session_state.current_question_id = question_id
        st.session_state.current_state = state
        st.session_state.main_question_id = None
        st.session_state.subquestion_depth = 0
        add_to_history("assistant", question.question)

# Display chat history
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat input
if prompt := st.chat_input("Type your answer here..."):
    # Display user message
    add_to_history("user", prompt)
    with st.chat_message("user"):
        st.write(prompt)

    # Process the answer
    is_accepted, reaction, next_question, next_question_id, new_state, next_subquestion_depth, next_main_question_id = st.session_state.chat_manager.continue_conversation(
        st.session_state.user_id,
        prompt,
        st.session_state.main_question_id,
        st.session_state.subquestion_depth
    )

    # Display reaction if there is one
    if reaction:
        add_to_history("assistant", reaction)
        with st.chat_message("assistant"):
            st.write(reaction)

    # Handle follow-up question
    if next_question and next_main_question_id:
        st.session_state.main_question_id = next_main_question_id
        st.session_state.subquestion_depth = next_subquestion_depth
        add_to_history("assistant", next_question.question)
        with st.chat_message("assistant"):
            st.write(f"{next_question.question} + {st.query_params['user_id']}")
    # Handle next main question
    elif next_question:
        st.session_state.current_question = next_question
        st.session_state.current_question_id = next_question_id
        st.session_state.current_state = new_state
        st.session_state.main_question_id = None
        st.session_state.subquestion_depth = 0
        add_to_history("assistant", next_question.question)
        with st.chat_message("assistant"):
            st.write(next_question.question)
    else:
        st.session_state.main_question_id = None
        st.session_state.subquestion_depth = 0
        add_to_history("assistant", "Thank you for completing the interview!")
        with st.chat_message("assistant"):
            st.write("Thank you for completing the interview!")

# Sidebar with only restart button
with st.sidebar:
    st.markdown("---")
    if st.button("Start New Session"):
        st.session_state.user_id = str(uuid.uuid4())
        st.session_state.chat_history = []
        st.session_state.current_question = None
        st.session_state.current_question_id = None
        st.session_state.current_state = None
        st.session_state.main_question_id = None
        st.session_state.subquestion_depth = 0
        st.rerun()
