# Gilfoyle

Just an AI interviewer to reducem, bias, TAT, enginerring bandwidth for tech interviews.

Interviewing is painful process and it takes a lot of engineering bandwidth, there's issue with interviewer bias, TAT is high due to which companies sometimes tend to miss out on talented candidates. So ideally, app should
1. have an agent to take interview
2. Upload the transcript in transcripts section
3. Transcript should be summarised and searchable for human recuriter
4. Provide feedback to the user pretty quickly

## Task
- [X] Set up websockets over fastapi 
- [X] Set up chains, streaming, intro to interview agent
- [x] Set up output parser to collect words from a stream of tokens so that eleven labs api can be streamed
- [] Agentify the structure to be able to add multiple chain
- [] Set up other agents to carry out a full coding interview 
- [] Refactor and remove all the crap that might have been introduced by now
- [] React frontend with editor and react chat window
- [] Add openAI Whisper for the Speech to text
- [] Add elevenlabs for text to speech and direct audio transfer over websocklets
- [] Store transcripts in vector store for semantic search
- [] View transcripts on a dashboard
- [] System design interview
- [] Mermaidjs integration for the system design interview
- [] Behavioural interview
- [] Slides
- [] Demo