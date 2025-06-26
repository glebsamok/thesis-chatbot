"""
Data Merging and Processing Script for Chatbot Analysis

This script merges chatbot conversation data with external dataset information
and formats the combined data for further analysis. It processes question-answer
pairs from chatbot interactions and prepares them for trait classification.

Key Functions:
- Merges chatbot answers with external dataset using user_id
- Collects all Q&A pairs per user into consolidated text format
- Exports processed data to JSONL format for downstream analysis

Author: Thesis Research Project
Date: 2024
"""

import pandas as pd
import json

# Load the datasets
# chatbot_answers_export.csv contains the raw conversation data from the chatbot
chatbot_answers = pd.read_csv('chatbot_answers_export.csv')

# dataset_to_merge.csv contains external data (likely demographic or trait information)
dataset_to_merge = pd.read_csv('dataset_to_merge.csv')

# Rename the user_id column in dataset_to_merge to match the format in chatbot_answers
# The original column name appears to be a validation question asking users to write a number
dataset_to_merge = dataset_to_merge.rename(
    columns={"If you're still paying attention write down this number: [int-1:100000]": "user_id"}
)

# Merge the datasets on 'user_id' column using left join
# This preserves all chatbot answers and adds matching external data where available
merged_dataset = pd.merge(chatbot_answers, dataset_to_merge, on='user_id', how='left')

def collect_qa_per_user(df, user_id_col='user_id', question_col='question', answer_col='full_answer'):
    """
    For each user, collect all questions and answers into a single JSON object with a 'text' field.
    Returns a list of dicts: [{'user_id': ..., 'text': ...}, ...]
    
    This function consolidates all conversation data for each user into a single text block,
    which is useful for natural language processing and trait classification tasks.
    
    Args:
        df (pd.DataFrame): Merged dataset containing user conversations
        user_id_col (str): Column name containing user identifiers
        question_col (str): Column name containing question text
        answer_col (str): Column name containing user answers
        
    Returns:
        list: List of dictionaries with user_id and consolidated text for each user
    """
    results = []
    # Group the dataframe by user_id to process each user's conversations separately
    for user_id, group in df.groupby(user_id_col):
        qa_pairs = []
        # Iterate through each question-answer pair for this user
        for i, row in enumerate(group.itertuples(), 1):
            question = getattr(row, question_col)
            answer = getattr(row, answer_col)
            # Format each Q&A pair with numbering for clarity
            qa_pairs.append(f"Question {i}: {question}, Answer {i}: {answer} \n\n")
        # Join all Q&A pairs for this user into a single text string
        text = " ".join(qa_pairs)
        results.append({'user_id': user_id, 'text': text})
    return results

# Collect Q&A per user using the defined function
qa_json_list = collect_qa_per_user(merged_dataset)

# Save to a JSONL file (JSON Lines format)
# Each line contains a JSON object representing one user's complete conversation
with open('user_qa.jsonl', 'w', encoding='utf-8') as f:
    for item in qa_json_list:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')


