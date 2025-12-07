from io import BytesIO

import chainlit as cl
from langchain_core.messages import AIMessageChunk, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from ai_companion.graph import graph_builder
from ai_companion.modules.image import ImageToText

# Input processing modules (ImageToText, SpeechToText): Imported at interface level to process user uploads app.py:7-9 
# TextToSpeech: Imported at interface level because audio responses need synthesis after graph processing in the audio workflow 
# TextToImage: Not imported because image generation is fully self-contained within the graph workflow

from ai_companion.modules.speech import SpeechToText, TextToSpeech
from ai_companion.settings import settings


# global module instances
speech_to_text = SpeechToText()
text_to_speech = TextToSpeech()
image_to_text = ImageToText()


@cl.on_chat_start
async def on_chat_start():
    """Initialize the chat session"""
    cl.user_session.set("thread_id", 1) # With the current hardcoded thread_id = 1 configuration in the Chainlit interface, you have one continuous conversation thread that persists across all sessions


@cl.on_message
async def on_message(message: cl.Message):
    """Handles text messages and images"""
    empty_msg = cl.Message(content="") # creates an empty Chainlit message object that will be used to stream the AI's response back to the user

    # process any attached images
    content = message.content # message.content contains the text content of a message 
    
    if message.elements:# message.elements is a list of media attachments associated with the message
        for elem in message.elements:
            if isinstance(elem, cl.Image):
                with open(elem.path, "rb") as f:
                    image_bytes = f.read()
                
                # analyze the image and add to the message content
                try:
                    description = await image_to_text.analyze_image(
                        image_data=image_bytes,
                        prompt="Please describe what you see in this image in the context of our conversation.",
                    )
                    content = f"\n[Image Analysis: {description}]"
                except Exception as e:
                    cl.logger.warning(f"Failed to analyze image: {e}")

    thread_id = cl.user_session.get("thread_id")

    async with cl.Step(type="run"):
        async with AsyncSqliteSaver.from_conn_string(conn_string=settings.SHORT_TERM_MEMORY_DB_PATH) as short_term_memory:
            graph = graph_builder.compile(checkpointer=short_term_memory)
            async for chunk in graph.astream(
                {"messages": [HumanMessage(content=content)]},
                {"configurable": {"thread_id": thread_id}},
                stream_mode="messages",
            ):
                # chunk[0] - The message content itself (the actual AIMessageChunk object containing the text being generated)
                # chunk[1] - The metadata dictionary containing information about where this chunk came from, including the "langgraph_node" key that identifies which node in the graph produced this chunk
                if chunk[1]["langgraph_node"] == "conversation_node" and isinstance(chunk[0], AIMessageChunk):
                    await empty_msg.stream_token(chunk[0].content)
                
            output_state = await graph.aget_state(config={"configurable": {"thread_id": thread_id}})

            # The key distinction: async with is for resource management (like database connections), async for is for iterating over async streams, and async def declares functions that can perform async operation
    
    if output_state.values.get("workflow") == "audio":
        response = output_state.values["messages"][-1].content
        # Line 76 retrieves audio that was generated within the graph workflow, while line 131 generates audio outside the graph after receiving the graph's text response.
        audio_buffer = output_state.values["audio_buffer"]
        output_audio_element = cl.Audio(
            name="Audio",
            auto_play=True,
            mime="audio/mpeg3",
            content=audio_buffer,
        )
        await cl.Message(content=response, elements=[output_audio_element]).send()
    elif output_state.values.get("workflow") == "image":
        response = output_state.values["messages"][-1].content
        image_element = cl.Image(path=output_state.values["image_path"], display="inline")
        await cl.Message(content=response, elements=[image_element]).send()
    else:
        await empty_msg.send()


@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    """Handle incoming chunks"""
    if chunk.isStart:
        buffer = BytesIO()
        buffer.name = f"input_audio.{chunk.mimeType.split("/")[1]}"
        cl.user_session.set("audio_buffer", buffer)
        cl.user_session.set("mime_type", chunk.mimeType)
    cl.user_session.get("audio_buffer").write(chunk.data)


@cl.on_audio_end
async def on_audio_end(elements): # This allows the function to accept additional UI elements (like images or files) that the user might have attached along with their audio message, and display them all together in the chat.
    """Handle audio data from audio buffer"""
    # get audio data
    audio_buffer = cl.user_session.get("audio_buffer")
    audio_buffer.seek(0) # retrieve audio from the beginning
    audio_data = audio_buffer.read()

    # show user's audio message
    input_audio_element = cl.Audio(mime="audio/mpeg3", content=audio_data)
    await cl.Message(author="You", content="", elements=[input_audio_element, *elements]).send()


    # use the global SpeechToText instance
    transcription = await speech_to_text.transcribe(audio_data)

    thread_id = cl.user_session.get("thread_id")

    # Without lines 123-139, the user's voice message would be transcribed but never answered. Without lines 120-128, the AI would generate a text response but the user wouldn't hear it as audio - breaking the voice conversation experience.

    async with AsyncSqliteSaver.from_conn_string(settings.SHORT_TERM_MEMORY_DB_PATH) as short_term_memory:
        graph = graph_builder.compile(checkpointer=short_term_memory)
        output_state = await graph.ainvoke(
            {"messages": [HumanMessage(content=transcription)]},
            {"configurable": {"thread_id": thread_id}},
        )

    # use global TextToSpeech instance
    audio_buffer = await text_to_speech.synthesize(output_state["messages"][-1].content)

    output_audio_element = cl.Audio(
        name="Audio",
        auto_play=True,
        mime="audio/mpeg3",
        content=audio_buffer,
    )
    await cl.Message(content=output_state["messages"][-1].content, elements=[output_audio_element]).send()
