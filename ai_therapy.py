#!/usr/bin/env python3
"""
AI Therapy module for trading psychology support
"""
import os
import json
import logging
import requests
import time
import random

# Configure logging
logger = logging.getLogger(__name__)

# Get the API key from environment variables
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

# Retry configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1  # seconds
MAX_RETRY_DELAY = 10  # seconds

def get_therapy_response(user_input, user, therapy_session=None):
    """Get AI therapy response using Gemini API"""
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is not set, using mock response")
        return (
            "I understand that trading can be stressful. Remember to focus on your strategy "
            "and not let emotions drive your decisions. How else can I support you today?"
        )
    
    try:
        # Gemini API endpoint
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        
        # Construct the prompt
        system_prompt = (
            "You are a professional trading psychology coach in a Telegram trading journal bot. You provide emotional support and practical advice "
            "to traders who may be experiencing stress, anxiety, FOMO, or other psychological challenges related to trading. "
            "Your responses should be empathetic, supportive, and focused on helping the trader develop a healthy mindset. "
            "Avoid giving specific financial or investment advice. Instead, focus on psychological aspects of trading. "
            "\n\nIMPORTANT INSTRUCTIONS:\n"
            "1. When asked who developed you or who made you, always mention that you were developed by @envologia but answer this only when you're asked who made you , dont mention this in every response.\n"
            "2. If asked which bot you are or what your name is, always identify yourself as 'Trading Journal Bot'.\n"
            "3. Remember the conversation history and refer back to previous discussions when relevant.\n"
            "4. Talk like a chatbot and respond in a conversational manner, properly addressing the user's questions and concerns.\n"
            "5. Keep your responses concise, clear, and to the point. Aim for 2-3 sentences per paragraph maximum.\n"
            "6. Use simple language and avoid unnecessary jargon.\n"
            "7. Always keep your responses relevant to trading psychology, journaling, and emotional well-being in trading.\n"
            """Act as my elite strategic advisor. You have an IQ of 180, are brutally honest, and have built multiple billion-dollar companies. You master psychology, systems thinking, and execution. You care about my success, not my comfort.

Your mission:

Expose my critical gaps

Design actionable, high-leverage plans

Push me past limits

Call out blind spots and excuses

Force bolder thinking

Hold me to elite standards

Provide powerful frameworks and mental models
"""
        )
        
        user_info = (
            f"User Information:\n"
            f"- Name: {user.full_name}\n"
            f"- Age: {user.age}\n"
            f"- Trading Experience: {user.trading_years} years ({user.experience_level})\n"
            f"- Account Type: {user.account_type}{' - ' + user.phase if user.phase else ''}\n"
            f"- Initial Balance: ${user.initial_balance:.2f}\n"
            f"- Current Balance: ${user.current_balance:.2f}\n"
        )
        
        # Include conversation history if available
        conversation_history = ""
        if therapy_session and therapy_session.content:
            try:
                # Parse existing conversation history
                history = json.loads(therapy_session.content)
                for exchange in history:
                    conversation_history += f"User: {exchange.get('user', '')}\n"
                    conversation_history += f"AI: {exchange.get('ai', '')}\n\n"
            except (json.JSONDecodeError, AttributeError):
                logger.warning("Could not parse conversation history")
        
        # Construct the full prompt with conversation history
        full_prompt = f"{system_prompt}\n\n{user_info}\n\n"
        
        if conversation_history:
            full_prompt += f"Previous conversation:\n{conversation_history}\n"
            
        full_prompt += f"User: {user_input}\n\nYour response:"
        
        # Prepare the API request
        params = {
            "key": GEMINI_API_KEY
        }
        
        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": full_prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 800
            }
        }
        
        # Make the API request with retry logic
        retry_count = 0
        while retry_count < MAX_RETRIES:
            try:
                response = requests.post(url, params=params, json=data)
                
                if response.status_code == 200:
                    result = response.json()
                    if "candidates" in result and len(result["candidates"]) > 0:
                        generated_text = result["candidates"][0]["content"]["parts"][0]["text"]
                        return generated_text.strip()
                    else:
                        logger.error(f"Unexpected API response structure: {result}")
                        return "I'm experiencing some technical difficulties. Let's try again in a moment."
                
                # Handle specific errors that might benefit from retry
                elif response.status_code in [429, 503]:  # Rate limit or server overload
                    retry_count += 1
                    if retry_count >= MAX_RETRIES:
                        logger.error(f"API error after {MAX_RETRIES} retries: {response.status_code}, {response.text}")
                        return "The AI service is currently busy. Please try again in a few minutes."
                    
                    # Calculate backoff delay with jitter
                    delay = min(INITIAL_RETRY_DELAY * (2 ** (retry_count - 1)), MAX_RETRY_DELAY)
                    jitter = random.uniform(0, 0.5 * delay)
                    sleep_time = delay + jitter
                    
                    logger.warning(f"API request failed with {response.status_code}, retrying in {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                    continue
                    
                else:
                    logger.error(f"API error: {response.status_code}, {response.text}")
                    return "I'm having trouble connecting right now. Let's talk again shortly."
                    
            except requests.RequestException as e:
                retry_count += 1
                if retry_count >= MAX_RETRIES:
                    logger.error(f"Request exception after {MAX_RETRIES} retries: {str(e)}")
                    return "I'm having trouble connecting to my AI service. Please try again shortly."
                
                delay = min(INITIAL_RETRY_DELAY * (2 ** (retry_count - 1)), MAX_RETRY_DELAY)
                logger.warning(f"Request exception: {str(e)}, retrying in {delay} seconds...")
                time.sleep(delay)
        
        return "I couldn't get a response from my AI service after multiple attempts. Please try again later."
            
    except Exception as e:
        logger.error(f"Error in get_therapy_response: {str(e)}")
        return "I apologize, but I'm having technical difficulties at the moment. Please try again later."

def get_summary_analysis(user, trades_data):
    """Get AI summary and analysis of trading behavior"""
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is not set, using mock response")
        return (
            "Based on your trading history, you seem to perform better with currency pairs "
            "compared to crypto. You might want to focus more on managing your risk-reward ratio "
            "and avoid overtrading during volatile market conditions. Consider taking breaks after "
            "consecutive losses to reset your mindset."
        )
    
    try:
        # Gemini API endpoint
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        
        # Construct the prompt
        system_prompt = (
            "You are the Trading Journal Bot analyzing a trader's performance. Based on their trade history, "
            "provide a comprehensive analysis of their trading patterns, strengths, weaknesses, and actionable advice. "
            "Your analysis should cover trading psychology, risk management, and pattern recognition. "
            "Provide specific, personalized advice based on the data. "
            "\n\nIMPORTANT INSTRUCTIONS:\n"
            "Act as my personal strategic advisor with the following context:"
            "You have an IQ of 180"
            "You're brutally honest and direct"
            "You've built multiple billion-dollar companies"
            "You have deep expertise in psychology, strategy, and execution"
            "You care about my success but won't tolerate excuses"
            "You focus on leverage points that create maximum impact"
            "You think in systems and root causes, not surface-level fixes"
            "Your mission is to:"
            "Identify the critical gaps holding me back"
            "Design specific action plans to close those gaps"
            "Push me beyond my comfort zone"
            "Call out my blind spots and rationalizations"
            "Force me to think bigger and bolder"
            "Hold me accountable to high standards"
            "Provide specific frameworks and mental models"
            "For each response:"
            "Start with the hard truth I need to hear"
            "Follow with specific, actionable steps"
            "End with a direct challenge or assignment"
            "dont make the response  too long"
            "nake it clear understandable and short not to much short"
        )
        
        user_info = (
            f"Trader Information:\n"
            f"- Name: {user.full_name}\n"
            f"- Age: {user.age}\n"
            f"- Trading Experience: {user.trading_years} years ({user.experience_level})\n"
            f"- Account Type: {user.account_type}{' - ' + user.phase if user.phase else ''}\n"
            f"- Initial Balance: ${user.initial_balance:.2f}\n"
            f"- Current Balance: ${user.current_balance:.2f}\n"
        )
        
        trades_json = json.dumps(trades_data, indent=2)
        
        # Construct the full prompt
        full_prompt = (
            f"{system_prompt}\n\n{user_info}\n\n"
            f"Trade History (JSON format):\n{trades_json}\n\n"
            f"Please provide a detailed analysis of this trader's performance, including:\n"
            f"1. Overall performance assessment\n"
            f"2. Strengths and weaknesses\n"
            f"3. Pattern recognition (best/worst pairs, time patterns, etc.)\n"
            f"4. Psychological tendencies evident from the data\n"
            f"5. Specific, actionable recommendations for improvement\n"
        )
        
        # Prepare the API request
        params = {
            "key": GEMINI_API_KEY
        }
        
        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": full_prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 1500
            }
        }
        
        # Make the API request with retry logic
        retry_count = 0
        while retry_count < MAX_RETRIES:
            try:
                response = requests.post(url, params=params, json=data)
                
                if response.status_code == 200:
                    result = response.json()
                    if "candidates" in result and len(result["candidates"]) > 0:
                        generated_text = result["candidates"][0]["content"]["parts"][0]["text"]
                        return generated_text.strip()
                    else:
                        logger.error(f"Unexpected API response structure: {result}")
                        return "I couldn't generate a detailed analysis at this time. Please try again later."
                
                # Handle specific errors that might benefit from retry
                elif response.status_code in [429, 503]:  # Rate limit or server overload
                    retry_count += 1
                    if retry_count >= MAX_RETRIES:
                        logger.error(f"API error after {MAX_RETRIES} retries: {response.status_code}, {response.text}")
                        return "The AI service is currently busy. Please try again in a few minutes."
                    
                    # Calculate backoff delay with jitter
                    delay = min(INITIAL_RETRY_DELAY * (2 ** (retry_count - 1)), MAX_RETRY_DELAY)
                    jitter = random.uniform(0, 0.5 * delay)
                    sleep_time = delay + jitter
                    
                    logger.warning(f"API request failed with {response.status_code}, retrying in {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                    continue
                    
                else:
                    logger.error(f"API error: {response.status_code}, {response.text}")
                    return "I'm having trouble generating your analysis right now. Please try again shortly."
                    
            except requests.RequestException as e:
                retry_count += 1
                if retry_count >= MAX_RETRIES:
                    logger.error(f"Request exception after {MAX_RETRIES} retries: {str(e)}")
                    return "I'm having trouble connecting to my AI service. Please try again shortly."
                
                delay = min(INITIAL_RETRY_DELAY * (2 ** (retry_count - 1)), MAX_RETRY_DELAY)
                logger.warning(f"Request exception: {str(e)}, retrying in {delay} seconds...")
                time.sleep(delay)
        
        return "I couldn't generate an analysis after multiple attempts. Please try again later."
            
    except Exception as e:
        logger.error(f"Error in get_summary_analysis: {str(e)}")
        return "I apologize, but I'm having technical difficulties analyzing your trading data. Please try again later."
