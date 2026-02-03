import os
import cohere

class CohereService:
    def __init__(self):
        api_key = os.getenv("COHERE_API_KEY")
        self.client = cohere.Client(api_key) if api_key else None
        self.model = "command"  # Cohere's latest model
    
    async def get_drug_information(self, query: str) -> str:
        """
        Get drug information from Cohere
        """
        if not self.client:
            return "AI assistant is not configured. Please add your COHERE_API_KEY to use this feature."
        
        try:
            response = self.client.chat(
                model=self.model,
                message=query,
                preamble="""You are an expert pharmacist assistant. Provide accurate, helpful information about:
- Drug information, usage, and dosages
- Drug interactions and contraindications
- Side effects and warnings
- Medical conditions and treatments
- Medication safety and storage
Always be clear, professional, and remind users to consult healthcare professionals for personalized advice.""",
                max_tokens=1024
            )
            
            return response.text
        except Exception as e:
            return f"I'm sorry, I encountered an error: {str(e)}"