from langgraph.graph import MessagesState

class AICompanionState(MessagesState):
    """State class for the AI companion workflow
    
    Extends MessageState to track conversation history and maintain the last message received.

    Attributes:
        summary(str): Summary of the conversation between Tela and the user.
        workflow(str): The current workflow the AI Companion is in. Can be "conversation", "image" or "audio"
        audio_buffer(bytes): The audio buffer used for speech-to-text conversion.
        image_path(str): The path to where the current image file is stored if any
        current_activity(str): The current activity of Tela based on the schedule
        apply_activity(bool): Flag indicating whether a new activity should be applied.
        memory_context(str): The context of the memories to be injected into the character card.
    """

    summary: str
    workflow: str
    audio_buffer: bytes
    image_path: str
    current_activity: str
    apply_activity: bool
    memory_context: str
