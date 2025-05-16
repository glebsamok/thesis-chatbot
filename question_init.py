from utils import get_file_content
from llm_text_generation import generate_text_json, generate_text
import json


class Question:
    def __init__(self, question, acceptance_criteria):
        print(f"Initializing Question with: \nQuestion: {question}\nAcceptance Criteria: {acceptance_criteria}")
        self.question = question
        self.acceptance_criteria = acceptance_criteria

    def acceptance_check(self, answer):
        print(f"Starting acceptance check for answer: {answer}")
        
        print("Loading system prompts...")
        system_prompt_check = get_file_content('prompts/acceptance_general.txt')
        system_prompt_generate = get_file_content('prompts/generate_sub_question.txt')
        
        print("Preparing messages for acceptance check...")
        messages_check = [
            {"role": "system", "content": system_prompt_check},
            {"role": "user", "content": f"Question: {self.question}\nAcceptance Criteria: {self.acceptance_criteria}\nAnswer: {answer}"}
        ]
        
        print("Generating acceptance check response...")
        response = generate_text_json(messages_check)
        
        print("Parsing check result...")
        check_result = json.loads(response)

        if check_result['result'] == 'failed':
            print(f"Answer failed acceptance check. Reason: {check_result['reason']}")
            print("Generating follow-up question...")
            messages_sub_question = [
                {"role": "system", "content": system_prompt_generate},
                {"role": "user", "content": f"Question: {self.question}\nAnswer: {answer}\nReason: {check_result['reason']}"}
            ]
            extra_question = generate_text(messages_sub_question)
            print(f"Generated follow-up question: {extra_question}")
            return False, extra_question
        else:
            print("Answer passed acceptance check")
            return True, None
        
    def generate_answer_reactions(self, answer):
        print(f"Generating reaction for answer: {answer}")
        
        print("Loading reaction prompt...")
        system_prompt_generate = get_file_content('prompts/generate_answer_reactions.txt')
        
        print("Preparing messages for reaction generation...")
        messages_generate = [
            {"role": "system", "content": system_prompt_generate},
            {"role": "user", "content": f"Question: {self.question}\nAnswer: {answer}"}
        ]
        
        print("Generating reaction...")
        response = generate_text(messages_generate)
        print(f"Generated reaction: {response}")
        return response
