from pydantic import Field
from langchain import Agent, OpenAI, ConversationChain, AgentOutputParser, ConversationBufferMemory

class ConversationalAgent(Agent):
    """A conversational agent that uses the ConversationChain for interactions and maintains chat history."""
    
    llm_chain: ConversationChain = Field(default_factory=lambda: ConversationChain(llm=OpenAI()))
    output_parser: AgentOutputParser = Field(default_factory=AgentOutputParser)
    memory: ConversationBufferMemory = Field(default_factory=ConversationBufferMemory)

    def __init__(self, **data):
        super().__init__(**data)
        # Set the memory for the ConversationChain
        self.llm_chain.memory = self.memory

    def interact(self, message: str) -> str:
        """
        Interact with the agent using a given message.

        Args:
        - message (str): The input message for the agent.

        Returns:
        - str: The agent's response.
        """
        response = self.llm_chain(message)
        return response

    def get_chat_history(self) -> list:
        """
        Retrieve the chat history from the agent's memory.

        Returns:
        - list: The chat history.
        """
        return self.memory.get_history()

# Example usage:
agent = ConversationalAgent()
response1 = agent.interact("Hello, how are you?")
print(response1)

response2 = agent.interact("Tell me more about yourself.")
print(response2)

# Retrieve chat history
history = agent.get_chat_history()
print(history)
