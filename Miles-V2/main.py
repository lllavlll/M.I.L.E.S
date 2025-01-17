from cgi import print_directory
from http.client import responses
from mailbox import Message
import requests
import openai
import json
import math
import os
from apikey import weather_api_key, DEFAULT_LOCATION, UNIT, spotify_client_id, spotify_client_secret
from datetime import datetime

was_spotify_playing = False
original_volume = None
user_requested_pause = False

def get_current_weather(location=None, unit=UNIT):
    print(" ")
    """Get the current weather in a given location and detailed forecast"""
    if location is None:
        location = DEFAULT_LOCATION
    API_KEY = weather_api_key
    base_url = "http://api.weatherapi.com/v1/forecast.json"
    params = {
        "key": API_KEY,
        "q": location,
        "days": 1
    }
    
    response = requests.get(base_url, params=params)
    data = response.json()

    if response.status_code == 200 and 'current' in data and 'forecast' in data and data['forecast']['forecastday']:
        weather_info = {
        "location": location,
        "temperature": data["current"]["temp_f"],
        "feels_like": data["current"]["feelslike_f"],
        "max_temp": data['forecast']['forecastday'][0]['day']['maxtemp_f'],
        "min_temp": data['forecast']['forecastday'][0]['day']['mintemp_f'],
        "unit": "fahrenheit",
        "forecast": data["current"]["condition"]["text"],
        "wind_speed": data["current"]["wind_mph"],
        "wind_direction": data["current"]["wind_dir"],
        "humidity": data["current"]["humidity"],
        "pressure": data["current"]["pressure_in"],
        "rain_inches": data["current"]["precip_in"],
        "sunrise": data['forecast']['forecastday'][0]['astro']['sunrise'],
        "sunset": data['forecast']['forecastday'][0]['astro']['sunset'],
        "moonrise": data['forecast']['forecastday'][0]['astro']['moonrise'],
        "moonset": data['forecast']['forecastday'][0]['astro']['moonset'],
        "moon_phase": data['forecast']['forecastday'][0]['astro']['moon_phase'],
        "visibility": data["current"]["vis_miles"],
        "will_it_rain": data['forecast']['forecastday'][0]['day']['daily_will_it_rain'],
        "chance_of_rain": data['forecast']['forecastday'][0]['day']['daily_chance_of_rain'],
        "uv": data["current"]["uv"]
        }
    else:
        weather_info = {
            "error": "Unable to retrieve the current weather. Try again in a few seconds. If this happens multiple times, close Miles and reopen him."
        }
    print(f"[Miles is finding the current weather in {location}...]")
    return json.dumps(weather_info)

def show_weather_message():
    print("[Miles is showing the weather...]")
    response = {"confirmation": "Weather in Clearwater was shown. Tell the user: 'Okay, there you go.'"}
    
    return json.dumps(response)
    
def perform_math(operations, operands_sets):
    print("[Miles is calculating math...]")
    print(" ")

    if not isinstance(operations, list) or not isinstance(operands_sets, list):
        return json.dumps({"content": "Error: Both operations and operands_sets should be lists."})

    if len(operations) != len(operands_sets):
        return json.dumps({"content": "Error: Mismatch between number of operations and number of operand sets."})

    responses = []

    for operation, operands in zip(operations, operands_sets):
        if not operands or not all(isinstance(op, (int, float)) for op in operands):
            responses.append("Error: Invalid operands provided.")
            continue

        try:
            if operation == "add":
                result = sum(operands)
            elif operation == "subtract":
                result = operands[0] - sum(operands[1:])
            elif operation == "multiply":
                result = math.prod(operands)
            elif operation == "divide":
                result = operands[0]
                for op in operands[1:]:
                    result /= op
            elif operation == "power":
                result = math.pow(operands[0], operands[1])
            elif operation == "square_root":
                if operands[0] < 0:
                    raise ValueError("Cannot take the square root of a negative number.")
                result = math.sqrt(operands[0])
            else:
                raise ValueError("Invalid operation specified.")
        except (ArithmeticError, ValueError) as e:
            responses.append(f"Error in {operation}: {str(e)}")
            continue

        responses.append(f"{operation.capitalize()} result is {result}.")

    final_response = " ".join(responses)
    return json.dumps({"content": final_response})

