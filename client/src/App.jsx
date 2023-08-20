import "./App.css";
import AudioRecorder from "../src/AudioRecorder";
import { useState, useEffect, useRef } from "react";

const App = () => {
    const [currentMessage, setCurrentMessage] = useState("");
    const prevMessageRef = useRef();

    const [chatMessages, setChatMessages] = useState([{ "You": "", "Gilfoyle": "" }]);
    useEffect(() => {
        prevMessageRef.current = currentMessage;
    }, [currentMessage]);

    useEffect(() => {
        const timer = setInterval(() => {
            if (prevMessageRef.current === currentMessage) {
                setCurrentMessage("");
            }
        }, 6000);

        return () => clearInterval(timer);
    }, [currentMessage]);

    return (
        <div className="container">
            <h1>DeepGram Live Transcription</h1>
            <div className="recorder">
                <AudioRecorder />
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
