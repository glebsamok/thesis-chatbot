from openai import OpenAI
from dotenv import load_dotenv
import streamlit as st

api_key = st.secrets["OPENAI_API_KEY"]

client = OpenAI(api_key=api_key)

def generate_text_json(messages, model='gpt-4.1', temperature=0.3):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content

def generate_text(messages, model='gpt-4.1', temperature=0.3):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature
    )
    return response.choices[0].message.content


