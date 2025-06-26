"""
Chatbot Interface Module

This module provides the main Streamlit web interface for the chatbot application.
It creates an interactive chat interface where users can engage with the
AI interviewer, answer questions, and receive feedback. The interface
manages session state, handles user input, and coordinates with the
ChatManager for conversation flow.

Key Features:
- Interactive chat interface with message history
- Session state management for user persistence
- URL parameter support for user identification
- Real-time conversation flow with reactions and follow-ups
- Modern UI with custom styling

Author: Thesis Research Project
Date: 2024
"""

import streamlit as st
import uuid
from chat_manager import ChatManager
from datetime import datetime

# Initialize session state variables
# These persist across interactions within a single session
if 'user_id' not in st.session_state:
    # Get user_id from URL query parameters for external linking
    if 'user_id' in st.query_params:
        st.session_state.user_id = st.query_params['user_id']  # Store the exact user_id from URL
    else:
        st.session_state.user_id = str(uuid.uuid4())  # Generate random UUID only if no user_id in URL
    # print(f"User ID: {st.session_state.user_id}")

# Initialize chat history as an empty list
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Initialize current question tracking
if 'current_question' not in st.session_state:
    st.session_state.current_question = None
if 'current_question_id' not in st.session_state:
    st.session_state.current_question_id = None
if 'current_state' not in st.session_state:
    st.session_state.current_state = None

# Initialize subquestion tracking for follow-up questions
if 'main_question_id' not in st.session_state:
    st.session_state.main_question_id = None
if 'subquestion_depth' not in st.session_state:
    st.session_state.subquestion_depth = 0

# Initialize chat manager instance
if 'chat_manager' not in st.session_state:
    st.session_state.chat_manager = ChatManager()

def format_message(role, content):
    """
    Format a message for display in the chat interface.
    
    This function adds appropriate emojis and formatting to distinguish
    between user and assistant messages in the chat display.
    
    Args:
        role (str): Either "assistant" or "user"
        content (str): The message content to format
        
    Returns:
        str: Formatted message with emoji prefix
    """
    if role == "assistant":
        return f"🤖 {content}"
    return f"👤 {content}"

def add_to_history(role, content):
    """
    Add a message to the chat history with timestamp.
    
    This function appends a new message to the session's chat history,
    including metadata like role and timestamp for tracking purposes.
    
    Args:
        role (str): The role of the message sender ("assistant" or "user")
        content (str): The message content
    """
    st.session_state.chat_history.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now()
    })

def get_chat_history_text():
    """
    Get formatted chat history for use in prompts.
    
    This function converts the chat history into a text format that can
    be used as context for AI models or for debugging purposes.
    
    Returns:
        str: Formatted chat history as a single string
    """
    history_text = ""
    for msg in st.session_state.chat_history:
        role = "Assistant" if msg["role"] == "assistant" else "User"
        history_text += f"{role}: {msg['content']}\n"
    return history_text

# Set page configuration for the Streamlit app
st.set_page_config(
    page_title="Work situations interview",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS for modern styling and improved user experience
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

# Main title for the application
st.title("🤖 xSurvey Demo Chatbot")

# Welcome message for new sessions (commented out)
# if not st.session_state.chat_history:
#     st.markdown(
#         """
#         <div style='margin-bottom: 1.5rem; font-size: 1.1rem;'>
#         This AI-supported interviewer will help you think deeper about work situations. Your responses are private and not used outside of the scope of this study. Please type your answer below to begin.
#         </div>
#         """,
#         unsafe_allow_html=True
#     )

# Initialize chat if not already started
# This ensures the first question is loaded when the session begins
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
# This shows all previous messages in the conversation
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat input section
# This handles user input and processes responses
if prompt := st.chat_input("Type your answer here..."):
    # Display user message immediately
    add_to_history("user", prompt)
    with st.chat_message("user"):
        st.write(prompt)

    # Process the answer through the chat manager
    # This handles validation, reactions, and next question determination
    is_accepted, reaction, next_question, next_question_id, new_state, next_subquestion_depth, next_main_question_id = st.session_state.chat_manager.continue_conversation(
        st.session_state.user_id,
        prompt,
        st.session_state.main_question_id,
        st.session_state.subquestion_depth
    )

    # Display reaction if there is one
    # Reactions provide feedback and encouragement to users
    if reaction:
        add_to_history("assistant", reaction)
        with st.chat_message("assistant"):
            st.write(reaction)

    # Handle follow-up question (subquestion)
    # This occurs when the user's answer doesn't meet acceptance criteria
    if next_question and next_main_question_id:
        st.session_state.main_question_id = next_main_question_id
        st.session_state.subquestion_depth = next_subquestion_depth
        add_to_history("assistant", next_question.question)
        with st.chat_message("assistant"):
            st.write(f"{next_question.question}")
    # Handle next main question
    # This occurs when moving to the next primary question in the sequence
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
        # Conversation completed
        # Reset subquestion tracking and show completion message
        st.session_state.main_question_id = None
        st.session_state.subquestion_depth = 0
        add_to_history("assistant", "Thank you for completing the interview!")
        with st.chat_message("assistant"):
            st.write("Thank you for completing the interview!")

# Sidebar with session management controls
with st.sidebar:
    st.markdown("---")
    # Restart button to begin a new session
    if st.button("Start New Session"):
        # Preserve user_id from URL if available, otherwise generate new one
        if 'user_id' in st.query_params:
            st.session_state.user_id = st.query_params['user_id']  # Keep the same user_id from URL
        else:
            st.session_state.user_id = str(uuid.uuid4())
        # Reset all session state variables
        st.session_state.chat_history = []
        st.session_state.current_question = None
        st.session_state.current_question_id = None
        st.session_state.current_state = None
        st.session_state.main_question_id = None
        st.session_state.subquestion_depth = 0
        st.rerun()  # Refresh the page to start fresh
