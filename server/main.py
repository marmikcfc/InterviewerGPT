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

app = FastAPI()
templates = Jinja2Templates(directory="templates")
#os.environ["OPENAI_API_KEY"] = ""

interview_dict = {}
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
    elif diff > 1 and diff < 10:
        interview_agent.set_current_chain(InterviewSections.CODING_INTERVIEW_QUESTION_INTRO)
        return InterviewSections.CODING_INTERVIEW_QUESTION_INTRO
    elif diff > 10 and diff < 35:
        interview_agent.set_current_chain(InterviewSections.CODING_INTERVIEW)
        return InterviewSections.CODING_INTERVIEW
    elif diff >  35 and diff < 40:
        interview_agent.set_current_chain(InterviewSections.CODING_INTERVIEW_CONCLUSION)
        return InterviewSections.CODING_INTERVIEW_CONCLUSION
    elif diff > 40 and diff < 45:
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

@app.on_event("startup")
async def startup_event():
    logging.info("startup")

@app.get("/")
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


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

    while True:
        try:
            # Receive and send back the client message
            request = await websocket.receive_json()
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
                current_input = "Hi there!"
            else:
                current_input = request["msg"]
            
            if interview_agent.get_current_interview_section() != current_section:
                logging.info(f"Changing current section to {interview_agent.get_current_interview_section} as it has changed")
                current_section = interview_agent.get_current_interview_section

            if interview_agent.get_current_interview_section() != InterviewSections.CODING_INTERVIEW_INTRO:
                result = await interview_chain.acall({"input": request["msg"]})
            else:
                result = await interview_chain.acall({"input": request["msg"]})
            chat_history.append((request["msg"], result["response"]))
            print(f"answer {result}")
            chat_history.append((request["msg"], result["response"]))

            # Flush out remaining tokens in the buffer
            await stream_handler.flush_buffer() 
            end_resp = ChatResponse(sender="interviewer", message="", type="end")
            await websocket.send_json(end_resp.dict())

        except WebSocketDisconnect:
            logging.info("websocket disconnect")
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