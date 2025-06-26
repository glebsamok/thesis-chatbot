"""
Fine-tuning Data Preparation Script

This script prepares data for fine-tuning OpenAI models by generating
reasoning explanations for trait classifications. It processes a dataset
of questions and answers, then uses GPT-4 to generate step-by-step
reasoning for why each answer was classified with specific trait labels.

The script creates a new dataset with reasoning explanations that can
be used to train models to understand the classification process and
provide more interpretable predictions.

Key Features:
- Processes question-answer pairs with trait labels
- Generates reasoning explanations using GPT-4
- Creates structured training data for fine-tuning
- Handles error cases and parsing issues

Author: Thesis Research Project
Date: 2024
"""

from openai import OpenAI
from dotenv import load_dotenv
import streamlit as st
import pandas as pd
import os
import json
from sklearn.model_selection import train_test_split
load_dotenv()

# System prompt for generating reasoning explanations
# This prompt instructs the model to analyze answers and provide
# step-by-step reasoning for trait classifications
prompt_to_cot_gen = '''You are an experienced organizational psychologist.

You will receive questions which were asked to the users, their answers and correct labels for interpersonal traits

TASK  
1. Read the respondent's answers and correct classification for each traits.  
2. Think **step-by-step** about the evidence for each trait and write the thinking process which highlights the evidence and shows the thinking process of proving this label:  
   • Emotional Intelligence (EI) — recognising and appropriately expressing one's own and others' emotions.  
   • Perspective Taking (PT) — understanding the other person's viewpoint and reasons for their behaviour.  
   • Learning Orientation (LO) — actively seeking to learn, request feedback, and draw lessons.  
   • Social Curiosity (SC) — interest in new people, asking questions, expanding one's network.    

   You must mention which parts of the answer led to the label and mention correct labels in the answer with the conclusions

3. Output in **exactly** the JSON format below:  

{"rationale":"<2–3-sentence thought chain process summary>"}'''

# API key configuration
# api_key = st.secrets["OPENAI_API_KEY"]
api_key = os.getenv("OPENAI_API_KEY")

# Load the dataset for processing
dataset2_reduced = pd.read_csv('dataset2_reduced_with_reasoning.csv')

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

def generate_text_json(messages, model='gpt-4.1', temperature=0.3):
    """
    Generate structured JSON responses using OpenAI's API.
    
    This function is used to get structured responses from the model
    for reasoning generation tasks.
    
    Args:
        messages (list): List of message dictionaries
        model (str): OpenAI model to use
        temperature (float): Controls randomness in generation
        
    Returns:
        str: JSON-formatted response from the model
    """
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content

def generate_row_dict(row):
    """
    Generates a dictionary for a single row with questions and answers.

    This function formats a single row of the dataset into a structured
    dictionary that can be used as input for the reasoning generation
    process. It separates questions and answers from the trait labels.

    Args:
        row (pd.Series): A single row of the dataframe.

    Returns:
        dict: A dictionary representing the row's data in the specified format.
    """
    row_dict = {}
    headers = row.index.tolist()
    # Exclude the last 5 columns (labels) from the questions/answers
    question_headers = headers[:-5]

    # Format each question-answer pair
    for i, header in enumerate(question_headers):
        row_dict[f'Question {i+1}: {header}'] = f'\n\nAnswer {i+1}: {row[header]}'

    # Add the correct labels from the last 5 columns
    label_headers = headers[-5:]
    correct_labels = {header: row[header] for header in label_headers}
    row_dict['Correct Labels'] = correct_labels

    return row_dict

# Initialize the reasoning column in the dataset
dataset2_reduced['reasoning'] = None

# Process each row in the dataset to generate reasoning explanations
for index, row in dataset2_reduced.iterrows():
    # Generate the dictionary for the current row
    row_data = generate_row_dict(row)

    # Construct the full prompt by combining the initial prompt and the row data
    full_prompt = prompt_to_cot_gen + "\n\n" + str(row_data) # Convert dict to string for the prompt

    try:
        # Call the LLM with the full prompt
        messages=[
                {"role": "system", "content": prompt_to_cot_gen},
                {"role": "user", "content": str(row_data)}
            ]
        response = generate_text_json(messages=messages)
        print(f'iterating row {index}, result: {response}')
        # Parse the JSON response
        response_dict = json.loads(response)
        # Extract the 'rationale' and store it in the 'reasoning' column
        if 'rationale' in response_dict:
            dataset2_reduced.at[index, 'reasoning'] = response_dict['rationale']
        else:
            print(f"Row {index}: 'rationale' key not found in LLM response: {response}")
            dataset2_reduced.at[index, 'reasoning'] = "Parsing Error: 'rationale' key missing."

    except Exception as e:
        print(f"Row {index}: Error calling LLM or processing response - {e}")
        dataset2_reduced.at[index, 'reasoning'] = f"Error processing row: {e}"

# Display the dataframe with the new 'reasoning' column
# Show a sample of the results including trait labels and generated reasoning
print(dataset2_reduced[['emotional_intelligence_label', 'perspective_taking_label', 'learning_orientation_label', 'social_curiosity_label', 'big5_label', 'reasoning']].head())

# Save the processed dataset with reasoning explanations
dataset2_reduced.to_csv('dataset2_reduced_with_reasoning_full.csv', index=False)