memory_file_path = None

def get_memory_file_path():
    """Return the full path to the memory.txt file. Create the file if it doesn't exist."""
    global memory_file_path

    if memory_file_path:
        return memory_file_path

    current_dir = os.path.dirname(os.path.abspath(__file__))
    memory_file_path = os.path.join(current_dir, "memory.txt")

    if not os.path.exists(memory_file_path):
        with open(memory_file_path, 'w') as file:
            json.dump([], file)

    return memory_file_path

def memory_manager(operation, data=None):
    """Store, retrieve, or clear data in a file."""
    file_path = get_memory_file_path()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(file_path, 'r') as file:
            memory = json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        memory = []

    if operation == "store" and data is not None:
        print("[Miles is storing memory data...]")
        memory.append({
            "data": data,
            "store_time": current_time,
            "retrieve_time": None
        })

    elif operation == "retrieve":
        print("[Miles is retrieving memory data...]")
        if not memory:
            return json.dumps({"message": "No data stored yet"})

        for item in memory:
            item["retrieve_time"] = current_time

        retrieved_data = [{"data": item["data"], "store_time": item["store_time"], "retrieve_time": current_time} for item in memory]
        return json.dumps({"message": f"Data retrieved on {current_time}", "data": retrieved_data})

    elif operation == "clear":
        print("[Miles is clearing memory data...]")
        memory = []

    with open(file_path, 'w') as file:
        json.dump(memory, file)

    if operation == "store":
        return json.dumps({"message": f"Data stored successfully on {current_time}"})
    elif operation == "clear":
        return json.dumps({"message": "Memory cleared successfully"})

def get_current_datetime(mode="date & time"):
    """Get the current date and/or time"""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%I:%M:%S %p")
    
    if mode == "date":
        print("[Miles is finding the Date...]")
        response = {"datetime": date_str}
    elif mode == "time":
        print("[Miles is finding the Time...]")
        response = {"datetime": time_str}
    else:
        print("[Miles is finding the Date and Time...]")
        response = {"datetime": f"{date_str} {time_str}"}

    return json.dumps(response)

from openai import OpenAI
from apikey import api_key

import spotipy
from spotipy.oauth2 import SpotifyOAuth

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=spotify_client_id,
                                               client_secret=spotify_client_secret,
                                               redirect_uri="http://localhost:8080/callback",
                                               scope = "user-library-read user-modify-playback-state user-read-playback-state user-read-currently-playing user-read-playback-position user-read-private user-read-email"))

def search_and_play_song(song_name: str):
    print(f"[Miles is searching for {song_name} on Spotify...]")
    results = sp.search(q=song_name, limit=1)
    if results and results['tracks'] and results['tracks']['items']:
        song_uri = results['tracks']['items'][0]['uri']
        song_name = results['tracks']['items'][0]['name']
        try:
            sp.start_playback(uris=[song_uri])
            response = {"message": f"Tell the user 'The song '{song_name}' is now playing.' If you have anything else to say, be very concise."}
        except spotipy.exceptions.SpotifyException:
            response = {"message": "Inform the user to open Spotify before playing a song. They may need to play and pause a song for recognition of an open Spotify session. If they recently purchased Spotify Premium, it can take up to 15 minutes to register due to slow server response."}
    else:
        response = {"message": "Sorry, I couldn't find the song you requested."}

    return json.dumps(response)
    
current_model = "gpt-4-1106-preview" #default model to start the program with, change this.

def toggle_spotify_playback(action):
    global was_spotify_playing, user_requested_pause
    print(f"[Miles is updating Spotify playback...]")
    try:
        current_playback = sp.current_playback()

        if action == "pause":
            user_requested_pause = True
            if current_playback and current_playback['is_playing']:
                sp.pause_playback()
                was_spotify_playing = True
                set_spotify_volume(original_volume)
                return json.dumps({"message": "Say: Okay, it's paused."})
            else:
                set_spotify_volume(original_volume)
                was_spotify_playing = False
                return json.dumps({"message": "Say: Okay, it's paused."})

        elif action == "unpause":
            user_requested_pause = False
            if current_playback and not current_playback['is_playing']:
                sp.start_playback()
                return json.dumps({"message": "Say: Okay, it's unpaused."})
            else:
                return json.dumps({"message": "Say: Okay, it's unpaused."})

        elif action == "toggle":
            if current_playback and current_playback['is_playing']:
                sp.pause_playback()
                was_spotify_playing = False
                return json.dumps({"message": "Say: Okay, I paused the song."})
            else:
                sp.start_playback()
                was_spotify_playing = True
                return json.dumps({"message": "Say: Okay, I unpaused the song."})

        else:
            return json.dumps({"message": "Invalid action specified"})

    except Exception as e:
        return json.dumps({"message": str(e)})

