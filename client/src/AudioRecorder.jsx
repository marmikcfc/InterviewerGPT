import { useRef, useState } from "react";
import { Deepgram } from "@deepgram/sdk/browser";

const mimeType = "audio/webm";
const deepGram = new Deepgram(`${import.meta.env.VITE_DG_API_KEY}`)

const AudioRecorder = (props) => {
    const [permission, setPermission] = useState(false);
    const mediaRecorder = useRef(null);
    const [recordingStatus, setRecordingStatus] = useState("inactive");
    const [stream, setStream] = useState(null);
    const [audioChunks, setAudioChunks] = useState([]);
    const [audio, setAudio] = useState(null);
    const [transcripts, setTranscript] = useState([]);


    const getMicrophonePermission = async () => {
        if ("MediaRecorder" in window) {
            try {
                const streamData = await navigator.mediaDevices.getUserMedia({
                    audio: true,
                    video: false,
                });
                setPermission(true);
                setStream(streamData);
            } catch (err) {
                alert(err.message);
            }
        } else {
            alert("The MediaRecorder API is not supported in your browser.");
        }
    };

    const startRecording = async () => {

        console.log("Starting the interview")
        props.toggleInterviewState("start")
        setRecordingStatus("recording");
        mediaRecorder.current = new MediaRecorder(stream, { type: mimeType });

        const deepGramSocket = deepGram.transcription.live({
            interim_results: true, punctuate: true, language: "en-US", model: "nova", endpointing: true,
        });

        deepGramSocket.addEventListener('open', () => {
            mediaRecorder.current.addEventListener('dataavailable', async (event) => {
                if (event.data.size > 0 && deepGramSocket.readyState === 1) {
                    deepGramSocket.send(event.data)
                }
            })
            mediaRecorder.current.start(250)
        });

        deepGramSocket.addEventListener("message", (message) => {
            const received = JSON.parse(message.data);
            console.log(received);
            const transcript = received.channel.alternatives[0].transcript;
            if (transcript && received.is_final) {
                setTranscript((_prev) => [..._prev, transcript]);
                //var currentMessage = props.getCurrentMessage();
                //currentMessage += " " + transcript;
                props.updateCurrentMessage((_currMessage) => _currMessage + " " + transcript);
                console.log(`transcript ${transcript}`);
            }
        });

        deepGramSocket.addEventListener("close", () => {
            console.log("Connection closed.");
        });

        let localAudioChunks = [];
        mediaRecorder.current.ondataavailable = (event) => {
            if (typeof event.data === "undefined") return;
            if (event.data.size === 0) return;
            localAudioChunks.push(event.data);
        };
        setAudioChunks(localAudioChunks);
    };

    const stopRecording = () => {
        console.log("Stopping the interview")
        props.toggleInterviewState("end")
        setRecordingStatus("inactive");
        mediaRecorder.current.stop();
        mediaRecorder.current.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: mimeType });
            const audioUrl = URL.createObjectURL(audioBlob);
            setAudio(audioUrl);
            setAudioChunks([]);
        };
    };

    return (
        <div>
            <main>
                <div className="audio-controls">
                    {!permission ? (
                        <button onClick={getMicrophonePermission} type="button">
                            Allow Microphone
                        </button>
                    ) : null}
                    {permission && recordingStatus === "inactive" ? (
                        <button onClick={startRecording} type="button">
                            Start Interview
                        </button>
                    ) : null}
                    {recordingStatus === "recording" ? (
                        <button onClick={stopRecording} type="button">
                            Stop Interview
                        </button>
                    ) : null}
                </div>
                {/* {audio ? (
                    <div className="audio-player">
                        <audio src={audio} controls></audio>
                        <br />
                        <button>
                            <a download href={audio}>
                                Download Recording
                            </a>
                        </button> 
                    </div>
                ) : null} */}
            </main>

        </div>
    );
};
export default AudioRecorder;