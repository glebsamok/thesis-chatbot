"""
Chatbot Validation Script for Real User Data

This script validates the fine-tuned model on real chatbot conversation data.
It processes user conversations from the chatbot interface and compares
model predictions against true labels (if available) to assess performance
on actual user interactions.

The script includes:
- Processing of real chatbot conversation data
- Trait prediction using the fine-tuned model
- Comparison with true labels from external datasets
- Comprehensive results analysis and storage

Key Features:
- Real-world chatbot data validation
- Structured prediction with Pydantic models
- True label comparison and analysis
- Results export for further analysis

Author: Thesis Research Project
Date: 2024
"""

import json
import pandas as pd
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv
import os
from typing import Literal

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Pydantic model for trait labels with strict validation
class TraitLabels(BaseModel):
    """
    Pydantic model for trait classification labels.
    
    This model enforces that trait labels must be one of the three
    specified levels: low, medium, or high. It provides type safety
    and validation for model outputs.
    """
    emotional_intelligence: Literal["low", "medium", "high"]
    perspective_taking:   Literal["low", "medium", "high"]
    learning_orientation: Literal["low", "medium", "high"]
    social_curiosity:     Literal["low", "medium", "high"]

    model_config = {"extra": "forbid"}        # -> additionalProperties: false

# Pydantic model for the complete decision output
class DecisionMaker(BaseModel):
    """
    Pydantic model for complete trait assessment output.
    
    This model includes both explanatory rationales for each trait
    and the final discrete labels. It provides a comprehensive
    structure for model outputs with reasoning.
    """
    # explanatory rationales
    emotional_intelligence: str = Field(..., description="Why EI is rated so")
    perspective_taking:    str = Field(..., description="Why PT is rated so")
    learning_orientation:  str = Field(..., description="Why LO is rated so")
    social_curiosity:      str = Field(..., description="Why SC is rated so")

    # final discrete labels
    result: TraitLabels

    model_config = {"extra": "forbid"}

# Load user_qa.jsonl - contains real chatbot conversations
user_qa = []
with open('user_qa.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        user_qa.append(json.loads(line))

# Load merged_dataset.csv for true labels
# This contains external data with true trait labels for comparison
merged = pd.read_csv('merged_dataset.csv')

# For each user, get the most common label for each trait (in case of multiple rows per user)
# This handles cases where users might have multiple entries in the external dataset
label_cols = [
    'emotional_intelligence_label',
    'perspective_taking_label',
    'learning_orientation_label',
    'social_curiosity_label'
]
true_labels = (
    merged.groupby('user_id')[label_cols]
    .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else None)
    .reset_index()
    .set_index('user_id')
    .to_dict(orient='index')
)

# Load the dataset with reasoning explanations for few-shot examples
dataset_w_reasoning = pd.read_csv('dataset2_reduced_with_reasoning_full.csv')

def concat_answers(row):
    """
    Concatenate all answers for a given row into a formatted string.
    
    This function combines all question-answer pairs for a single
    respondent, excluding label columns and reasoning columns.
    
    Args:
        row (pd.Series): A single row of the dataframe
        
    Returns:
        str: Formatted string containing all questions and answers
    """
    return "\n".join([f" Question: {col} \n Answer: {row[col]}" for col in row.index if 'label' not in col and col != 'reasoning' and col != 'big5_label'])

def fetch_true_labels(row):
    """
    Extract true trait labels from a dataframe row.
    
    This function retrieves the actual trait labels from the dataset
    for comparison with model predictions.
    
    Args:
        row (pd.Series): A single row of the dataframe
        
    Returns:
        dict: Dictionary containing true trait labels
    """
    return {col: row[col] for col in row.index if 'label' in col and col != 'big5_label' and col != 'reasoning'}

def fetch_rationale(row):
    """
    Extract the reasoning explanation from a dataframe row.
    
    Args:
        row (pd.Series): A single row of the dataframe
        
    Returns:
        str: The reasoning explanation for the trait classifications
    """
    return row['reasoning']

def get_few_shot_examples():
    """
    Get balanced few-shot examples from the dataset.
    
    This function selects examples to ensure representation of all
    trait-level combinations. It first selects examples for each
    trait-level combination, then adds random examples to reach
    the desired total number.
    
    Returns:
        list: List of tuples containing (answers, true_labels, rationale)
    """
    examples = []
    trait_levels = ["Low", "Medium", " High"]
    traits = ["emotional_intelligence", "perspective_taking", "learning_orientation", "social_curiosity"]
    used_indices = set()  # Keep track of which rows we've already used
    
    # First get examples for each trait-level combination
    for trait in traits:
        for level in trait_levels:
            # Find rows where this trait has this level
            matching_rows = dataset_w_reasoning[dataset_w_reasoning[f"{trait}_label"] == level]
            # Filter out rows we've already used
            available_rows = matching_rows[~matching_rows.index.isin(used_indices)]
            
            if not available_rows.empty:
                # Take the first available row
                row = available_rows.iloc[0]
                used_indices.add(row.name)  # Mark this row as used
                examples.append((concat_answers(row), fetch_true_labels(row), fetch_rationale(row)))
                print(f"Selected example for {trait} {level} from row {row.name}")
            else:
                print(f"Warning: No unique example found for {trait} {level}")
    
    # Add 8 more random examples from remaining rows
    remaining_rows = dataset_w_reasoning[~dataset_w_reasoning.index.isin(used_indices)]
    if len(remaining_rows) >= 8:
        random_rows = remaining_rows.sample(n=8)
    else:
        random_rows = remaining_rows  # Take all remaining if less than 8
        
    for _, row in random_rows.iterrows():
        examples.append((concat_answers(row), fetch_true_labels(row), fetch_rationale(row)))
        print(f"Added random example from row {row.name}")
    
    print(f"Total examples collected: {len(examples)}")
    return examples