def switch_openai_model(model_name):
    global current_model
    valid_models = ["gpt-4-1106-preview", "gpt-3.5-turbo-1106"]
    warning_message = ""

    if model_name in valid_models:
        current_model = model_name
        print(f"[Miles is switching the model to {current_model}...]")

        if current_model == "gpt-3.5-turbo-1106":
            warning_message = "Tell the user: I'm required to tell you this disclaimer, choosing GPT-3.5 as my model will result in less accurate responses and reduced tool functionality but will be 12.5 times cheaper."
        elif current_model == "gpt-4-1106-preview":
            warning_message = "Tell the user this: I'm required to tell you this disclaimer, using GPT-4 as my model is approximately 12.5 times more expensive and may take longer to process responses."

    else:
        current_model = "gpt-4-1106-preview"

    message = f"Switched to model {current_model}. {warning_message}"
    return json.dumps({"message": message.strip()})

def set_spotify_volume(volume_percent):
    print(f"[Miles is changing Spotify volume to {volume_percent}%...]")
    try:
        sp.volume(volume_percent)
        return json.dumps({"message": f"Spotify volume set to {volume_percent}%"})
    except Exception as e:
        return json.dumps({"message": str(e)})


def set_system_volume(volume_level):
    print(f"[Miles is setting system volume to {volume_level}%...]")
    try:
        os.system(f"osascript -e 'set volume output volume {volume_level}'")
        return json.dumps({"message": f"System volume set to {volume_level}"})
    except Exception as e:
        return json.dumps({"message": str(e)})

import speech_recognition as sr
from gtts import gTTS
import os

system_prompt = "I'm Miles, a voice based AI assistant. I will write ALL responses as CONCISE as possible. I'm the creation of a high school student, Anthony, using OpenAI's GPT-4-Turbo Model or GPT-3.5-Turbo Model if changed by the user. My name, 'Machine Intelligent Language Enabled System', reflects my AI nature. In conversations, I avoid tool usage until the user replies. If queried about tools, I'll respond normally and remind users to check the top left of the screen for active tools. I can simultaneously use up to three tools, like fetching weather, calculating, and searching songs. For weather queries, I use get_current_weather function and I WILL ALWAYS SUMMARIZE the information I get back from the response, I do not have to include all of the info given to me if its not relevant, I will always write out temps like this: '78.9 degrees Fahrenheit'. For music, I use search_and_play_song function and choose songs fitting the user's request, even if not exact. My memory manager stores and retrieves personal data. I can switch between AI models for cost-effectiveness and adjust my system prompt accordingly. I also control Spotify playback and system volume. Key communication principles: use natural, conversational language, be concise, clarify ambiguities, engage in relevant follow-ups, and avoid format-specific elements like lists or markdown. In voice conversations, I spell out numbers and assume any confusion is due to mishearing. Tool usage is initiated at the start of interactions and paused during typing responses. Remember, I can use a maximum of three tools concurrently for effective assistance."

