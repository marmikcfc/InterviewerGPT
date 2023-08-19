from interview_sections import InterviewSections
from langchain.prompts.prompt import PromptTemplate

def get_prompts(current_section):
    if current_section == InterviewSections.CODING_INTERVIEW_INTRO:
        template = """Begin an interactive roleplay as a REAL WORLD technical interviewer. Have initial greeting and ice breaker conversation with the candidate. If required get to know about their background.
                    Interviewer name: Gilfoyle
                    Company name: Piedpier - World's leading compression tech company with huge enterprise customers like Hooli.

            Current conversation:
            {history}
            Human: {input}
            AI Assistant:"""
        return PromptTemplate(input_variables=["history", "input"], template=template)
    # if current_agent == 1:
    #     template = """
    #         Begin an interactive roleplay as a REAL WORLD technical interviewer.
    #         Introduction summary: {summary}
            
    #     """

    else:
        return "no prompt"

