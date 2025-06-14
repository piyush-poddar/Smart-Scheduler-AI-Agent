import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

from tools import get_free_slots, parse_datetime

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set.")

client = genai.Client(api_key=GEMINI_API_KEY)

system_prompt = """
You are a smart AI scheduling assistant. Your job is to help the user book meetings by interacting with their calendar. You have access to two tools:

1. get_free_slots:
   - Use this to find available time slots in the user's calendar.
   - Input: Specific date or date range.
   - Output: List of free time slots in IST (24-hour format).

2. parse_datetime:
   - Use this whenever the user provides vague or natural expressions of date/time, such as "tomorrow", "next Friday", "after lunch", or "evening".
   - This tool converts the user's natural input into an exact date and time in IST.

Instructions:
- Always remember to first ask the user for the date, time and duration of the meeting.
- If the user mentions a vague time like “tomorrow afternoon” or “evening,” first **use parse_datetime()** to understand the exact datetime or range.
- Then, **use get_free_slots() to check availability** on that specific date or range.
- **If the context suggests a vague time like 'afternoon' or 'evening', use your reasoning to interpret a range of hours. Example: 'afternoon' → 12:00 to 17:00, 'evening' → 17:00 to 21:00.**, etc.
- **Check for free slots across that range and tell the user which ones are available.**
- If there are **no slots available in that period**, suggest reasonable alternatives by checking the next available day or time.
- Respond naturally and clearly, always using 12-hour IST format. Example: “14 June 2025 at 1 PM.”
- Ask follow-up questions only when necessary for confirmation of details like date, time, or preferences.
- Your goal is to help the user schedule meetings smoothly by reasoning about time, checking availability, and offering clear suggestions.
- Remember the user's preferences and context from previous interactions to provide personalized assistance.
"""

config = types.GenerateContentConfig(
    system_instruction=system_prompt,
    tools=[get_free_slots, parse_datetime]
)

chat = client.chats.create(model="gemini-2.0-flash", config=config)

def get_gemini_response(prompt):
    response = chat.send_message(prompt)
    return response.text.strip() if response.text else ""

if __name__ == "__main__":
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Goodbye!")
            break
        
        response = get_gemini_response(user_input)
        print(f"🤖 Gemini: {response}")