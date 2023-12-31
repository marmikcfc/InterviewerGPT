import "./App.css";
import AudioRecorder from "./AudioRecorder";
import { useState, useEffect, useRef } from "react";
import { CodeEditor } from "./CodeEditor";
import { Chat } from "./ChatWindow";

import ReactAudioPlayer from 'react-audio-player';

const App = () => {
    const [currentMessage, setCurrentMessage] = useState("");
    const [currentReceivedMessage, setCurrentReceivedMessage] = useState("");
    const [chatMessages, setChatMessages] = useState([]);
    const [waitingForStreamToEnd, setWaitingForStreamToEnd] = useState(false)
    const [interviewId, setInterviewId] = useState(Math.random())
    const [initialContent, setInitialContent] = useState("#piedpiper phone interivew")
    const [audioSrc, setAudioSrc] = useState(null);
    const [currentEditorContent, setCurrentEditorContent] = useState("#piedpiper phone interivew");

    var startTime = Date.now();

    const prevMessageRef = useRef();

    var currentAudioMessage = "";

    const [interviewState, setInterviewState] = useState("");

    const updateCurrentMessage = (message) => {
        setCurrentMessage(message);
    }

    const addToCurrentAudioMessage = (msg) => {
        currentAudioMessage = currentAudioMessage + " " + message
    }

    const getCurrentMessage = () => {
        return currentMessage;
    }


    // Setup eleven api
    const apiKey = `${import.meta.env.VITE_ELEVEN_LABS_API_KEY}`; // Replace with your Elevenlabs API key
    const voiceId = "IsQVxKZH6osrAZXuiOdd"; // Brian
    const headers = new Headers();
    headers.append('Accept', 'audio/mpeg');
    headers.append('xi-api-key', apiKey);
    headers.append('Content-Type', 'application/json');

    var ttsTextBuffer = ""
    var waitForTTSStreamToEnd = false
    const speak = (text) => {
        console.log(`starting to speak ${text} waitForTTSStreamToEnd ${waitForTTSStreamToEnd}`)
        waitForTTSStreamToEnd = true;
        const body = JSON.stringify({
            text: text,
            model_id: 'eleven_monolingual_v1',
            voice_settings: {
                stability: 0.5,
                similarity_boost: 0.5
            }
        });

        fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}/stream`, {
            method: 'POST',
            headers: headers,
            body: body
        })
            .then(response => response.blob())
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                var audio = new Audio(url)

                audio.addEventListener('ended', () => {
                    console.log('Audio playback has completed. Making waitForTTSStreamToEnd = false');
                    waitForTTSStreamToEnd = false
                });

                audio.play()


            })
            .catch(error => console.error('Error:', error));
    };


    // Initialize socket as a class variable
    const interviewSocket = useRef(null);

    useEffect(() => {
        prevMessageRef.current = currentMessage;

    }, [currentMessage]);

    useEffect(() => {
        const timer = setInterval(() => {
            if (prevMessageRef.current === currentMessage) {
                // Send currentMessage to the backend before clearing
                if (interviewSocket.current && currentMessage !== "" && !waitingForStreamToEnd) {
                    const dataToBackend = {
                        interview_id: interviewId,
                        msg: currentMessage,
                        justCode: false
                    };
                    startTime = Date.now()
                    interviewSocket.current.send(JSON.stringify(dataToBackend));
                    //currentAudioMessage = ""
                    setCurrentMessage("");
                }
            }
        }, 6000);

        return () => {
            clearInterval(timer);
        };
    }, [currentMessage]);


    const sendCurrentCode = (code) => {
        if (!waitingForStreamToEnd) {

            // Every minute and a half send the coding update for the LLM to review asynchronously.
            // Preferably dispatch a webworker? 
            if (code != currentEditorContent) {
                const dataToBackend = {
                    interview_id: interviewId,
                    msg: code,
                    justCode: true
                };
                console.log(`Sending to backend ${JSON.stringify(dataToBackend)}`)
                startTime = Date.now()
                interviewSocket.current.send(JSON.stringify(dataToBackend));
                setWaitingForStreamToEnd(true)
            } else {
                console.log("No changes in the editor and hence not sending it to backend")
            }


        } else {
            // just append to current message
            setCurrentMessage((_msg) => _msg + "\n CODE" + code)
        }
    }


    var currMessage = ""
    var prevMessages = []
    // Function to handle incoming messages from server
    const handleIncomingMessage = (message) => {

        if (message.type === "start") {
            // Handle the start of the stream
            currMessage = ""
            console.log("Stream started:", message);

        } else if (message.type === "stream") {
            // Handle the actual stream message

            console.log("Stream message:", message.message);
            currMessage += message.message
            ttsTextBuffer += message.message
            if (!waitForTTSStreamToEnd) {
                speak(ttsTextBuffer)
                ttsTextBuffer = ""
            }


        }
        else if (message.type === "info") {
            // Handle the actual stream message
            console.log("info message:", message.message);
            if (message.message.includes("QUESTION")) {
                console.log(`Qustion Message: ${message.message}`)
                setInitialContent((_initialContent) => _initialContent + "\n" + message.message)
                setCurrentEditorContent((_currentEditorContent) => _currentEditorContent + "\n" + message.message)
            }

        } else if (message.type === "end") {

            if (interviewState == "start") {
                setInterviewState("started")
            }

            const intervalId = setInterval(() => {
                if (!waitForTTSStreamToEnd) {
                    console.log("The waitForTTSStreamToEnd is now false! Let's start with the next stream");
                    speak(ttsTextBuffer);
                    ttsTextBuffer = "";
                    clearInterval(intervalId);
                } else {
                    console.log("Waiting for the waitForTTSStreamToEnd to become false...");
                }
            }, 300); // Check every 0.3 second


            // Handle the end of the stream
            // Update chatMessages state if needed

            var latency = Date.now() - startTime;
            console.log(`Latency: ${latency} ms`);
            //speak(currMessage)

            prevMessages.push(currMessage);
            setChatMessages([...prevMessages])

            setWaitingForStreamToEnd(false);
            console.log("Stream ended:", message);
        }
    };


    useEffect(() => {
        if (interviewState === "start") {
            const dataToSend = {
                interview_id: 1,
                msg: "START_INTERVIEW",
                justCode: false
            };

            setWaitingForStreamToEnd(true);

            // Initialize socket only if it's not already initialized
            if (!interviewSocket.current) {
                interviewSocket.current = new WebSocket('ws://localhost:9000/chat');

                interviewSocket.current.addEventListener('open', () => {
                    startTime = Date.now();
                    interviewSocket.current.send(JSON.stringify(dataToSend));
                });

                // Receive messages from WebSocket
                interviewSocket.current.addEventListener('message', (event) => {
                    const receivedMessage = JSON.parse(event.data);
                    handleIncomingMessage(receivedMessage);
                });

                // WebSocket close event
                interviewSocket.current.addEventListener('close', (event) => {
                    console.log('WebSocket connection closed:', event);
                });
            }
        }
    }, [interviewState]);

    useEffect(() => {
        if (interviewState === "end") {
            // Close WebSocket connection when interview ends
            if (interviewSocket.current) {
                alert("closing the websocket");
                interviewSocket.current.close();
                interviewSocket.current = null;  // Reset socket ref after closing
            }
        }
    }, [interviewState]);


    return (
        <div className="container">
            <h1>InterviewerGPT</h1>
            <div className="recorder">
                <AudioRecorder getCurrentMessage={getCurrentMessage} updateCurrentMessage={updateCurrentMessage} toggleInterviewState={setInterviewState} />
            </div>
            <div className="content">
                <div className="coding-editor">
                    <CodeEditor initialContent={initialContent} setQuestion={initialContent.includes("QUESTION")} sendCurrentCode={sendCurrentCode} />
                </div>
                <div className="chat-window">
                    <h2>Chat Window</h2>
                    <Chat chatMessages={chatMessages} />
                </div>
            </div>

            <div style={{ display: "none" }}>
                {audioSrc && (
                    <ReactAudioPlayer
                        src={audioSrc}
                        autoPlay
                        controls
                    />
                )}
            </div>


            Current Message Transcribed from Deepgram:  {currentMessage}
            <br />
            Received Message : {JSON.stringify(chatMessages)}
        </div>
    );
};

export default App;
