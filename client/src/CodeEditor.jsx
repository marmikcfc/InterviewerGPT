import React, { useRef } from 'react';
import ReactDOM from 'react-dom';
import Editor from '@monaco-editor/react';
import { useState } from 'react';
import { FormControl, InputLabel, Select, MenuItem } from "@mui/material";
import { useEffect } from 'react';

export function CodeEditor(props) {
    const editorRef = useRef(null);

    const monacoRef = useRef(null);
    function handleEditorDidMount(editor, monaco) {
        editorRef.current = editor;
        monacoRef.current = monaco;
        if (props.question != null) {
            editorRef.current.getModel().setValue(props.initialContent)
        }
    }

    const [content, setQuestion] = useState(props.initialContent);


    // Every 60 seconds let the interviewer know what you're typing.
    useEffect(() => {
        const timer = setInterval(() => {
            var currentCode = editorRef.current.getValue()
            props.sendCurrentCode(currentCode);
        }, 6000)
        return () => {
            clearInterval(timer);
        };
    });


    useEffect(() => {
        if (editorRef.current) {
            editorRef.current.setValue(props.initialContent);
        }
        //alert(`content ${content}`)
    }, [content]);


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
    const [language, setLanguage] = useState("python");

    function handleChange(event) {
        monacoRef.current.editor.setModelLanguage(editorRef.current.getModel(), event.target.value);
        setLanguage(event.target.value);
    }




    return (
        <div>

            {/* <button onClick={showValue}>Show value</button> */}

            <FormControl>
                <InputLabel htmlFor="programming-language">Programming Langugage</InputLabel>
                <Select
                    value={language}
                    onChange={handleChange}
                    inputProps={{
                        name: "programming language",
                        id: "programming-languge"
                    }}
                >
                    {languages.map((value, index) => {
                        return <MenuItem value={value}>{value}</MenuItem>;
                    })}
                </Select>
            </FormControl>

            <Editor
                height="80vh"
                theme="vs-dark"
                defaultLanguage="python"
                defaultValue={props.initialContent}
                onMount={handleEditorDidMount}
                key={props.initialContent}
            />
        </div>
    )
}