import os
import logging
from io import BytesIO
from typing import Dict

import httpx
from fastapi import APIRouter, Request, Response, Header
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from graph import graph_builder
from ai_companion.modules.image import ImageToText
from ai_companion.modules.speech import SpeechToText, TextToSpeech
from ai_companion.settings import settings

logger = logging.getLogger(__name__)

image_to_text = ImageToText()
speech_to_text = SpeechToText()
text_to_speech = TextToSpeech()

telegram_router = APIRouter()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SECRET_WEBHOOK_TOKEN = os.getenv("SECRET_WEBHOOK_TOKEN")

@telegram_router.api_route(path="/telegram_response.py", methods=[ "POST"]) # Telegram ignores GET for webhooks
async def telegram_handler(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None) #retrieves the secret token sent by Telegram as an HTTP header
    ) -> Response:
    """Handle incoming messages and status updates from Telegram Cloud API."""
    
    if request.method == "POST":
        if x_telegram_bot_api_secret_token != SECRET_WEBHOOK_TOKEN:
            return Response(content="Token mismatch", status_code=403)
        return Response(content="Received Telegram data", status_code=200)

    try:
        update_payload = await request.json()

        if "message" in update_payload:
            msg_dict = update_payload["message"][0]
            from_id = msg_dict["from"]["id"]
            session_id = msg_dict["from"]["id"]

            content = ""
            if "audio" in msg_dict:
                content = await process_audio_message(msg_dict)
            elif "photo" in msg_dict:
                content = msg_dict.get("caption", "")
                image_bytes = await download_media(msg_dict["photo"]["file_id"])
                try:
                    description = await image_to_text.analyze_image(
                        image_data=image_bytes,
                        prompt="Please describe what you see in this image in the context of our conversation.",
                    )
                    content += f"[Image Analysis: {description}]"
                except Exception as e:
                    logger.warning(f"Failed to analyze the image: {e}")
            else:
                content = msg_dict["text"]

            # process the message through the graph agent
            async with AsyncSqliteSaver.from_conn_string(settings.SHORT_TERM_MEMORY_DB_PATH) as short_term_memory:
                graph = graph_builder.compile(checkpointer=short_term_memory)
                await graph.ainvoke(
                    {"messages": [HumanMessage(content=content)]},
                    {"configurable": {"thread_id": session_id}}
                )

                # get the workflow type and response from the state
                output_state = graph.aget_state(config={"configurable": {"thread_id": session_id}})

            workflow = output_state.values.get("workflow", "conversation")
            response_message = output_state.values["messages"][-1].content # extracts the AI-generated response that will be sent back to the WhatsApp user


            if workflow == "audio":
                audio_buffer = output_state.values["audio_buffer"]
                success = await send_response(from_id, response_message, "audio", audio_buffer)
            elif workflow == "image":
                image_path = output_state.values["image_path"]
                with open(image_path, "rb") as f:
                    image_data = f.read()
                success = await send_response(from_id, response_message, "image", image_data)
            else:
                success = await send_response(from_id, response_message, "text")
            

            if not success:
                return Response(content="Failed to send message", status_code=500)
            
            return Response(content="Message processed", status_code=200)
        
        else:
            return Response(content="Unknown event type", status_code=400)
        
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        return Response(content="Internal server error", status_code=500)
    
      
async def download_media(media_id: str) -> bytes:
    """Download media from Telegram via media id"""
   
   # step 1: get the media path for the media id
    media_metadata_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile"
    params={"file_id": media_id}


    async with httpx.AsyncClient() as client:
        metadata_response = await client.get(url=media_metadata_url, params=params)
        metadata_response.raise_for_status()
        metadata = metadata_response.json()
        media_path = metadata["results"]["file_path"]

        # step 2: construct the download url and fetch the content
        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{media_path}"
        media_response = await client.get(download_url)
        media_response.raise_for_status()
        return media_response.content
    

async def process_audio_message(msg_dict: Dict) -> str:
    """Download and transcribe audio message"""
    audio_id = msg_dict["audio"]["file_id"]
    media_data_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile"
    params = {"file_id": audio_id}

    async with httpx.AsyncClient() as client:
        metadata_response = await client.get(url=media_data_url, params=params)
        metadata_response.raise_for_status()
        metadata = metadata_response.json()
        media_path = metadata["results"]["file_path"]

    # download the audio file
    async with httpx.AsyncClient() as client:
        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{media_path}"
        audio_response = await client.get(url=download_url, params=params)
        audio_response.raise_for_status()

    # prepare for transcription
    audio_buffer = BytesIO(audio_response.content)
    audio_buffer.seek(0)
    audio_data = audio_buffer.read()

    return await speech_to_text.transcribe(audio_data)

#  The Telegram Bot API uses different endpoints and payload structures for each media type, but you can wrap them in a unified function.

# # To upload media for Telegram, you do not use a separate upload endpoint (like WhatsApp's /media). Instead, you upload media as part of sending a message (e.g., photo, audio, document, video, etc.) by making a multipart HTTP POST request to the appropriate send method (like /sendPhoto, /sendAudio, etc.)
async def send_response(
        from_id: int,
        response_message: str,
        message_type: str = "text",
        media_content: bytes = None,
) -> bool:
    """Send response messages via the Telegram API"""

    BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    try:

        async with httpx.AsyncClient() as client:
                if message_type == "text":
                    url = f"{BASE_URL}/sendMessage"
                    payload = {"chat_id": from_id, "text": response_message}
                    resp = await client.post(url=url, data=payload)
                    return resp.status_code == 200
                
                elif message_type == "image":                
                    # When you successfully send a media message (photo, audio, etc.), Telegram returns a "file_id" for each uploaded file in the response.

                    url = f"{BASE_URL}/sendPhoto"
                    payload = {"chat_id": from_id}
                    if response_message:
                        payload["caption"] = response_message
                        # If media_content is bytes, you should wrap it as a tuple. httpx requires (filename, bytes, mimetype).
                    files = {"photo": ("image.jpg", media_content, "image/jpeg")}
                    resp = await client.post(url=url, data=payload, files=files)
                    return resp.status_code == 200
                elif message_type == "audio":
                    url = f"{BASE_URL}/sendAudio"
                    payload = {"chat_id": from_id}
                    files = {"audio": ("file.mp3", media_content, "audio/mpeg")}
                    resp = await client.post(url=url, data=payload, files=files)
                    return resp.status_code == 200
                else:
                    logger.error("Unsupported message_type")
                    return False
    
    except Exception as e:
        logger.error(f"Message send failed: {e}")
        return False