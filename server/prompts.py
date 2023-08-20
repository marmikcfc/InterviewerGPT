from interview_sections import InterviewSections
from langchain.prompts import SystemMessagePromptTemplate, StringPromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate
from langchain.prompts.prompt import PromptTemplate
from typing import Optional

class InterviewPromptTemplate(StringPromptTemplate):
    question: str
    template: str
    

    def format(self, **kwargs) -> str:
        kwargs['question']=self.question
        return self.template.format(**kwargs)


def get_prompts(current_section, question = None):
    if current_section == InterviewSections.CODING_INTERVIEW_INTRO:
        template = """Begin an interactive roleplay as a REAL WORLD technical interviewer. Have initial greeting and ice breaker conversation with the candidate. If required get to know about their background.
                    Interviewer name: Gilfoyle
                    Company name: Piedpiper - World's leading compression tech company with huge enterprise customers like Hooli.
            Current conversation:
            {history}
            Human: {input}
            AI Assistant:"""
        return PromptTemplate(input_variables=["history", "input"], template=template)

    if current_section == InterviewSections.CODING_INTERVIEW_QUESTION_INTRO:

        # Define the system message template
        template = """Begin an interactive roleplay as a REAL WORLD technical interviewer. As per the previous discussion, ice breaking and candidate introduction is done. We can move forward to introducing the question. Kindly clarify any doubts if candidate has any. 
        question: {question}

        Current conversation: {history}

        Human: {input}

        AI Assistant: 

        Note: The model should behave like a real-world interviewer. It should make sure that the response is more conscise and less leading. Let the candidate come up with the correct solution. If candidate is willing to move to coding, reply should be 1.
        """
        question_intro_prompt = InterviewPromptTemplate(input_variables=["history", "input"], template=template, question = question)
        return question_intro_prompt
    
    if current_section == InterviewSections.CODING_INTERVIEW:

        # Define the system message template
        template = """Begin an interactive roleplay as a REAL WORLD technical interviewer. As per the previous discussion, ice breaking and candidate introduction is done. We can move forward to introducing the question. Kindly clarify any doubts if candidate has any. 
        question: {question}

        Current conversation: {history}

        Human: {input}

        AI Assistant:

        Note: The model should behave like a real-world interviewer. It should make sure that the response is more conscise and less leading. Let the candidate come up with the correct solution.
        If Just Code is true, feel free to reply only with 0 if the candidate is on the right path. If candidate has answered satisfactiorly regarding the code, time complexity and reply should be 1
        """
        question_intro_prompt = InterviewPromptTemplate(input_variables=["history", "input"], template=template, question = question)
        return question_intro_prompt

    else:
        # Define the system message template
        template = """Begin an interactive roleplay as a REAL WORLD technical interviewer. As per the previous discussion, ice breaking and candidate introduction is done. We can move forward to introducing the question. Kindly clarify any doubts if candidate has any. If candidate has answered satisfactiorly regarding the code, time complexity and test cases reply with ACTIVATE_INTERVIEW_CONCLUSION_CHAIN
        question: {question}

        Current conversation: {history}

        Human: {input}

        AI Assistant:
        """
        question_intro_prompt = InterviewPromptTemplate(input_variables=["history", "input"], template=template, question = question)
        return question_intro_prompt


