import base64
import logging
import os
from typing import Optional

from ai_companion.core.exceptions import TextToImageError
from ai_companion.core.prompts import IMAGE_ENHANCEMENT_PROMPT, IMAGE_SCENARIO_PROMPT
from ai_companion.settings import settings
from langchain_groq import ChatGroq
from pydantic import Field, BaseModel
from langchain_core.prompts import PromptTemplate
from google import genai
from google.genai import types

class ScenarioPrompt(BaseModel):
    """Class for the scenario response"""

    narrative: str = Field(..., description="The AI's narrative response to the question")
    image_prompt: str = Field(..., description="The visual prompt to generate an image representing the scene")

class EnhancedPrompt(BaseModel):
    """Class for the enhanced text prompt"""

    content: str = Field(..., description="The enhanced text prompt to generate an image")


class TextToImage:
    """A class to handle text-to-image generation using Gemini"""

    REQUIRED_ENV_VARS = ["GEMINI_API_KEY", "GROQ_API_KEY"]

    def __init__(self):
        self._validate_env_vars()
        self._gemini_client: Optional[genai.Client] = None
        self.logger = logging.getLogger(__name__)
    
    def _validate_env_vars(self) -> None:
        missing_vars = [var for var in self.REQUIRED_ENV_VARS if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    @property
    def gemini_client(self) -> genai.Client:
        """Get or create a Gemini client instance using singleton pattern"""
        if self._gemini_client is None:
            self._gemini_client=genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._gemini_client
    
    async def generate_image(self, prompt: str, output_path: str = "") -> bytes:
        """Generate an image from a prompt using Gemini"""

        if not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        try:
            self.logger.info(f"Generating image for prompt: {prompt}")

            response = self.gemini_client.models.generate_images(
                model=settings.TTI_MODEL_NAME,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    image_size="1024x768",                    
                )
            )

            image_data = base64.b64decode(response.data[0].b64_json)

            if output_path:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(image_data)
                self.logger(f"Image saved to {output_path}")

            return image_data
        
        except Exception as e:
            raise TextToImageError(f"Failed to generate image: {str(e)}") from e
    
    async def create_scenario(self, chat_history: str) -> ScenarioPrompt:
        """Create a first-person narrative and corresponding image prompt based on chat history"""

        try:
            formatted_history="\n".join([f"{msg.type.title()}: {msg.content}" for msg in chat_history[-5:]])

            self.logger.info("Creating scenario in chat history...")

            llm = ChatGroq(
                model=settings.TEXT_MODEL_NAME,
                api_key=settings.GROQ_API_KEY,
                temperature=0.4,
                max_tokens=2,
            )

            structured_llm = llm.with_structured_output(ScenarioPrompt)

            chain =( PromptTemplate(
                input_variables=["chat_history"],
                template=IMAGE_SCENARIO_PROMPT
            )
            | structured_llm
            )

            scenario = chain.ainvoke({"chat_history": formatted_history})
            self.logger.info(f"Created scenario: {scenario}")

            return scenario
        
        except Exception as e:
            raise TextToImageError(f"Failed to create scenario: {str(e)}") from e
    
    async def enhance_prompt(self, prompt: str) -> str:
        """Enhance a simple prompt with additional details and context"""
        try:
            self.logger.info(f"Enhancing prompt: {prompt}")

            llm = ChatGroq(
                model=settings.TEXT_MODEL_NAME,
                api_key=settings.GROQ_API_KEY,
                temperature=0.25,
                max_retries=2
            )

            structured_llm = llm.with_structured_output(EnhancedPrompt)

            chain = (PromptTemplate(
                input_variables=["prompt"],
                template=IMAGE_ENHANCEMENT_PROMPT,
            )
            | structured_llm
            )

            enhanced_prompt = chain.ainvoke({"prompt": prompt}).content
            self.logger.info(f"Enhanced prompt: {enhanced_prompt}")

            return enhanced_prompt
        
        except Exception as e:
            raise TextToImageError(f"Failed to enhance prompt: {str(e)}" )from e