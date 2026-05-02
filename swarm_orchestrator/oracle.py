import os
import zmq
import time
import random
import logging
from google import genai
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [ORACLE] - %(message)s')

client = genai.Client()

NEWS_FEED = [
    "Tech Giant reports record-breaking Q3 earnings, shattering Wall Street estimates.",
    "Federal Reserve announces emergency rate cut of 100 bps.",
    "Major pipeline explodes, disrupting global oil supply significantly.",
    "Unemployment drops to historic lows, economy booming.",
    "CEO of major simulated company resigns amidst massive accounting scandal.",
    "Routine Tuesday: No major economic data released today."
]

# THE PRODUCTION FALLBACK MATRIX
# If the API fails, the system safely defaults to these scores.
FALLBACK_SCORES = {
    "Tech Giant reports record-breaking Q3 earnings, shattering Wall Street estimates.": 0.85,
    "Federal Reserve announces emergency rate cut of 100 bps.": 0.75,
    "Major pipeline explodes, disrupting global oil supply significantly.": -0.85,
    "Unemployment drops to historic lows, economy booming.": 0.70,
    "CEO of major simulated company resigns amidst massive accounting scandal.": -0.90,
    "Routine Tuesday: No major economic data released today.": 0.0
}

def score_news_sentiment(headline):
    prompt = f"""
    Analyze the financial sentiment of this headline. 
    Respond ONLY with a single float number between -1.0 (extreme bearish/panic) and 1.0 (extreme bullish/euphoria).
    Do not include any other text, words, or formatting.
    Headline: "{headline}"
    """
    try:
        # Changed back to the highly stable 1.5-flash model
        response = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=prompt,
        )
        score = float(response.text.strip())
        return max(-1.0, min(1.0, score))
    except Exception as e:
        logging.warning(f"API Rate Limit/Error Hit. Triggering Local Fallback Matrix.")
        return FALLBACK_SCORES.get(headline, 0.0)

def run_oracle():
    context = zmq.Context()
    host = os.getenv("ZMQ_HOST", "127.0.0.1")
    port = os.getenv("ZMQ_ORDER_PORT", "5555")

    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://{host}:{port}")
    
    logging.info("Gemini Macro Oracle Online. Monitoring news feeds...")

    try:
        while True:
            time.sleep(15) 
            
            headline = random.choice(NEWS_FEED)
            logging.info(f"BREAKING NEWS: {headline}")
            
            sentiment = score_news_sentiment(headline)
            logging.info(f"Sentiment Score: {sentiment}")

            if abs(sentiment) >= 0.7:
                side = "BUY" if sentiment > 0 else "SELL"
                qty = 100000 
                
                logging.warning(f"HIGH IMPACT DETECTED! Injecting Massive {side} Order for {qty} shares!")
                
                socket.send_json({
                    "agent_id": "GEMINI_ORACLE",
                    "action": side,
                    "qty": qty,
                    "type": "MARKET"
                })
                
                reply = socket.recv_json()
                logging.info(f"Oracle Execution: {reply}")
            else:
                logging.info("News impact minimal. No Oracle intervention required.")

    except KeyboardInterrupt:
        logging.info("Oracle shutting down.")
        socket.close()
        context.term()

if __name__ == "__main__":
    run_oracle()