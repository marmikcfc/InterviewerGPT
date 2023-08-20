import "./App.css";
import AudioRecorder from "../src/AudioRecorder";
import { useState, useEffect, useRef } from "react";

const App = () => {
    const [currentMessage, setCurrentMessage] = useState("");
    const prevMessageRef = useRef();

    const [chatMessages, setChatMessages] = useState([{ "You": "", "Gilfoyle": "" }]);
    const [interviewStarted, setInterviewStarted] = useState(false);

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
                if (socket.current && currentMessage !== "") {
                    const dataToBackend = {
                        interview_id: 1,
                        msg: currentMessage
                    };
                    socket.current.send(JSON.stringify(dataToBackend));
                }

                setCurrentMessage("");
            }
        }, 6000);

        return () => clearInterval(timer);
    }, [currentMessage]);

    useEffect(() => {
        if (interviewStarted) {
            const dataToSend = {
                interview_id: 1,
                msg: "START_INTERVIEW"
            };

            // Initialize socket when interview starts
            socket.current = new WebSocket('ws://localhost:9000/chat');
            socket.current.addEventListener('open', () => {
                socket.current.send(JSON.stringify(dataToSend));
            });

            // Receive messages from WebSocket
            socket.current.addEventListener('message', (event) => {
                const receivedMessage = JSON.parse(event.data);
                console.log('Received message:', receivedMessage);
            });

            // WebSocket close event
            socket.current.addEventListener('close', (event) => {
                console.log('WebSocket connection closed:', event);
                // Perform actions on WebSocket close if needed
            });
        }
    }, [interviewStarted]);

    return (
        <div className="container">
            <h1>InterviewerGPT</h1>
            <div className="recorder">
                <AudioRecorder getCurrentMessage={getCurrentMessage} updateCurrentMessage={updateCurrentMessage} />
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
        </div>
    );
};

export default App;
