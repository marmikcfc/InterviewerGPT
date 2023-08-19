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

app = FastAPI()
templates = Jinja2Templates(directory="templates")
#os.environ["OPENAI_API_KEY"] = ""

interview_dict = {}
chat_history = []
interview_agent = InterviewAgent()
interview_started = False

def get_questions ():
    num = random.random()%2
    if num == 0:
        return """ Given a string, find the length of the longest substring without repeating characters. 
                Input: "abcabcbb"
                Output: 3
                Explanation: The answer is "abc", with the length of 3.
               """
    else:
        return "two sum"


# Need to handle a case where we need to abruptly stop the interview
def get_current_interview_section(start_time):
    current_agent = InterviewSections.CODING_INTERVIEW_INTRO
    current_time = datetime.now()
    diff = (current_time - start_time).total_seconds() / 60

    # Prompt for intro 
    if diff < 5 :
        interview_agent.set_current_chain(InterviewSections.CODING_INTERVIEW_INTRO)
        return InterviewSections.CODING_INTERVIEW_INTRO
    elif diff > 5 and diff < 10:
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


def setup_interview_agent(stream_handler):
    logging.info("Setting up different chains for different interview sections")
    for interview_section in InterviewSections:
        prompt_template = get_prompts(interview_section)
        current_chain = get_chain(interview_section, stream_handler, prompt_template, False)
        interview_agent.add_chain(interview_section, current_chain)

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
    setup_interview_agent(stream_handler)

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

            prompt_template = get_prompts(current_agent)

            # Construct a response
            start_resp = ChatResponse(sender="interviewer", message="", type="start")
            await websocket.send_json(start_resp.dict())

            # Start the interview
            if request["msg"] == "START_INTERVIEW":
                interview_chain = interview_agent.get_current_chain()
                print("starting interview")
                result = await interview_chain.acall({"input": "Hi there!"})
                print(f"answer {result}")
                chat_history.append((request["msg"], result["response"]))
            else:
                result = await interview_chain.acall({"input": request["msg"]})
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