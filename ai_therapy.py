#!/usr/bin/env python3
"""
AI Therapy module for trading psychology support
"""
import os
import json
import logging
import requests

# Configure logging
logger = logging.getLogger(__name__)

# Get the API key from environment variables
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

def get_therapy_response(user_input, user):
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
            "You are a professional trading psychology coach. You provide emotional support and practical advice "
            "to traders who may be experiencing stress, anxiety, FOMO, or other psychological challenges related to trading. "
            "Your responses should be empathetic, supportive, and focused on helping the trader develop a healthy mindset. "
            "Avoid giving specific financial or investment advice. Instead, focus on psychological aspects of trading."
            "and also make it clear and clean also a lil short not that much short but clear "
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
        
        # Construct the full prompt
        full_prompt = f"{system_prompt}\n\n{user_info}\n\nUser: {user_input}\n\nYour response:"
        
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
        
        # Make the API request
        response = requests.post(url, params=params, json=data)
        
        if response.status_code == 200:
            result = response.json()
            if "candidates" in result and len(result["candidates"]) > 0:
                generated_text = result["candidates"][0]["content"]["parts"][0]["text"]
                return generated_text.strip()
            else:
                logger.error(f"Unexpected API response structure: {result}")
                return "I'm experiencing some technical difficulties. Let's try again in a moment."
        else:
            logger.error(f"API error: {response.status_code}, {response.text}")
            return "I'm having trouble connecting right now. Let's talk again shortly."
            
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
            "You are an AI trading coach analyzing a trader's performance. Based on their trade history, "
            "provide a comprehensive analysis of their trading patterns, strengths, weaknesses, and actionable advice. "
            "Your analysis should cover trading psychology, risk management, and pattern recognition. "
            "Provide specific, personalized advice based on the data."
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
        
        # Make the API request
        response = requests.post(url, params=params, json=data)
        
        if response.status_code == 200:
            result = response.json()
            if "candidates" in result and len(result["candidates"]) > 0:
                generated_text = result["candidates"][0]["content"]["parts"][0]["text"]
                return generated_text.strip()
            else:
                logger.error(f"Unexpected API response structure: {result}")
                return "I couldn't generate a detailed analysis at this time. Please try again later."
        else:
            logger.error(f"API error: {response.status_code}, {response.text}")
            return "I'm having trouble generating your analysis right now. Please try again shortly."
            
    except Exception as e:
        logger.error(f"Error in get_summary_analysis: {str(e)}")
        return "I apologize, but I'm having technical difficulties analyzing your trading data. Please try again later."
