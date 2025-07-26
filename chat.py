import requests
import time

# Model name to use with Ollama
MODEL = "llama3"

# URL for the Ollama chat API (Docker container mapped to localhost)
OLLAMA_URL = "http://localhost:11434/api/chat"

def ask_llama3(prompt):
    """
    Send a prompt to the Ollama API using the llama3 model.
    Returns the model response and elapsed time.
    """
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }

    start_time = time.time()
    response = requests.post(OLLAMA_URL, json=payload)
    elapsed_time = time.time() - start_time

    if response.status_code == 200:
        content = response.json()["message"]["content"]
        return content.strip(), elapsed_time
    else:
        return f"❌ Error {response.status_code}: {response.text}", elapsed_time

def chat():
    """
    Terminal chat loop for interacting with the llama3 model via Ollama.
    """
    print("🤠 Welcome to Charro Bot (powered by llama3 via Ollama)")
    print("Type 'exit' to quit.\n")

    while True:
        try:
            user_input = input("🧑 You: ").strip()
            if user_input.lower() in ["exit", "quit"]:
                print("👋 Goodbye!")
                break

            print("✅ Thinking...")
            reply, duration = ask_llama3(user_input)
            print(f"🤖 Charro Bot: {reply}")
            print(f"⏱ Response time: {duration:.2f} seconds\n")

        except KeyboardInterrupt:
            print("\n👋 Interrupted. Exiting...")
            break

if __name__ == "__main__":
    chat()
