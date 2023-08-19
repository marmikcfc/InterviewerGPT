"""Main entrypoint for the app."""
import logging
import pickle
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from langchain.vectorstores import VectorStore
from callback import QuestionGenCallbackHandler, StreamingLLMCallbackHandler
from datetime import datetime
import random
import os
from schema import ChatResponse
from chains import get_chain
from langchain.prompts.prompt import PromptTemplate


'''
Interviewing is painful process and it takes a lot of bandwidth. So ideally, app should
1. have an agent to take interview
2. Upload the transcript in transcripts section
3. Transcript should be summarised and searchable for human recuriter
4. Provide feedback to the user pretty quickly

---
P0 -> Set up websockets over fastapi
P1 -> Set up chains, streaming, intro to interview agent
P2 -> Set up output parser to collect words from a stream of tokens
P3 -> Set up other agents to carry out coding interview 
P4 -> React frontend with editor and react chat window
P5 -> Add openAI Whisper for the Speech to text
P6 -> Add elevenlabs for text to speech and direct audio transfer over websocklets
P7 -> Store transcripts in vector store for semantic search
P8 -> View transcripts on a dashboard
P9 -> System design interview
P10 -> Mermaidjs integration for the system design interview
P11 -> Behavioural interview
'''

app = FastAPI()
templates = Jinja2Templates(directory="templates")
#os.environ["OPENAI_API_KEY"] = ""

interview_dict = {}
chat_history = []


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

def get_prompts(current_agent):
    if current_agent == 0:
        template = """Begin an interactive roleplay as a REAL WORLD technical interviewer. Have initial greeting and ice breaker conversation with the candidate. If required get to know about their background.
                    Interviewer name: Gilfoyle
                    Company name: Piedpier - World's leading compression tech company with huge enterprise customers like Hooli.

            Current conversation:
            {history}
            Human: {input}
            AI Assistant:"""
        return PromptTemplate(input_variables=["history", "input"], template=template)

    else:
        return "no prompt"

def get_agent(start_time):
    current_agent = 0
    current_time = datetime.now()

    diff = (current_time - start_time).total_seconds() / 60

    # Prompt for intro 
    if diff < 5 :
        return 0
    elif diff > 1 and diff < 15:
        return 1
    elif diff > 15 and diff < 40:
        return 2
    elif diff >  40 and diff < 45:
        return 3
    else:
        # In case we need to abruptly stop the interview
        return 4

@app.on_event("startup")
async def startup_event():
    logging.info("loading vectorstore")


@app.get("/")
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})




@app.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    question_handler = QuestionGenCallbackHandler(websocket)
    stream_handler = StreamingLLMCallbackHandler(websocket)
    chat_history = []
    #TODO: Tracing true isn't working, resolve that
    interview_chain = None

    while True:
        try:
            # Receive and send back the client message
            request = await websocket.receive_json()
            print(request)
            interview_id = request["interview_id"]
            if interview_id not in interview_dict:
                interview_dict[interview_id] = {"start_time": datetime.now(), "current_agent": 0}
            
            print(f"interview dict {interview_dict}")
            current_agent =  get_agent(interview_dict[interview_id]["start_time"])
            print(f"current agent {current_agent}")

            prompt_template = get_prompts(current_agent)
            if interview_chain is None:
                print("Interview chain is None and hence, creating it")
                interview_chain = get_chain(stream_handler, prompt_template , tracing=False)

            # Construct a response
            start_resp = ChatResponse(sender="interviewer", message="", type="start")
            await websocket.send_json(start_resp.dict())

            # Start the interview
            if request["msg"] == "START_INTERVIEW":
                print("starting interview")
                result = await interview_chain.acall({"input": "Hi there!"})
                print(f"answer {result}")
                chat_history.append((request["msg"], result["response"]))
            else:
                result = await interview_chain.acall({"input": request["msg"]})
                chat_history.append((request["msg"], result["response"]))
            
            end_resp = ChatResponse(sender="interviewer", message="", type="end")
            await websocket.send_json(end_resp.dict())


            
        except WebSocketDisconnect:
            logging.info("websocket disconnect")
            break
        except Exception as e:
            logging.error(e)
            # resp = ChatResponse(
            #     sender="bot",
            #     message="Sorry, something went wrong. Try again.",
            #     type="error",
            # )
            await websocket.send_json({"msg": "Sorry something went wrong"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)