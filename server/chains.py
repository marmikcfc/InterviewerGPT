"""Create a conversation chain for interview."""
from langchain.callbacks.manager import AsyncCallbackManager
from langchain.callbacks.tracers import LangChainTracer
from langchain.chains import ConversationChain
from langchain.chains.llm import LLMChain
from langchain.chains.question_answering import load_qa_chain
from langchain.llms import OpenAI
from langchain.memory import ConversationBufferMemory, ConversationSummaryBufferMemory
from interview_sections import InterviewSections 
import logging
from typing import Any, Dict, List

from langchain.chains.constitutional_ai.models import ConstitutionalPrinciple

ethical_principle = ConstitutionalPrinciple(
    name="Ethical Interviewer Principle",
    critique_request="The model should behave like a real-world interviewer. It should make sure that the response is more conscise and less leading.",
    revision_request="Rewrite the model's output to be like a real-world interviewer without giving lot of the answer away.",
)



class ExtendedConversationBufferMemory(ConversationBufferMemory):
    extra_variables:List[str] = []

    @property
    def memory_variables(self) -> List[str]:
        """Will always return list of memory variables."""
        logging.info(f"#### #### #### ####{self.memory_key}")
        return [self.memory_key] + self.extra_variables

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Return buffer with history and extra variables"""
        d = super().load_memory_variables(inputs)
        d.update({k:inputs.get(k) for k in self.extra_variables})        
        return d



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

    streaming_llm_for_intro = OpenAI(
        streaming=True,
        callback_manager=stream_manager,
        verbose=True,
        temperature=0.7,
    )

    streaming_llm_for_interview= OpenAI(
        streaming=True,
        callback_manager=stream_manager,
        verbose=True,
        temperature=0,
    )
    memory = ConversationSummaryBufferMemory(llm=streaming_llm_for_interview, max_token_limit=10)

    print("creating chain")

    if interview_section == InterviewSections.CODING_INTERVIEW_INTRO:
        conversation_chain = ConversationChain(
            prompt = prompt,
            llm=streaming_llm_for_intro, 
            verbose=True, 
            memory=ConversationBufferMemory()
        )
    
    elif interview_section == InterviewSections.CODING_INTERVIEW_QUESTION_INTRO:
        conversation_chain = ConversationChain(
            prompt = prompt,
            llm=streaming_llm_for_intro, 
            verbose=True, 
            memory=ConversationBufferMemory()
        )
    elif interview_section == InterviewSections.CODING_INTERVIEW:
        constitutional_chain = ConstitutionalChain.from_llm(
            chain=evil_qa_chain,
            constitutional_principles=[ethical_principle],
            llm=streaming_llm_for_interview,
            verbose=True,
            memory=memory)
    
    elif interview_section == InterviewSections.CODING_INTERVIEW_CONCLUSION:
        constitutional_chain = ConstitutionalChain.from_llm(
            chain=evil_qa_chain,
            constitutional_principles=[ethical_principle],
            llm=streaming_llm_for_interview,
            verbose=True,
            memory=memory)

    elif interview_section == InterviewSections.CODING_INTERVIEW_OUTRO:
        constitutional_chain = ConstitutionalChain.from_llm(
            chain=evil_qa_chain,
            constitutional_principles=[ethical_principle],
            llm=streaming_llm_for_interview,
            verbose=True,
            memory=memory)

    return conversation_chain