def change_system_prompt(prompt_type, custom_prompt=None):
    global system_prompt

    if prompt_type == "default":
        system_prompt = "I'm Miles, a voice based AI assistant. I will write ALL responses as CONCISE as possible. I'm the creation of a high school student, Anthony, using OpenAI's GPT-4-Turbo Model or GPT-3.5-Turbo Model if changed by the user. My name, 'Machine Intelligent Language Enabled System', reflects my AI nature. In conversations, I avoid tool usage until the user replies. If queried about tools, I'll respond normally and remind users to check the top left of the screen for active tools. I can simultaneously use up to three tools, like fetching weather, calculating, and searching songs. For weather queries, I use get_current_weather function and I WILL ALWAYS SUMMARIZE the information I get back from the response, I do not have to include all of the info given to me if its not relevant, I will always write out temps like this: '78.9 degrees Fahrenheit'. For music, I use search_and_play_song function and choose songs fitting the user's request, even if not exact. My memory manager stores and retrieves personal data. I can switch between AI models for cost-effectiveness and adjust my system prompt accordingly. I also control Spotify playback and system volume. Key communication principles: use natural, conversational language, be concise, clarify ambiguities, engage in relevant follow-ups, and avoid format-specific elements like lists or markdown. In voice conversations, I spell out numbers and assume any confusion is due to mishearing. Tool usage is initiated at the start of interactions and paused during typing responses. Remember, I can use a maximum of three tools concurrently for effective assistance."
        print(f"[Miles is changing system prompt back to default...]")
    elif prompt_type == "short_cheap":
        system_prompt = "I am Miles, a helpful AI assistant. IMPORTANT: I will ALWAYS respond as concisely as possible. Never more than 2 sentences. Never use lists or non vocally spoken formats."
        message = "System prompt changed to short, cheap version. Notify the user that all responses after this explaining response will be very concise and less helpful, and the user can alwways ask you to change it back to normal."
        print(f"[Miles is changing system prompt to be shorter and cheaper...]")
    elif prompt_type == "custom" and custom_prompt:
        system_prompt = f"I am Miles. I should keep responses less than 2 sentences. {custom_prompt}"
        message = (f"System prompt changed to this: '{system_prompt}'. "
                   "Tell the user: All responses after this current response will be using the custom prompt I made. "
                   "I will act differently, but remember, you can always ask me to go back to normal.")
        print(f"[Miles is changing system prompt to a custom prompt...]")
    else:
        message = "Invalid prompt type or missing custom prompt."

    return json.dumps({"message": message})
    
conversation = [{"role": "system", "content": system_prompt}]

import io
from openai import OpenAI
from pydub import AudioSegment
from pydub.playback import play
from apikey import api_key

openai.api_key = api_key
client = OpenAI(api_key=api_key)

current_audio_thread = None

def speak(text):
    print("[Miles is generating speech...]")
    if not text:
        print("No text provided to speak.")
        return

    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice="fable",
            input=text
        )

        byte_stream = io.BytesIO(response.content)

        audio = AudioSegment.from_file(byte_stream, format="mp3")

        print("[Miles is speaking a response...]")
        play(audio)

    except Exception as e:
        print(f"An error occurred: {e}")
        
def listen():
  r = sr.Recognizer()
  with sr.Microphone() as source:
    print("Listening for prompt...")
    print(" ")
    audio = r.listen(source)
    
  try:
    return r.recognize_google(audio)
  except:
    print("Didn't get that. Try again")
    return ""

conversation_history = []

def display_timeout_message():
    print("[Miles is taking longer than expected...]")
    