# Load few-shot examples for improved prediction performance
FEW_SHOT_EXAMPLES = get_few_shot_examples()

# Comprehensive system message with detailed trait definitions
SYSTEM_MSG = '''
You are an experienced industrial-organizational psychologist who specialises in competency-based content analysis.

You will receive **(a)** the original question that was asked of a respondent and **(b)** the respondent's verbatim answer(s).

────────────────────────────────────────  TASK  ────────────────────────────────────────
1. **Read** the respondent's answer(s) carefully and holistically.
2. **Think *step-by-step***: gather explicit quotes or paraphrased passages that support (or contradict) each trait below.  
   - List the evidence in the order you notice it (bullet points are fine).  
   - Make sure every piece of evidence is tied to a specific part of the respondent's text ("L3: 'I often ask my peers…' ").  
3. **Conclude** with a one-line verdict for each trait — either **Present**, **Partially present**, or **Not demonstrated** — based solely on the evidence you recorded.

────────────────────────────  TRAIT DEFINITIONS & BEHAVIOURAL CUES  ────────────────────────────
For each trait, use the rubric below.  Treat "evidence" as any phrase, sentence, or pattern in the answer that clearly signals the behaviour.

### 1. Emotional Intelligence (EI)
* **Definition**: Accurately recognising, regulating, and constructively expressing one's own emotions **and** reading or responding to others' emotions.
* **Positive cues**  
  • Names a feeling ("I felt frustrated but …") **and** acts on it constructively.  
  • Describes sensing another person's mood, tone, or non-verbal cue and adapting behaviour.  
  • Uses empathy language ("imagined how they must have felt," "validated her concern").  
* **Red-flags / Low EI**  
  • Dismisses or mocks emotions; focuses only on facts/tasks.  
  • Describes outbursts or emotional hijacking with no reflection or remedy.

### 2. Perspective Taking (PT)
* **Definition**: The cognitive act of stepping into someone else's shoes to see *why* they think or behave a certain way.
* **Positive cues**  
  • Explicitly mentions the other party's constraints, motives, or context ("Given his tight deadline, I understood…").  
  • Adjusts own stance after considering that viewpoint.  
* **Red-flags / Low PT**  
  • Frames conflict purely as "they were wrong."  
  • No attempt to understand opposing needs or context.

### 3. Learning Orientation (LO)
* **Definition**: A stable tendency to seek feedback, reflect, and turn experiences (even failures) into lessons.
* **Positive cues**  
  • Actively requests feedback or mentoring.  
  • Describes experimenting, iterating, reading, taking courses, or setting learning goals.  
  • Converts mistakes into specific take-aways ("Next time I will…").  
* **Red-flags / Low LO**  
  • Blames circumstances rather than extracting lessons.  
  • Avoids feedback or portrays growth as unnecessary.

### 4. Social Curiosity (SC)
* **Definition**: An intrinsic interest in people — asking thoughtful questions, exploring backgrounds, and expanding one's social network.
* **Positive cues**  
  • Approaches new colleagues, attends networking events, or conducts informational interviews.  
  • Asks probing, open-ended questions to understand others' experiences.  
* **Red-flags / Low SC**  
  • Interacts strictly for transactional reasons.  
  • Shows little initiative in meeting or learning about new people.

DO NOT ALWAYS ASSIGN MEDIUM LEVEL, BE BRAVE AND USE YOUR JUDGEMENT. Sometimes it is medium for real, but you should not be afraid to assign low or high.
'''

def predict_traits(text):
    """
    Make trait predictions using the fine-tuned model with structured output.
    
    This function uses the fine-tuned model with Pydantic validation to
    ensure consistent and properly structured outputs. It includes
    comprehensive trait definitions and behavioral cues.
    
    Args:
        text (str): The user's conversation text to analyze
        
    Returns:
        DecisionMaker: Validated prediction with reasoning and labels
    """
    resp = client.beta.chat.completions.parse(
        model="ft:gpt-4.1-2025-04-14:personal:thesis-classification:BhkqVEdL",
        messages=[
            {"role": "system", "content": SYSTEM_MSG},
            {"role": "user", "content": text}
        ],
        temperature=0.2,
        response_format=DecisionMaker
    )
    return resp

# Process each user conversation and generate predictions
results = []
for entry in user_qa:
    user_id = entry['user_id']
    text = entry['text']
    result = predict_traits(text)
    
    parsed = result.choices[0].message.parsed
    row = {
        'user_id': user_id,
        'emotional_intelligence_reasoning': getattr(parsed, 'emotional_intelligence'),
        'perspective_taking_reasoning': getattr(parsed, 'perspective_taking'),
        'learning_orientation_reasoning': getattr(parsed, 'learning_orientation'),
        'social_curiosity_reasoning': getattr(parsed, 'social_curiosity'),
        'emotional_intelligence_predicted': getattr(parsed.result, 'emotional_intelligence'),
        'perspective_taking_predicted': getattr(parsed.result, 'perspective_taking'),
        'learning_orientation_predicted': getattr(parsed.result, 'learning_orientation'),
        'social_curiosity_predicted': getattr(parsed.result, 'social_curiosity'),
    }
    # Add true labels if available for comparison
    if user_id in true_labels:
        for trait in label_cols:
            row[trait + '_true'] = true_labels[user_id][trait]
    else:
        for trait in label_cols:
            row[trait + '_true'] = None
    results.append(row)

# Save results to CSV for further analysis
df_results = pd.DataFrame(results)
df_results.to_csv('chatbot_valid_results.csv', index=False)