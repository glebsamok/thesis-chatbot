"""
Model Validation Script

This script evaluates the performance of the fine-tuned model by comparing
predictions against true labels. It provides comprehensive metrics including
accuracy, classification reports, and confusion matrices for each trait.

The script processes validation data, makes predictions using the fine-tuned
model, and calculates various performance metrics to assess model quality.

Key Features:
- Model prediction on validation data
- Performance metrics calculation
- Few-shot learning examples
- Comprehensive evaluation reports

Author: Thesis Research Project
Date: 2024
"""

import json
from openai import OpenAI
import os
from dotenv import load_dotenv
import re
from collections import Counter
from sklearn.metrics import classification_report, confusion_matrix

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Define the trait labels that the model predicts
LABELS = ["emotional_intelligence", "perspective_taking", "learning_orientation", "social_curiosity"]

# System message for the model that defines the task and output format
SYSTEM_MSG = '''You are an experienced organizational psychologist.

You will receive questions which were asked to the users and their answers.

TASK  
1. Read the respondent's answers.
2. Think **step-by-step** about the evidence for each trait and write the thinking process which highlights the evidence and shows the thinking process of proving this label:  
   • Emotional Intelligence (EI) — recognising and appropriately expressing one's own and others' emotions.  
   • Perspective Taking (PT) — understanding the other person's viewpoint and reasons for their behaviour.  
   • Learning Orientation (LO) — actively seeking to learn, request feedback, and draw lessons.  
   • Social Curiosity (SC) — interest in new people, asking questions, expanding one's network.    

3. Output in **exactly** the JSON format below:  

{"rationale":"<2–3-sentence thought chain process summary>", "emotional_intelligence": "...", "perspective_taking": "...", "learning_orientation": "...", "social_curiosity": "..."}
'''

def extract_true_labels(assistant_content):
    """
    Extract true labels from the assistant's response in the training data.
    
    This function parses the JSON block from the assistant's message
    in the training data to extract the true trait labels for comparison.
    
    Args:
        assistant_content (str): The assistant's response from training data
        
    Returns:
        dict: Extracted labels or empty dict if parsing fails
    """
    # Extract the JSON block from the assistant's message
    match = re.search(r'```json\\n(\\{.*?\\})\\n```', assistant_content, re.DOTALL)
    if not match:
        match = re.search(r'```json\\n(\\{.*)', assistant_content, re.DOTALL)
    if not match:
        match = re.search(r'({.*})', assistant_content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    return {}

def get_few_shot_examples(n=4):
    """
    Get few-shot examples from the training data.
    
    This function loads examples from the training data to provide
    context for the model during prediction. Few-shot learning can
    improve model performance by providing relevant examples.
    
    Args:
        n (int): Number of examples to load (default: 4)
        
    Returns:
        list: List of tuples containing (user_content, assistant_content)
    """
    examples = []
    with open("train.jsonl", "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= n:
                break
            obj = json.loads(line)
            messages = obj["messages"]
            user_content = next(m["content"] for m in messages if m["role"] == "user")
            assistant_content = next(m["content"] for m in messages if m["role"] == "assistant")
            examples.append((user_content, assistant_content))
    return examples

# Load few-shot examples for improved prediction performance
FEW_SHOT_EXAMPLES = get_few_shot_examples(4)

def predict_traits(user_content):
    """
    Make trait predictions using the fine-tuned model with few-shot examples.
    
    This function uses the fine-tuned model to predict trait labels for
    given user content. It includes few-shot examples to improve prediction
    quality and uses structured JSON output format.
    
    Args:
        user_content (str): The user's answers to analyze
        
    Returns:
        dict: Predicted trait labels and rationale
    """
    # Build the few-shot prompt
    few_shot_prompt = ""
    for ex_user, ex_assistant in FEW_SHOT_EXAMPLES:
        few_shot_prompt += f"User's answers:\n{ex_user}\n\nRationale and correct labels:\n{ex_assistant}\n\n"
    user_prompt = f"Current user's answers:\n{user_content}\n\nRationale and correct labels:\n"
    resp = client.chat.completions.create(
        model="ft:gpt-4.1-2025-04-14:personal:thesis-classification:BhkqVEdL",
        messages=[
            {"role": "system", "content": SYSTEM_MSG + few_shot_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
        response_format={"type": "json_object"}
    )
    print(messages)
    return json.loads(resp.choices[0].message.content)

# Process validation data and collect results
results = []
with open("valid.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        obj = json.loads(line)
        messages = obj["messages"]
        user_content = next(m["content"] for m in messages if m["role"] == "user")
        assistant_content = next(m["content"] for m in messages if m["role"] == "assistant")
        true_labels = extract_true_labels(assistant_content)
        pred_labels = predict_traits(user_content)
        results.append({"pred": pred_labels, "true": true_labels})

# Calculate accuracy for each trait
# This provides overall accuracy metrics for each individual trait
trait_acc = Counter()
trait_total = Counter()
for r in results:
    for trait in LABELS:
        if trait in r["pred"] and trait in r["true"]:
            trait_total[trait] += 1
            if r["pred"][trait].strip().lower() == r["true"][trait].strip().lower():
                trait_acc[trait] += 1

# Print accuracy for each trait
for trait in LABELS:
    print(f"{trait} accuracy: {trait_acc[trait] / trait_total[trait]:.2%}")

# Calculate overall exact match accuracy
# This measures how often the model gets ALL traits correct for a single prediction
all_correct = sum(
    all(r["pred"].get(trait, "").strip().lower() == r["true"].get(trait, "").strip().lower() for trait in LABELS)
    for r in results
)
print(f"Overall exact match accuracy: {all_correct / len(results):.2%}")

# Collect predictions and true labels for each trait
# This prepares data for detailed classification reports
trait_preds = {trait: [] for trait in LABELS}
trait_trues = {trait: [] for trait in LABELS}

for r in results:
    for trait in LABELS:
        if trait in r["pred"] and trait in r["true"]:
            trait_preds[trait].append(r["pred"][trait].strip().lower())
            trait_trues[trait].append(r["true"][trait].strip().lower())

# Generate detailed classification reports and confusion matrices
# This provides comprehensive evaluation metrics for each trait
for trait in LABELS:
    print(f"\n=== {trait.upper()} ===")
    print("Classification Report:")
    print(classification_report(trait_trues[trait], trait_preds[trait], digits=3))
    print("Confusion Matrix:")
    print(confusion_matrix(trait_trues[trait], trait_preds[trait]))
