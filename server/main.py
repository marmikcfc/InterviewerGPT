"""Main entrypoint for the app."""
import logging
import pickle
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from langchain.vectorstores import VectorStore
from callback import StreamingLLMCallbackHandler
from datetime import datetime
import random
import os
from schema import ChatResponse
from chains import get_chain
from langchain.prompts.prompt import PromptTemplate
from interview_sections import InterviewSections 
from agents import InterviewAgent
from prompts import get_prompts
from questions import get_question
from interview_types import InterviewTypes
import json

app = FastAPI()
#os.environ["OPENAI_API_KEY"] = ""
logging.basicConfig(level = logging.DEBUG)


chat_history = []
interview_agent = InterviewAgent()
interview_started = False
current_section = InterviewSections.CODING_INTERVIEW_INTRO

# Need to handle a case where we need to abruptly stop the interview
def get_current_interview_section(start_time):
    current_agent = InterviewSections.CODING_INTERVIEW_INTRO
    current_time = datetime.now()
    diff = (current_time - start_time).total_seconds() / 60

    # Prompt for intro 
    if diff < 1:
        interview_agent.set_current_chain(InterviewSections.CODING_INTERVIEW_INTRO)
        return InterviewSections.CODING_INTERVIEW_INTRO
    elif diff > 1 and diff < 2:
        interview_agent.set_current_chain(InterviewSections.CODING_INTERVIEW_QUESTION_INTRO)
        return InterviewSections.CODING_INTERVIEW_QUESTION_INTRO
    elif diff > 2 and diff < 4:
        interview_agent.set_current_chain(InterviewSections.CODING_INTERVIEW)
        return InterviewSections.CODING_INTERVIEW
    elif diff >  4 and diff < 5:
        interview_agent.set_current_chain(InterviewSections.CODING_INTERVIEW_CONCLUSION)
        return InterviewSections.CODING_INTERVIEW_CONCLUSION
    elif diff > 5 and diff < 6:
        interview_agent.set_current_chain(InterviewSections.CODING_INTERVIEW_OUTRO)
        return InterviewSections.CODING_INTERVIEW_OUTRO
    else:
        interview_agent.set_current_chain(InterviewSections.CODING_INTERVIEW_FEEDBACK)
        return InterviewSections.CODING_INTERVIEW_FEEDBACK


def setup_interview_agent(stream_handler, question):
    logging.info("Setting up different chains for different interview sections")
    for interview_section in InterviewSections:
        prompt_template = get_prompts(interview_section, question)
        current_chain = get_chain(interview_section, stream_handler, prompt_template, False)
        interview_agent.add_chain(interview_section, current_chain)
    logging.info("Setup agent")

# TODO Make this into a class so that there's cleaner interface to update prompts
def update_chains(interview_section, stream_handler, question, code):
    interivew_conclusion_prompt_template = get_prompts(interview_section, question, code)
    interview_section_chain = get_chain(interview_section, stream_handler, interivew_conclusion_prompt_template, False)
    interview_agent.update_chains(interview_section, interview_section_chain)
    logging.info("Updated agent")

@app.on_event("startup")
async def startup_event():
    logging.info("startup")

@app.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    stream_handler = StreamingLLMCallbackHandler(websocket)
    chat_history = []
    #TODO: Tracing true isn't working, resolve that
    current_interview_chain = None
    question = get_question(InterviewTypes.CODING_INTERVIEW)
    setup_interview_agent(stream_handler, question)
    current_section = InterviewSections.CODING_INTERVIEW_INTRO
    sent_question_to_the_frontend = False
    interview_dict = {}
    
    logging.info("##### ##### ##### ###### ###### ###### ####### ####### ######## ######## ")
    most_recent_code = None
    while True:
        try:
            # Receive and send back the client message
            message = await websocket.receive_text()
            request = json.loads(message)

            print(request)
            interview_id = request["interview_id"]
            if interview_id not in interview_dict:
                interview_dict[interview_id] = {"start_time": datetime.now(), "current_agent": 0}
            
            print(f"interview dict {interview_dict}")
            current_agent =  get_current_interview_section(interview_dict[interview_id]["start_time"])
            print(f"current agent {current_agent}")

            # Construct a response
            start_resp = ChatResponse(sender="interviewer", message="", type="start")
            await websocket.send_json(start_resp.dict())

            # Start the interview
            interview_chain = interview_agent.get_current_chain()

            if request["msg"] == "START_INTERVIEW":
                print("starting interview")
                current_input = "Hello! [Begin Interview]"
            else:
                current_input = request["msg"]
            
            if interview_agent.get_current_interview_section() != current_section:
                logging.info(f"Changing current section to {interview_agent.get_current_interview_section} as it has changed")
                current_section = interview_agent.get_current_interview_section
    

            if request["justCode"] == True:
                logging.info("Just code is true and hence updating chains")
                current_input += "\n Just Code: True"
                most_recent_code = current_input
                # make sure most_recent_code is set in the prompt 
                update_chains(InterviewSections.CODING_INTERVIEW_CONCLUSION, stream_handler, question, most_recent_code)
                update_chains(InterviewSections.CODING_INTERVIEW_OUTRO, stream_handler, question, most_recent_code)
                update_chains(InterviewSections.CODING_INTERVIEW_FEEDBACK, stream_handler, question, most_recent_code)
                logging.info("Chains updated")

            if interview_agent.get_current_interview_section() == InterviewSections.CODING_INTERVIEW_FEEDBACK:
                current_input = chat_history
            
            logging.info("Sending a call to LLM")
            result = await interview_chain.acall({"input": current_input})

            if request["justCode"] == False:
                chat_history.append((current_input, result["response"]))
            
            print(f"answer {result}")
            logging.info(f"{sent_question_to_the_frontend} current_section {current_section} question {question}")
            # A hack to display question on the code editor as well as display it 
            if sent_question_to_the_frontend == False and interview_agent.get_current_interview_section() == InterviewSections.CODING_INTERVIEW_QUESTION_INTRO:
                logging.info("sending the question as a info message to the frontend")
                await stream_handler.send_specific_information(question) 
                sent_question_to_the_frontend = True

            logging.info("Sent it to the frontend")
            # Flush out remaining tokens in the buffer
            await stream_handler.flush_buffer() 
            end_resp = ChatResponse(sender="interviewer", message="", type="end")
            await websocket.send_json(end_resp.dict())

        except WebSocketDisconnect:
            logging.info("websocket disconnect")
            # Hack for testing remove soon
            interview_dict = {}
            break
        except Exception as e:
            logging.error(e)
            resp = ChatResponse(
                sender="interviewer",
                message="Sorry, something went wrong. Try again.",
                type="error",
            )
            await websocket.send_json(resp.dict())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)