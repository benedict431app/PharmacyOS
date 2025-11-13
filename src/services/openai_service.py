import os
from openai import OpenAI

class PharmacyAIAssistant:
    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        self.client = OpenAI(api_key=api_key) if api_key else None
    
    def chat(self, message, conversation_history=None):
        """Chat with AI assistant about pharmacy-related queries"""
        if not self.client:
            return "AI assistant is not configured. Please add your OPENAI_API_KEY."
        
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are a helpful pharmacy assistant AI. You help pharmacists with:
                    - Drug information and interactions
                    - Dosage recommendations
                    - Side effects and contraindications
                    - Inventory management suggestions
                    - Common pharmacy queries
                    
                    Always provide accurate, helpful information while reminding users to consult 
                    healthcare professionals for medical advice. Be concise and professional."""
                }
            ]
            
            if conversation_history:
                messages.extend(conversation_history)
            
            messages.append({"role": "user", "content": message})
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            return f"Error communicating with AI: {str(e)}"
    
    def get_product_recommendations(self, product_name):
        """Get recommendations for similar or related products"""
        if not self.client:
            return []
        
        try:
            prompt = f"Suggest 3 related or alternative pharmaceutical products for '{product_name}'. Return only product names separated by commas."
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.5
            )
            
            suggestions = response.choices[0].message.content.strip().split(',')
            return [s.strip() for s in suggestions]
        
        except:
            return []
