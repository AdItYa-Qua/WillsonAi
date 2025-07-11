from Frontend.GUI2 import (
    GraphicalUserInterface,
    SetAssistantStatus,
    ShowTextToScreen,
    TempDirectoryPath,
    SetMicrophoneStatus,
    AnswerModifier,
    QueryModifier,
    GetMicrophoneStatus,
    GetAssistantStatus
)
from Backend.Model import FirstLayerDMM
from Backend.RealtimeSearchEngine import RealtimeSearchEngine
from Backend.Automation import Automation
from Backend.SpeechToText import SpeechRecognition
from Backend.Chatbot import ChatBot
from Backend.TextToSpeech import TextToSpeech
from dotenv import dotenv_values
from asyncio import run
from time import sleep
import subprocess
import threading
import json
import os

# Load environment variables
env_vars = dotenv_values(".env")
Username = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")
DefaultMessage = f"{Username} Hello {Assistantname}, How are you?\n{Assistantname}: Welcome {Username}. I am doing well. How may I help you?"
subprocesses = []
Functions = ["open", "close", "play", "system", "content", "google search", "youtube search"]

# Global thread control
stop_thread = threading.Event()
file_lock = threading.Lock()

def ShowDefaultChatIfNoChats():
    try:
        with open(r'Data\ChatLog.json', "r", encoding='utf-8') as file:
            if len(file.read()) < 5:
                with open(TempDirectoryPath('Database.data'), 'w', encoding='utf-8') as db_file:
                    db_file.write("")
                with open(TempDirectoryPath('Responses.data'), 'w', encoding='utf-8') as resp_file:
                    resp_file.write(DefaultMessage)
    except Exception as e:
        print(f"Error in ShowDefaultChatIfNoChats: {e}")

def ReadChatLogJson():
    try:
        with open(r'Data\ChatLog.json', 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error in ReadChatLogJson: {e}")
        return {}

def ChatLogIntegration():
    try:
        json_data = ReadChatLogJson()
        formatted_chatlog = ""
        for entry in json_data:
            if entry["role"] == "user":
                formatted_chatlog += f"User: {entry['content']}\n"
            elif entry["role"] == "assistant":
                formatted_chatlog += f"Assistant: {entry['content']}\n"

        formatted_chatlog = formatted_chatlog.replace("User", Username + " ")
        formatted_chatlog = formatted_chatlog.replace("Assistant", Assistantname + " ")

        with file_lock:
            with open(TempDirectoryPath('Database.data'), 'w', encoding='utf-8') as file:
                file.write(AnswerModifier(formatted_chatlog))
    except Exception as e:
        print(f"Error in ChatLogIntegration: {e}")

def ShowChatsOnGUI():
    try:
        with open(TempDirectoryPath('Database.data'), "r", encoding='utf-8') as file:
            Data = file.read().strip()  # Remove leading/trailing whitespace
            print(f"Data read from Database.data: {Data}")  # Debugging log

        result = ""  # Default value for result
        if len(Data) > 0:  # Check if the file is not empty
            lines = Data.split('\n')
            result = '\n'.join(lines)

        # Write the result to Responses.data
        with open(TempDirectoryPath('Responses.data'), "w", encoding='utf-8') as file:
            file.write(result)
        print("Data successfully written to Responses.data")
    except Exception as e:
        print(f"Error in ShowChatsOnGUI: {e}")


def InitialExecution():
    SetMicrophoneStatus("False")
    ShowTextToScreen("")
    ShowDefaultChatIfNoChats()
    ChatLogIntegration()
    ShowChatsOnGUI()

InitialExecution()

def MainExecution():
    try:
        TaskExecution = False
        ImageExecution = False
        ImageGenerationQuery = ""

        SetAssistantStatus("Listening...")
        Query = SpeechRecognition()
        ShowTextToScreen(f"{Username} : {Query}")
        SetAssistantStatus("Thinking...")
        Decision = FirstLayerDMM(Query)

        G = any([i for i in Decision if i.startswith("general")])
        R = any([i for i in Decision if i.startswith("realtime")])

        Mearged_query = " and ".join(
            [" ".join(i.split()[1:]) for i in Decision if i.startswith("general") or i.startswith("realtime")]
        )

        for queries in Decision:
            if "generate" in queries:
                ImageGenerationQuery = str(queries)
                ImageExecution = True

        for queries in Decision:
            if not TaskExecution and any(queries.startswith(func) for func in Functions):
                run(Automation(list(Decision)))
                TaskExecution = True

            if ImageExecution:
                with open(r"Frontend\Files\ImageGeneratoion.data", "w") as file:
                    file.write(f"{ImageGenerationQuery}, True")

                try:
                    p1 = subprocess.Popen(['python', r'Backend\ImageGeneration.py'],
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                          stdin=subprocess.PIPE, shell=False)
                    subprocesses.append(p1)
                except Exception as e:
                    print(f"Error starting ImageGeneration.py: {e}")

            if G and R or R:
                SetAssistantStatus("Searching...")
                Answer = RealtimeSearchEngine(QueryModifier(Mearged_query))
                ShowTextToScreen(f" {Assistantname} : {Answer}")
                SetAssistantStatus("Answering...")
                TextToSpeech(Answer)
                return True
            else:
                for Queries in Decision:
                    if "general" in Queries:
                        SetAssistantStatus("Thinking...")
                        QueryFinal = Queries.replace("general", "")
                        Answer = ChatBot(QueryModifier(QueryFinal))
                        ShowTextToScreen(f"{Assistantname} : {Answer}")
                        SetAssistantStatus("Answering...")
                        TextToSpeech(Answer)
                        return True

                    elif "realtime" in Queries:
                        SetAssistantStatus("Searching...")
                        QueryFinal = Queries.replace("realtime", "")
                        Answer = RealtimeSearchEngine(QueryModifier(QueryFinal))
                        ShowTextToScreen(f"{Assistantname} : {Answer}")
                        SetAssistantStatus("Answering...")
                        TextToSpeech(Answer)
                        return True

                    elif "exit" in Queries:
                        QueryFinal = "Okay, Bye!"
                        Answer = ChatBot(QueryModifier(QueryFinal))
                        ShowTextToScreen(f"{Assistantname} : {Answer}")
                        SetAssistantStatus("Answering...")
                        TextToSpeech(Answer)
                        os._exit(1)
    except Exception as e:
        print(f"Error in MainExecution: {e}")

def FirstThread():
    while not stop_thread.is_set():
        try:
            CurrentStatus = GetMicrophoneStatus()
            if CurrentStatus == "True":
                MainExecution()
            else:
                AIStatus = GetAssistantStatus()

            if "Available... " in AIStatus:
                sleep(0.1)
            else:
                SetAssistantStatus("Available...")
        except Exception as e:
            print(f"Error in FirstThread: {e}")

def SecondThread():
    GraphicalUserInterface()

if __name__ == "__main__":
    try:
        # Start the background thread
        thread2 = threading.Thread(target=FirstThread, daemon=True)
        thread2.start()

        # Start the GUI
        SecondThread()

    except KeyboardInterrupt:
        print("Exiting program...")
        stop_thread.set()
        thread2.join()

    except Exception as e:
        print(f"Unhandled error in main: {e}")