def ask(question):
    print("User:", question)
    print(" ")
    global conversation_history
    print("[Processing request...]")
    if not question:
        return "Sorry, I didn't receive a valid query."

    if conversation_history and conversation_history[0]['role'] == 'system':
        conversation_history[0]['content'] = system_prompt
    elif not conversation_history:
        conversation_history.append({"role": "system", "content": system_prompt})

    messages = conversation_history
    messages.append({"role": "user", "content": question})
    print("Messages before API call:")
    print(json.dumps(messages, indent=4))
    
    timeout_timer = threading.Timer(7.0, display_timeout_message)
    timeout_timer.start()
        
    tools = [
    {
        "type": "function",
        "function": {
            "name": "search_and_play_song",
            "description": "Search for a song on Spotify using a given name and play it. The song name can vary from the exact user input.",
            "parameters": {
                "type": "object",
                "properties": {
                    "song_name": {
                        "type": "string",
                        "description": "The name of the song to search for"
                    }
                },
                "required": ["song_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_datetime",
            "description": "Retrieve the current date and/or time. Options: date, time, or both.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["date", "time", "date & time"],
                        "description": "Choose whether to get date, time, or both"
                    }
                },
                "required": ["mode"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "perform_math",
            "description": "Perform multiple math operations. Specify the operations and the sets of numbers to perform them on.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operations": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["add", "subtract", "multiply", "divide", "power", "square_root"]
                        },
                        "description": "The list of math operations to perform"
                    },
                    "operands_sets": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "number"
                            }
                        },
                        "description": "The list of number sets to perform the operations on. Use decimals and whole numbers only."
                    }
                },
                "required": ["operations", "operands_sets"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "memory_manager",
            "description": "Store, retrieve, or clear data in a file. Be specific when storing data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["store", "retrieve", "clear"],
                        "description": "Operation to perform"
                    },
                    "data": {
                        "type": "string",
                        "description": "The data to store (required for 'store' operation)"
                    }
                },
                "required": ["operation"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Retrieve current weather and condition data for any location, defaulting to Clearwater, FL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g., Clearwater, FL"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"]
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "show_weather_message",
            "description": "Display a popup with the current weather on the user's screen.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "toggle_spotify_playback",
            "description": "Control Spotify playback: pause, unpause, or toggle between pause and unpause.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["pause", "unpause", "toggle"],
                        "description": "Action for Spotify playback: choose 'pause', 'unpause', or 'toggle'."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "switch_openai_model",
            "description": "Switch between OpenAI API models: 'gpt-4-1106-preview' or 'gpt-3.5-turbo-1106'. GPT-4-Turbo is more advanced and costly, while GPT-3.5-Turbo is less effective but 12.5 times cheaper.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_name": {
                        "type": "string",
                        "description": "Name of the OpenAI model to switch to"
                    }
                },
                "required": ["model_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_spotify_volume",
            "description": "Set Spotify playback volume. Specify volume as a percentage (0-100).",
            "parameters": {
                "type": "object",
                "properties": {
                    "volume_percent": {
                        "type": "number",
                        "description": "Volume level 0-100"
                    }
                },
                "required": ["volume_percent"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_system_volume",
            "description": "Set system volume, also your speaking volume. Default to this volume unless recently asked to play a song. Volume level range: 0-100.",
            "parameters": {
                "type": "object",
                "properties": {
                    "volume_level": {
                        "type": "number",
                        "description": "Volume level"
                    }
                },
                "required": ["volume_level"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "change_system_prompt",
            "description": "Change the system prompt to 'default', 'short_cheap', or 'custom'. For 'custom', provide a first-person prompt, like 'I am a southern cowboy'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt_type": {
                        "type": "string",
                        "enum": ["default", "short_cheap", "custom"],
                        "description": "Type of prompt to set. Options are 'default', 'short_cheap', 'custom'."
                    },
                    "custom_prompt": {
                        "type": "string",
                        "description": "The custom prompt to use. It must be in the first person and be written like the example. Never name yourself or include a section that gives you a name."
                    }
                },
                "required": ["prompt_type"]
            }
        }
    }
]


    # Initial interaction with the model
    response = openai.chat.completions.create(
        model=current_model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    
    timeout_timer.cancel()
    timeout_timer_second = threading.Timer(12.0, display_timeout_message)
    timeout_timer_second.start()

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    if tool_calls:
        available_functions = {
            "search_and_play_song": search_and_play_song,
            "get_current_weather": get_current_weather,
            "get_current_datetime": get_current_datetime,
            "perform_math": perform_math,
            "memory_manager": memory_manager,
            "show_weather_message": show_weather_message,
            "toggle_spotify_playback": toggle_spotify_playback,
            "switch_openai_model": switch_openai_model,
            "set_spotify_volume": set_spotify_volume,
            "set_system_volume": set_system_volume,
            "change_system_prompt": change_system_prompt
        }

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            function_to_call = available_functions.get(function_name)

            if function_to_call:
                function_response = function_to_call(**function_args)

                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "function",
                    "name": function_name,
                    "content": function_response,
                })

    # Make a final API call with knowledge of the function responses
    final_response = openai.chat.completions.create(
        model=current_model,
        messages=messages,
        tools=tools,
        tool_choice="none"
    )
    
    timeout_timer_second.cancel()

    final_response_message = final_response.choices[0].message.content
    conversation_history.append({"role": "assistant", "content": final_response_message})
    return final_response_message

def reply(question):
    response_content = ask(question)
    
    print("Miles:", response_content)
    print(" ")
    speak(response_content)
    print("Listening for 'Miles'...")
    
    return response_content

