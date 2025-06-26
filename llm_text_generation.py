"""
LLM Text Generation Module

This module provides functions for generating text using OpenAI's API.
It handles both structured JSON responses and free-form text generation
for various chatbot functionalities including acceptance checking,
follow-up question generation, and answer reactions.

The module uses OpenAI's GPT models and supports both development
(environment variables) and production (Streamlit secrets) configurations.

Key Functions:
- generate_text_json: Generate structured JSON responses
- generate_text: Generate free-form text responses

Author: Thesis Research Project
Date: 2024
"""

from openai import OpenAI
from dotenv import load_dotenv
import streamlit as st
import os
load_dotenv()

# API key configuration
# Priority: Streamlit secrets (production) > Environment variables (development)
api_key = st.secrets["OPENAI_API_KEY"]
# api_key = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

def generate_text_json(messages, model='gpt-4.1', temperature=0.3):
    """
    Generate structured JSON responses using OpenAI's API.
    
    This function is used for tasks that require structured output,
    such as acceptance criteria checking where the response needs
    to be parsed as JSON with specific fields.
    
    Args:
        messages (list): List of message dictionaries with 'role' and 'content'
        model (str): OpenAI model to use (default: 'gpt-4.1')
        temperature (float): Controls randomness in generation (0.0-1.0, default: 0.3)
        
    Returns:
        str: JSON-formatted response from the model
        
    Example:
        >>> messages = [
        ...     {"role": "system", "content": "You are a helpful assistant."},
        ...     {"role": "user", "content": "Check if this answer meets criteria."}
        ... ]
        >>> response = generate_text_json(messages)
        >>> print(response)
        '{"result": "passed", "reason": "Answer meets all criteria"}'
    """
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content

def generate_text(messages, model='gpt-4.1', temperature=0.3):
    """
    Generate free-form text responses using OpenAI's API.
    
    This function is used for tasks that require natural language output,
    such as generating follow-up questions, reactions, or explanations.
    
    Args:
        messages (list): List of message dictionaries with 'role' and 'content'
        model (str): OpenAI model to use (default: 'gpt-4.1')
        temperature (float): Controls randomness in generation (0.0-1.0, default: 0.3)
        
    Returns:
        str: Natural language response from the model
        
    Example:
        >>> messages = [
        ...     {"role": "system", "content": "You are a helpful interviewer."},
        ...     {"role": "user", "content": "Generate a follow-up question."}
        ... ]
        >>> response = generate_text(messages)
        >>> print(response)
        'Could you provide a specific example of that situation?'
    """
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature
    )
    return response.choices[0].message.content


