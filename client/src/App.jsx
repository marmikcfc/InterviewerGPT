import "./App.css";
import AudioRecorder from "../src/AudioRecorder";
import { useState, useEffect, useRef } from "react";

const App = () => {
    const [currentMessage, setCurrentMessage] = useState("");
    const [currentReceivedMessage, setCurrentReceivedMessage] = useState("");
    const [chatMessages, setChatMessages] = useState([]);
    const [waitingForStreamToEnd, setWaitingForStreamToEnd] = useState(false)
    const [interviewId, setInterviewId] = useState(Math.random())
    const prevMessageRef = useRef();


    const [interviewState, setInterviewState] = useState("");

    const updateCurrentMessage = (message) => {
        setCurrentMessage(message);
    }

    const getCurrentMessage = () => {
        return currentMessage;
    }

    // Initialize socket as a class variable
    const socket = useRef(null);

    useEffect(() => {
        prevMessageRef.current = currentMessage;
    }, [currentMessage]);

    useEffect(() => {
        const timer = setInterval(() => {
            if (prevMessageRef.current === currentMessage) {
                // Send currentMessage to the backend before clearing
                if (socket.current && currentMessage !== "" && !waitingForStreamToEnd) {
                    const dataToBackend = {
                        interview_id: interviewId,
                        msg: currentMessage
                    };
                    socket.current.send(JSON.stringify(dataToBackend));
                    setCurrentMessage("");
                }
            }
        }, 6000);

        return () => {
            clearInterval(timer);
            // Close WebSocket connection when component unmounts or interview ends
            if (socket.current) {
                socket.current.close();
            }
        };
    }, [currentMessage]);

    var currMessage = ""

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

        } else if (message.type === "end") {

            if (interviewState == "start") {
                setInterviewState("started")
            }

            // Handle the end of the stream
            // Update chatMessages state if needed

            let prevMessages = [...chatMessages];
            prevMessages.push(currMessage);
            setChatMessages([...prevMessages])


            setWaitingForStreamToEnd(false);
            console.log("Stream ended:", message);
        }
    };


    useEffect(() => {
        if (interviewState == "start") {
            const dataToSend = {
                interview_id: interviewId,
                msg: "START_INTERVIEW"
            };

            // Initialize socket when interview starts
            socket.current = new WebSocket('ws://localhost:9000/chat');
            socket.current.addEventListener('open', () => {
                socket.current.send(JSON.stringify(dataToSend));
            });
            setWaitingForStreamToEnd(true);

            // Receive messages from WebSocket
            socket.current.addEventListener('message', (event) => {
                const receivedMessage = JSON.parse(event.data);
                handleIncomingMessage(receivedMessage);
            });

            // WebSocket close event
            socket.current.addEventListener('close', (event) => {
                console.log('WebSocket connection closed:', event);
                // Perform actions on WebSocket close if needed
            });
        } else if (interviewState == "end") {
            // Close WebSocket connection when interview ends
            if (socket.current) {
                socket.current.close();
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
                    <h2>Coding Editor</h2>
                    {/* Your coding editor content here */}
                </div>
                <div className="chat-window">
                    <h2>Chat Window</h2>
                    {/* Your chat window content here */}
                </div>
            </div>

            Current Message Transcribed from Deepgram:  {currentMessage}
            <br />
            Received Message : {JSON.stringify(chatMessages)}
        </div>
    );
};

export default App;