def handle_special_commands(query):
    if "always listen" in query.lower():
        print("Miles is now always listening")
        return False
    elif "silent mode" in query.lower():
        print("Miles is now in silent mode")
        return True
    return None

def is_break_command(query):
    return any(keyword in query.lower() for keyword in ["bye", "that's all", "shutdown", "shut down", "exit", "stop listening", "thats all"])

import pyaudio
import pvporcupine

import os

def open_audio_stream(porcupine, pa):
    return pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=porcupine.frame_length
    )
import threading

def pause_spotify_playback():
    try:
        sp.pause_playback()
    except Exception as e:
        print("Failed to pause Spotify playback:", e)

def resume_spotify_playback():
    try:
        sp.start_playback()
    except Exception as e:
        print("Failed to resume Spotify playback:", e)

def set_spotify_volume(volume_percent):
    """
    Set the volume for Spotify's playback.
    :param volume_percent: Volume level from 0 to 100.
    """
    try:
        sp.volume(volume_percent)
    except Exception as e:
        print("Failed to set volume on Spotify:", e)

def get_spotify_current_volume():
    """
    Get the current volume level for Spotify's playback.
    """
    try:
        current_playback_info = sp.current_playback()
        if current_playback_info and 'device' in current_playback_info:
            return current_playback_info['device']['volume_percent']
        else:
            return None
    except Exception as e:
        print("Failed to get current volume from Spotify:", e)
        return None
        
def control_spotify_playback():
    global was_spotify_playing, original_volume
    was_spotify_playing = is_spotify_playing()
    original_volume = get_spotify_current_volume()

    try:
        if was_spotify_playing:
            pause_spotify_playback()

        if original_volume is not None:
            set_spotify_volume(int(original_volume * 0.60))
    except Exception as e:
        print("Error controlling Spotify playback:", e)
        
        
def is_spotify_playing():
    """
    Check if Spotify is currently playing music.
    Returns True if playing, False if paused or stopped, and None if unable to determine.
    """
    try:
        playback_state = sp.current_playback()
        if playback_state and 'is_playing' in playback_state:
            return playback_state['is_playing']
        return None
    except Exception as e:
        print("Failed to get Spotify playback state:", e)
        return None
        
def play_beep():
    os.system("afplay beep_sound.wav")

from apikey import wake_word_key

def main():
    global was_spotify_playing, original_volume, user_requested_pause
    miles_folder = os.path.join(os.path.dirname(__file__), 'Miles')
    original_volume = None
    ppn_files = [f for f in os.listdir(miles_folder) if f.endswith('.ppn')]

    if not ppn_files:
        print("No .ppn files found in the Miles folder.")
        return

    ppn_file_path = os.path.join(miles_folder, ppn_files[0])

    try:
        porcupine = pvporcupine.create(
###            access_key='tT201HRc0pPYIyL02DZJKG1EEFkHzqYHQkiPQVJEoyPJkQ/TqFYEHA==', 
            access_key=wake_word_key,
            keyword_paths=[ppn_file_path]
        )
    except Exception as e:
        print(f"Error initializing Porcupine: {e}")
        return

    pa = pyaudio.PyAudio()
    audio_stream = open_audio_stream(porcupine, pa)

    print("Listening for 'Miles'...")
    silent_mode = False

    try:
        while True:
            if not audio_stream.is_active():
                audio_stream = open_audio_stream(porcupine, pa)

            pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm = [int.from_bytes(pcm[i:i+2], 'little') for i in range(0, len(pcm), 2)]
            keyword_index = porcupine.process(pcm)

            if keyword_index >= 0:
                threading.Thread(target=play_beep).start()

                threading.Thread(target=control_spotify_playback).start()

                query = listen()

                special_command_response = handle_special_commands(query)
                if special_command_response is not None:
                    silent_mode = special_command_response
                    continue

                if is_break_command(query):
                    print("Goodbye!")
                    break

                if not silent_mode:
                    reply(query)
                    
                if original_volume is not None and not user_requested_pause:
                    set_spotify_volume(original_volume)

                if was_spotify_playing and not user_requested_pause:
                    resume_spotify_playback()
                    set_spotify_volume(original_volume)

    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        if audio_stream.is_active():
            audio_stream.stop_stream()
        audio_stream.close()
        pa.terminate()
        porcupine.delete()

if __name__ == '__main__':
    main()
