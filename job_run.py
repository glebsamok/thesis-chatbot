"""
Job Run Script for Model Training and Prediction

This script handles the training data preparation and prediction tasks
for the fine-tuned model. It processes datasets, creates training/validation
splits, and provides functionality for making predictions using the
fine-tuned model.

The script includes functions for:
- Data preprocessing and formatting
- Training/validation split creation
- Model prediction using fine-tuned models
- Structured output generation

Key Features:
- Configurable system prompts and question columns
- Stratified train/validation splits
- JSONL file generation for training
- Prediction functionality with fine-tuned models

Author: Thesis Research Project
Date: 2024
"""

import json, pathlib, random
from sklearn.model_selection import train_test_split
import pandas as pd
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

# Load the dataset with reasoning explanations
df = pd.read_csv('dataset2_reduced_with_reasoning_full.csv')

# ------------ config ------------
# System message for the model that defines the task and output format
SYSTEM_MSG = '''You are an experienced organizational psychologist.

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

# Define the question columns that contain the actual interview questions
# These columns will be used to create the training data
QUESTION_COLS = [            # rename to your real column names
    "Briefly describe what happened (1-2 sentences).", "How did this situation make you feel? How did you express your feelings? Did you avoid them, expressed them, or kept them to yourself?", "What emotions do you think the other person was feeling? What cues gave you this impression? Why those behaviours indicated the following emotions?", "Did you understand where they were coming from? What do you think was driving their behavior?",
    "Looking, deeper, what underlying needs or concerns might have influenced how they acted?", "Briefly describe your goal and what you've been doing to achieve it (1-2 sentences).", "When looking at all the information you gathered while working on this goal, was there a time when things felt particularly confusing or complicated? How did you sort through that confusion to better understand what you needed to do?",
    "What unexpected challenges or surprises have you faced while working toward this goal? What steps did you take to overcome them?", "Did you try any new approaches or methods while working on this goal? Where did you learn about this new approach and how did you put it into practice?"     # …add as many as you kept
]

# Mapping between dataframe column names and JSON output keys
# This defines how the trait labels are mapped in the output
LABEL_MAP = {                # dataframe col → JSON key
    "emotional_intelligence_label": "emotional_intelligence",
    "perspective_taking_label":     "perspective_taking",
    "learning_orientation_label":   "learning_orientation",
    "social_curiosity_label":       "social_curiosity"
}

# ------------ helpers -----------
def concat_answers(row) -> str:
    """
    Concatenate all answers for a given row into a single string.
    
    This function combines all the question-answer pairs for a single
    respondent into a formatted string that can be used as input
    for the model.
    
    Args:
        row (pd.Series): A single row of the dataframe
        
    Returns:
        str: Formatted string containing all questions and answers
    """
    parts = []
    for col in QUESTION_COLS:
        full_q = df.columns[df.columns.get_loc(col)]   # keeps complete wording
        parts.append(f"{full_q}\n{row[col]}")
    return "\n\n".join(parts)

def build_record(row) -> dict:
    """
    Build a training record for the fine-tuned model.
    
    This function creates a structured record that includes the system
    message, user input (questions and answers), and assistant output
    (reasoning and labels) in the format required for fine-tuning.
    
    Args:
        row (pd.Series): A single row of the dataframe
        
    Returns:
        dict: Training record with messages and expected output
    """
    labels_json = {
        "rationale": row["reasoning"][:350]            # full or trimmed CoT
    }
    for col, key in LABEL_MAP.items():
        labels_json[key] = str(row[col]).title()       # Low/Medium/High
    assistant_content = f"{row['reasoning']}\n\n```json\n{json.dumps(labels_json, ensure_ascii=False)}\n```"
    return {
        "messages": [
            {"role": "system",    "content": SYSTEM_MSG},
            {"role": "user",      "content": concat_answers(row)},
            {"role": "assistant", "content": assistant_content}
        ]
    }

# Create a combined label column for stratification
# This ensures that the train/validation split maintains the distribution
# of all trait combinations
df['combined_label'] = df[list(LABEL_MAP)].apply(lambda x: '_'.join(x.astype(str)), axis=1)

# Remove rows where the combined label appears only once
# This prevents issues with stratification when some combinations are rare
label_counts = df['combined_label'].value_counts()
valid_labels = label_counts[label_counts >= 2].index
df_filtered = df[df['combined_label'].isin(valid_labels)]

# Create stratified train/validation split
# This ensures that both sets have similar distributions of trait combinations
train_df, val_df = train_test_split(df_filtered, test_size=0.2, random_state=42, stratify=df_filtered['combined_label'])

# Commented out code for generating JSONL files
# # Drop the temporary combined_label column
# train_df = train_df.drop('combined_label', axis=1)
# val_df = val_df.drop('combined_label', axis=1)

# # pathlib.Path("train.jsonl").write_text(
# #     "\n".join(json.dumps(build_record(r), ensure_ascii=False) for _, r in train_df.iterrows()),
# #     encoding="utf-8"
# # )
# # pathlib.Path("valid.jsonl").write_text(
# #     "\n".join(json.dumps(build_record(r), ensure_ascii=False) for _, r in val_df.iterrows()),
# #     encoding="utf-8"
# # )
# print("✅  Files ready: train.jsonl & valid.jsonl")

# Initialize OpenAI client for predictions
client = OpenAI()

def predict_traits(row):
    """
    Make trait predictions using the fine-tuned model.
    
    This function uses the fine-tuned model to predict trait labels
    for a given set of answers. It formats the input and calls
    the model to get predictions.
    
    Args:
        row (pd.Series): A single row of the dataframe
        
    Returns:
        str: Model response containing trait predictions
    """
    prompt_block = concat_answers(row)     # same helper as above
    resp = client.chat.completions.create(
        model="ft:gpt-4.1-2025-04-14:personal:thesis-classification:BhkqVEdL",
        messages=[
            {"role":"system", "content": SYSTEM_MSG},
            {"role":"user",   "content": prompt_block}
        ],
        temperature=0.2
    )
    return resp.choices[0].message.content   # → JSON block inside ```json

# Example prediction on validation data
print(predict_traits(val_df.iloc))
