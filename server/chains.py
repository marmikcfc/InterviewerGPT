"""Create a conversation chain for interview."""
from langchain.callbacks.manager import AsyncCallbackManager
from langchain.callbacks.tracers import LangChainTracer
from langchain.chains import ConversationChain
from langchain.chains.constitutional_ai.base import ConstitutionalChain
from langchain.chains.llm import LLMChain
from langchain.chains.question_answering import load_qa_chain
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory, ConversationSummaryBufferMemory, ConversationSummaryMemory
from interview_sections import InterviewSections 
import logging
from typing import Any, Dict, List
from langchain.chains import SimpleSequentialChain


from langchain.chains.constitutional_ai.models import ConstitutionalPrinciple

def get_chain(interview_section, stream_handler, prompt, tracing: bool = False) -> ConversationChain:
    """Create a converstion introduction chain for question/answering."""
    manager = AsyncCallbackManager([])
    #question_manager = AsyncCallbackManager([question_handler])
    stream_manager = AsyncCallbackManager([stream_handler])
    if tracing:
        tracer = LangChainTracer()
        tracer.load_default_session()
        manager.add_handler(tracer)
        question_manager.add_handler(tracer)
        stream_manager.add_handler(tracer)

    streaming_llm_for_intro = ChatOpenAI(
        streaming=True,
        callback_manager=stream_manager,
        verbose=True,
        temperature=1,
        model = "gpt-3.5-turbo"
    )

    streaming_llm_for_interview= ChatOpenAI(
        streaming=True,
        callback_manager=stream_manager,
        verbose=True,
        temperature=0.3,
        model = "gpt-3.5-turbo-16k"
    )
    memory = ConversationSummaryBufferMemory(llm=streaming_llm_for_interview, max_token_limit=10)

    print("creating chain")

    if interview_section == InterviewSections.CODING_INTERVIEW_INTRO:
        conversation_chain = ConversationChain(
            prompt = prompt,
            llm=streaming_llm_for_intro, 
            verbose=True, 
            memory=ConversationSummaryMemory(llm=OpenAI(temperature=0))
        )
    
    elif interview_section == InterviewSections.CODING_INTERVIEW_QUESTION_INTRO:
        conversation_chain = ConversationChain(
            prompt = prompt,
            llm=streaming_llm_for_interview, 
            verbose=True, 
            memory=ConversationSummaryMemory(llm=OpenAI(temperature=0))

        )
        #conversation_chain = SimpleSequentialChain(chains=[constitutional_chain], verbose=True)
            
    elif interview_section == InterviewSections.CODING_INTERVIEW:
        conversation_chain = ConversationChain(
            prompt = prompt,
            llm=streaming_llm_for_interview, 
            verbose=True, 
            memory=ConversationSummaryMemory(llm=OpenAI(temperature=0))

        )
    
    else:
        return None

    return conversation_chain

    #     elif interview_section == InterviewSections.CODING_INTERVIEW:
    #     constitutional_chain = ConstitutionalChain.from_llm(
    #         chain=streaming_llm_for_interview,
    #         constitutional_principles=[interview_ethics_principle],
    #         llm=streaming_llm_for_interview,
    #         verbose=True,
    #         memory=memory)
    
    # elif interview_section == InterviewSections.CODING_INTERVIEW_CONCLUSION:
    #     constitutional_chain = ConstitutionalChain.from_llm(
    #         chain=streaming_llm_for_interview,
    #         constitutional_principles=[interview_ethics_principle],
    #         llm=streaming_llm_for_interview,
    #         verbose=True,
    #         memory=memory)

    # elif interview_section == InterviewSections.CODING_INTERVIEW_OUTRO:
    #     constitutional_chain = ConstitutionalChain.from_llm(
    #         chain=streaming_llm_for_interview,
    #         constitutional_principles=[interview_ethics_principle],
    #         llm=streaming_llm_for_interview,
    #         verbose=True,
    #         memory=memory)
