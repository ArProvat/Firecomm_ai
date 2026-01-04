
from langchain_core.messages import HumanMessage, AIMessage















async def generate_session_title(self, first_message: str) -> str:
        """Generate session title"""
        try:
            prompt = f"Generate a short, descriptive title (max 6 words) for: '{first_message}'. Return only the title."
            messages = [HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages)
            title = response.content.strip().strip('"').strip("'")
            return title[:100]
        except Exception as e:
            print(f"Error generating title: {e}")
            return first_message[:50] + "..." if len(first_message) > 50 else first_message