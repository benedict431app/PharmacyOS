import os
from openai import OpenAI
import base64

class OpenAIService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key) if api_key else None
        # the newest OpenAI model is "gpt-5" which was released August 7, 2025. do not change this unless explicitly requested by the user
        self.model = "gpt-5"
    
    async def get_drug_information(self, query: str) -> str:
        """
        Get drug information from OpenAI
        """
        if not self.client:
            return "AI assistant is not configured. Please add your OPENAI_API_KEY to use this feature."
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert pharmacist assistant. Provide accurate, helpful information about:
- Drug information, usage, and dosages
- Drug interactions and contraindications
- Side effects and warnings
- Medical conditions and treatments
- Medication safety and storage
Always be clear, professional, and remind users to consult healthcare professionals for personalized advice."""
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                max_tokens=1024
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"I'm sorry, I encountered an error: {str(e)}"
    
    async def extract_text_from_image(self, image_path: str) -> str:
        """
        Extract text from prescription image using OpenAI Vision API
        """
        if not self.client:
            return "AI assistant is not configured. Please add your OPENAI_API_KEY to use this feature."
        
        try:
            # Read and encode image
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """Extract all text from this prescription image. Include:
- Patient name
- Doctor name and license
- Medications prescribed
- Dosages and instructions
- Date
Format the output clearly."""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2048
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"Error extracting text: {str(e)}"
