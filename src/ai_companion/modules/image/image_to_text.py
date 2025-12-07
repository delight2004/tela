import base64
import logging
import os
from typing import Union, Optional

from ai_companion.core.exceptions import ImageToTextError
from ai_companion.settings import settings
from groq import Groq


class ImageToText:
    """A class to handle image-to-text conversion using Groq's vision capabilties"""

    REQUIRED_ENV_VARS=["GROQ_API_KEY"]

    def __init__(self):
        self._validate_env_vars()
        self._client = Optional[Groq] = None
        self._logger = logging.getLogger(__name__)

    def _validate_env_vars(self) -> None:
        """Validate that all the required environment variables are set"""
        missing_vars = [var for var in self.REQUIRED_ENV_VARS if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {", ".join(missing_vars)}")
        
    @property
    def client(self) -> Groq:
        """Get or create Groq client instance using the singleton pattern"""
        if self._client is None:
            self._client = Groq(api_key=settings.GROQ_API_KEY)
        return self._client
    

    async def analyze_image(self, image_data: Union[str, bytes], prompt: str="") -> str:
        """Analyzes an image using Groq's vision capabilites.
        
        Args:
            image_data: Either a file path(str) or binary image data(bytes)
            prompt: Optional prompt to gude image analysis
        
        Returns:
            str: Description or analysis of the image

        Raises:
            ValueError: If the image data is empty or invalid
            ImageToTextError: If the image analysis fails
        """

        try:
            # handle file path
            if isinstance(image_data, str):
                if not os.path.exists(path=image_data):
                    raise ValueError(f"Image file not found: {image_data}")
                with open(image_data, "rb") as f:
                    image_bytes=f.read()
            
            else:
                image_bytes = image_data
            
            if not image_bytes:
                raise ValueError("Image data cannot be empty")
            
            base64_image = base64.b64encode(image_bytes).decode("utf-8")

            if not prompt:
                prompt = "Please describe what you see in this image in detail."
            
            # create the messages for the Vision API
            messages = [
                {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                ]
                }
            ]

            # make the API call
            response = self.client.chat.completions.create(
                messages=messages,
                model=settings.ITT_MODEL_NAME,
                max_tokens=1000,
            )

            if not response.choices:
                raise ImageToTextError("No response received from the vision model.")
            
            description = response.choices[0].message.content
            self._logger.info(f"Generated image description: {description}")

            return description
        
        except Exception as e:
            raise ImageToTextError(f"Failed to analyze image: {str(e)}") from e