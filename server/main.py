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
from typing import Iterator, Optional, AsyncIterator
import asyncio
from websockets.exceptions import ConnectionClosedError


message_queue = asyncio.Queue()
asyncio.get_event_loop().set_debug(True)


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

#Websocket for text to speech
#TODO integrate with the actual stream generation from LLM to avoid two and fro from server to client
#TODO persist websocket connection to makes sure that it can be reused
@app.websocket("/tts")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        print("Before generate")
        
        # Start message_generator in the background
        task = asyncio.create_task(message_generator(websocket))
        
        async for audio_chunk in generate_stream_input(voice="IsQVxKZH6osrAZXuiOdd", model="eleven_monolingual_v1", api_key="5bb83d503e06369aff83abb071ec0f89"):
            print("Post generate")
            if audio_chunk == "":
                continue
            await websocket.send_bytes(audio_chunk)
    except Exception as e:
        print(f"error {e}")
    finally:
        task.cancel()  # Cancel the message_generator task when done

async def message_generator(websocket: WebSocket):
    while True:
        try:
            print("Waiting for WebSocket message...")
            data = await websocket.receive_text()
            data = json.loads(data)
            print(f"data {data}")
            await message_queue.put(data["msg"])
            print(f"Added message to queue: {data['msg']}")
        except ConnectionClosedError:
            print("WebSocket connection closed.")
            break

async def text_chunker_from_queue() -> AsyncIterator[str]:
    """Used during input streaming to chunk text blocks and set last char to space"""
    splitters = (".", ",", "?", "!", ";", ":", "—", "-", "(", ")", "[", "]", "}", " ")
    buffer = ""
    print("In text chunker from queue")
    while True:
        print("Waiting to get message from queue...")

        text = await message_queue.get()
        print(f"Got {text}")
        if buffer.endswith(splitters):
            t = buffer if buffer.endswith(" ") else buffer + " "
            print(f"Yielding in if {t}")
            yield t
            buffer = text
        elif text.startswith(splitters):
            output = buffer + text[0]
            t = output if output.endswith(" ") else output + " "
            print(f"Yielding in elif {t}")
            yield output if output.endswith(" ") else output + " "
            buffer = text[1:]
        else:
            buffer += text
            yield buffer + " "
            buffer = ""


async def generate_stream_input( voice, model, api_key: Optional[str] = None) -> Iterator[bytes]:
    print("IN generate stream input")
    BOS = {
        "text": " ",
        "try_trigger_generation": True,
        "voice_settings": None,
        "generation_config": {
            "chunk_length_schedule": [50],
        },
        "xi-api-key": api_key  # Add your xi-api-key here with hyphens
    }
    BOS = json.dumps(BOS)

    EOS = json.dumps({"text":"", "xi-api-key": api_key })

    async with websockets.connect(
        f"wss://api.elevenlabs.io/v1/text-to-speech/{voice}/stream-input?model_id={model}"
    ) as websocket:
        print("Concceted to websocket")
        # Send beginning of stream
        await websocket.send(BOS)
        # Stream text chunks and receive audio
        async for text_chunk in text_chunker_from_queue():
            print(f"Got text_chuunk {text_chunk}")
            data = dict(text=text_chunk, try_trigger_generation=True)
            await websocket.send(json.dumps({"text":text_chunk, "try_trigger_generation":True , "xi-api-key": api_key}))
            await websocket.send(EOS)
            print("sent to the websocket")
            try:
                print("waiting to revieve websocket")
                data = json.loads(await asyncio.wait_for(websocket.recv(), timeout=10))
                print(data)
                if data["audio"]:
                    yield data["audio"] 
            except websockets.exceptions.ConnectionClosedOK:
                print("Connection closed ")
                break
            except asyncio.TimeoutError:
                print("WebSocket response timed out!")
                break

        # Receive remaining audio
        while True:
            try:
                data = await json.loads(await websocket.recv())
                if data["audio"]:
                    yield data["audio"]
            except websockets.exceptions.ConnectionClosedOK:
                print("Connection closed ")
                break
                
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)