import openai
import logging
from datetime import datetime
import os
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class AzureOpenAIChatbot:
    def __init__(self, endpoint: str, api_key: str, deployed_model: str, api_version: str):
        """Initialize the Azure OpenAI chatbot"""
        self.client = openai.AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version
        )
        # self.client = openai.OpenAI(api_key=api_key)
        self.deployed_model = deployed_model
        self.conversation_history: List[Dict[str, str]] = []
        self.system_prompt = "You are a helpful travel assistant. Provide friendly, informative advice about travel destinations, planning, and tips."

        # Setup logging
        self.setup_logging()

    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('chatbot.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def moderate_content(self, text: str) -> bool:
        """Check if content is appropriate using Azure OpenAI content moderation"""
        try:
            # Send request (Azure OpenAI's content moderation)
            response = self.client.moderations.create(input=text)

            # Check if any category is flagged
            results = response.results[0]
            if results.flagged:
                flagged_categories = [
                    category for category, flagged in results.categories.__dict__.items()
                    if flagged
                ]
                self.logger.warning(f"Content flagged for: {', '.join(flagged_categories)}")
                return False
            return True

        except Exception as e:
            # [Inference] If moderation fails, we'll allow the content but log the error
            self.logger.error(f"Content moderation failed: {e}")
            print("Content moderation unavailable, proceeding without filtering...")
            return True

    def get_ai_response(self, user_message: str) -> str:
        """Get response from Azure OpenAI model"""
        try:
            # Build messages with system prompt and conversation history
            messages = [{"role": "system", "content": self.system_prompt}]

            # Add conversation history (keep last 10 exchanges to manage token limits)
            recent_history = self.conversation_history[-20:]  # Last 10 exchanges (user + assistant)
            messages.extend(recent_history)

            # Add current user message
            messages.append({"role": "user", "content": user_message})

            # Send request (Chat Completion API)
            response = self.client.chat.completions.create(
                model=self.deployed_model,
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                top_p=0.95,
                frequency_penalty=0,
                presence_penalty=0
            )

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"Error getting AI response: {e}")
            return f"Sorry, I encountered an error: {str(e)}"

    def save_conversation(self, user_message: str, ai_response: str):
        """Save conversation to a text file only"""
        timestamp = datetime.now().isoformat()

        # Add to conversation history (if you use this elsewhere)
        self.conversation_history.extend([
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": ai_response}
        ])

        # Save to text file for easy reading
        try:
            with open("conversation_log.txt", "a", encoding='utf-8') as f:
                f.write(f"\n[{timestamp}]\n")
                f.write(f"User: {user_message}\n")
                f.write(f"Assistant: {ai_response}\n")
                f.write("-" * 50 + "\n")
        except Exception as e:
            self.logger.error(f"Error saving conversation to text file: {e}")

    def run_chatbot(self):
        """Main chatbot loop"""
        print()
        print("=" * 40)
        print("Azure OpenAI Travel Assistant")
        print("=" * 40)
        print()
        print("Hi! I'm your travel assistant. Ask me anything about travel!")
        print("Type 'exit' to quit, 'clear' to clear conversation history")
        print("-" * 40)

        while True:
            try:
                user_input = input("\n💬 You: ").strip()

                if user_input.lower() == 'exit':
                    print("\nThanks for chatting! Have a great trip!")
                    break

                if user_input.lower() == 'clear':
                    self.conversation_history = []
                    print("Conversation history cleared!")
                    continue

                if not user_input:
                    print("Please enter a message!")
                    continue

                # Content moderation
                if not self.moderate_content(user_input):
                    print("Sorry, your message contains inappropriate content. Please try again.")
                    continue

                print("\nThinking...")

                # Get AI response
                ai_response = self.get_ai_response(user_input)

                # Display response
                print(f"\nAssistant: {ai_response}")

                # Save conversation
                self.save_conversation(user_input, ai_response)

            except KeyboardInterrupt:
                print("\n\n Goodbye!")
                break
            except Exception as e:
                print(f"\nAn error occurred: {e}")
                self.logger.error(f"Unexpected error in main loop: {e}")


def main():
    """Main function to run the chatbot"""
    # Configuration - Azure OpenAI
    openai_endpoint: str = os.getenv("OPENAI_API_ENDPOINT")
    openai_api_key: str = os.getenv("OPENAI_API_KEY")
    openai_api_version: str = os.getenv("OPENAI_API_VERSION")
    openai_deployed_model: str = os.getenv("OPENAI_DEPLOYED_MODEL")

    try:
        chatbot = AzureOpenAIChatbot(
            endpoint=openai_endpoint,
            api_key=openai_api_key,
            deployed_model=openai_deployed_model,
            api_version=openai_api_version
        )
        chatbot.run_chatbot()

    except Exception as e:
        print(f"Failed to initialize chatbot: {e}")
        print("Please check your Azure OpenAI credentials and try again.")


if __name__ == "__main__":
    main()