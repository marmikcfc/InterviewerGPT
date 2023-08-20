import "./App.css";
import AudioRecorder from "./AudioRecorder";
import { useState, useEffect, useRef } from "react";
import { CodeEditor } from "./CodeEditor";
import { Chat } from "./ChatWindow";

const App = () => {
    const [currentMessage, setCurrentMessage] = useState("");
    const [currentReceivedMessage, setCurrentReceivedMessage] = useState("");
    const [chatMessages, setChatMessages] = useState([]);
    const [waitingForStreamToEnd, setWaitingForStreamToEnd] = useState(false)
    const [interviewId, setInterviewId] = useState(Math.random())
    const [initialContent, setInitialContent] = useState("// piedpiper phone interivew")

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
                        msg: currentMessage
                    };
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

        }
        else if (message.type === "info") {
            // Handle the actual stream message
            console.log("info message:", message.message);
            if (message.message.includes("QUESTION")) {
                console.log(`Qustion Message: ${message.message}`)
                setInitialContent((_initialContent) => _initialContent + "\n" + message.message)
            }

        } else if (message.type === "end") {

            if (interviewState == "start") {
                setInterviewState("started")
            }

            // Handle the end of the stream
            // Update chatMessages state if needed

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
                msg: "START_INTERVIEW"
            };

            setWaitingForStreamToEnd(true);

            // Initialize socket only if it's not already initialized
            if (!interviewSocket.current) {
                interviewSocket.current = new WebSocket('ws://localhost:9000/chat');

                interviewSocket.current.addEventListener('open', () => {
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
                    <CodeEditor initialContent={initialContent} setQuestion={initialContent.includes("QUESTION")} />
                </div>
                <div className="chat-window">
                    <h2>Chat Window</h2>
                    <Chat chatMessages={chatMessages} />
                </div>
            </div>

            Current Message Transcribed from Deepgram:  {currentMessage}
            <br />
            Received Message : {JSON.stringify(chatMessages)}
        </div>
    );
};

export default App;
