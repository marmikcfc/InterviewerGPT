"""Main entrypoint for the app."""
import logging
import pickle
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends, HTTPException
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
import websockets
import elevenlabs




app = FastAPI()
#os.environ["OPENAI_API_KEY"] = ""
logging.basicConfig(level = logging.DEBUG)

chat_history = []
interview_agent = InterviewAgent()
interview_started = False
current_section = InterviewSections.CODING_INTERVIEW_INTRO

ELEVEN_LABS_API_KEY = "5bb83d503e06369aff83abb071ec0f89"  # Set this environment variable or replace with your key
elevenlabs.set_api_key(ELEVEN_LABS_API_KEY)


# Need to handle a case where we need to abruptly stop the interview
def get_current_interview_section(start_time):
    current_agent = InterviewSections.CODING_INTERVIEW_INTRO
    current_time = datetime.now()
    diff = (current_time - start_time).total_seconds() / 60

    # Prompt for intro 
    if diff < 4:
        interview_agent.set_current_chain(InterviewSections.CODING_INTERVIEW_INTRO)
        return InterviewSections.CODING_INTERVIEW_INTRO
    elif diff > 4 and diff < 8:
        interview_agent.set_current_chain(InterviewSections.CODING_INTERVIEW_QUESTION_INTRO)
        return InterviewSections.CODING_INTERVIEW_QUESTION_INTRO
    elif diff > 8 and diff < 30:
        interview_agent.set_current_chain(InterviewSections.CODING_INTERVIEW)
        return InterviewSections.CODING_INTERVIEW
    elif diff >  30 and diff < 55:
        interview_agent.set_current_chain(InterviewSections.CODING_INTERVIEW_CONCLUSION)
        return InterviewSections.CODING_INTERVIEW_CONCLUSION
    elif diff > 35 and diff < 40:
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

# Textual websocket for text
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

async def get_eleven_labs_stream(voice_id: str):
    try:   
        logging.info("Connecting to eleven labs")
        stream = await elevenlabs.stream(voice_id=voice_id, model_id='eleven_monolingual_v1')
        logging.info("Returning stream object")
        return stream

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error connecting to ElevenLabs: {e}")


@app.websocket("/tts/{voice_id}")
async def websocket_endpoint(websocket: WebSocket, voice_id: str, stream_eleven=Depends(get_eleven_labs_stream)):
    await websocket.accept()
    message_queue = asyncio.Queue()

    async def receive_from_client():
        try:
            while True:
                logging.info("!!! Received from client !!!!")
                data = await websocket.receive_text()
                await message_queue.put(data)
        except Exception as e:
            logging.error(f"Error receiving from client: {e}")

    async def process_and_send():
        try:
            while True:
                logging.info("!!! Received from Queue !!!!")
                data = await message_queue.get()
                data = json.loads(data)
                await stream_eleven.send_text(data["msg"])
                
                response = await stream_eleven.receive()
                if response["type"] == "text":
                    await websocket.send_text(response["data"])
                elif response["type"] == "binary":
                    await websocket.send_bytes(response["data"])
        except Exception as e:
            logging.error(f"Error processing and sending: {e}")

    # Use asyncio.gather to run both coroutines in parallel
    try:
        receiver_task = asyncio.create_task(receive_from_client())
        sender_task = asyncio.create_task(process_and_send())
        await asyncio.gather(receiver_task, sender_task)
    except WebSocketDisconnect:
        logging.error("WebSocket disconnected")
        await stream_eleven.close()
    except Exception as e:
        logging.error(f"General error in WebSocket endpoint: {e}")
        await stream_eleven.close()
    finally:
        await stream_eleven.close()
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)