import React, { useRef } from 'react';
import ReactDOM from 'react-dom';
import Editor from '@monaco-editor/react';
import { useState } from 'react';
import { FormControl, InputLabel, Select, MenuItem } from "@mui/material";
import "./Chat.css";

export function Chat(props) {
    const editorRef = useRef(null);

    const monacoRef = useRef(null);
    function handleEditorDidMount(editor, monaco) {
        editorRef.current = editor;
        monacoRef.current = monaco;
    }

    function showValue() {
        alert(editorRef.current.getValue());
    }

    const [languages, setLanguages] = useState([
        "javascript",
        "python",
        "java",
        "c++",
        "ruby",
        "php"
    ]);
    const [language, setLanguage] = useState("javascript");

    function handleChange(event) {
        monacoRef.current.editor.setModelLanguage(editorRef.current.getModel(), event.target.value);
        setLanguage(event.target.value);
    }


    return (

        <div className="message-list">
            {props.chatMessages.map((message, index) => (
                <div key={index} className="message">
                    {message}
                </div>
            ))}
        </div>
    )
}