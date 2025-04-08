import tkinter as tk
from tkinter import scrolledtext, font as tkfont
import google.generativeai as genai
import pyttsx3
import threading
import re
import json
import os

# ============ GEMINI SETUP ============
genai.configure(api_key="AIzaSyC0YsB1fXdumOy2nVZhGVIybrJ9pN9ua5s")
model = genai.GenerativeModel("gemini-1.5-pro-001")

# ============ TTS SETUP ================
engine = pyttsx3.init()
speaking = False
speak_thread = None

language_voice_map = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Japanese": "ja",
    "Hindi": "hi"
}

# ========== MEMORY FILE ============
MEMORY_FILE = "memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f)

# =========== GUI LOGIC =================
class AILanguageCoach:
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 AI Language Coach")
        self.root.geometry("850x700")
        self.root.configure(bg="#0a0f1c")

        self.memory = load_memory()
        self.memory.setdefault("learning_language", "English")
        self.last_bot_response = ""

        self.custom_font = tkfont.Font(family="Fira Code", size=13)
        self.heading_font = tkfont.Font(family="Segoe UI", size=14, weight="bold")

        self.available_languages = list(language_voice_map.keys())
        lang_frame = tk.Frame(root, bg="#0a0f1c")
        lang_frame.pack(pady=5)

        tk.Label(lang_frame, text="🌟 Learning Language:", bg="#0a0f1c", fg="#00ffd0", font=self.heading_font).pack(side=tk.LEFT)
        self.lang_var = tk.StringVar(value=self.memory["learning_language"])
        lang_menu = tk.OptionMenu(lang_frame, self.lang_var, *self.available_languages, command=self.change_language)
        lang_menu.config(bg="#1f2a3a", fg="white", font=("Fira Code", 12), highlightbackground="#1f2a3a", activebackground="#00ffd0", activeforeground="#000")
        lang_menu["menu"].config(bg="#101828", fg="white", activebackground="#00ffd0")
        lang_menu.pack(side=tk.LEFT, padx=10)

        self.chat_display = scrolledtext.ScrolledText(
            root, wrap=tk.WORD, font=self.custom_font,
            bg="#0c1a2a", fg="#00ffe1", insertbackground="#00ffe1",
            bd=0, padx=10, pady=10, relief=tk.FLAT
        )
        self.chat_display.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.tag_config("user", foreground="#72f1b8", font=("Fira Code", 13, "bold"))
        self.chat_display.tag_config("bot", foreground="#1fa2ff", font=("Fira Code", 13, "italic"))

        self.user_input = tk.Entry(
            root, font=self.custom_font, bg="#12263a", fg="#ffffff",
            insertbackground='white', bd=3, relief=tk.FLAT, highlightthickness=2,
            highlightbackground="#00ffd0", highlightcolor="#00ffd0"
        )
        self.user_input.pack(padx=20, pady=(0, 10), fill=tk.X)
        self.user_input.bind("<Return>", self.send_message)

        button_frame = tk.Frame(root, bg="#0a0f1c")
        button_frame.pack(pady=10)

        self.send_button = tk.Button(
            button_frame, text="🚀 Send", font=self.heading_font, command=self.send_message,
            bg="#00ffd0", fg="#000", padx=25, pady=8, relief=tk.FLAT, bd=0
        )
        self.send_button.default_bg, self.send_button.default_fg = "#00ffd0", "#000"
        self._style_button(self.send_button)
        self.send_button.grid(row=0, column=0, padx=10)

        self.speak_button = tk.Button(
            button_frame, text="🔊 Speak", font=self.heading_font,
            command=self.toggle_speak, bg="#1c2230", fg="#00ffd0", padx=25, pady=8, relief=tk.FLAT, bd=0
        )
        self.speak_button.default_bg, self.speak_button.default_fg = "#1c2230", "#00ffd0"
        self._style_button(self.speak_button)
        self.speak_button.grid(row=0, column=1, padx=10)

    def _style_button(self, btn):
        btn.bind("<Enter>", lambda e: btn.config(bg="#00ffcc", fg="#000"))
        btn.bind("<Leave>", lambda e: btn.config(bg=btn.default_bg, fg=btn.default_fg))

    def change_language(self, selection):
        self.memory["learning_language"] = selection
        save_memory(self.memory)

    def toggle_speak(self):
        global speaking, speak_thread
        if speaking:
            self.stop_speaking()
            self.speak_button.config(text="🔊 Speak")
        else:
            self.speak_button.config(text="⏹ Stop")
            speak_thread = threading.Thread(target=self.speak_text, args=(self.last_bot_response,), daemon=True)
            speak_thread.start()
            threading.Thread(target=self.reset_button_after_speak, daemon=True).start()

    def reset_button_after_speak(self):
        global speaking
        while speaking:
            continue
        self.speak_button.config(text="🔊 Speak")

    def speak_text(self, text):
        global speaking
        speaking = True
        lang_code = language_voice_map.get(self.memory.get("learning_language", "English"), "en")
        for voice in engine.getProperty('voices'):
            if lang_code in voice.languages[0].decode("utf-8"):
                engine.setProperty('voice', voice.id)
                break
        engine.say(text)
        engine.runAndWait()
        speaking = False

    def stop_speaking(self):
        global speaking
        if speaking:
            engine.stop()
            speaking = False

    def send_message(self, event=None):
        user_msg = self.user_input.get().strip()
        if not user_msg:
            return
        self.display_message("You", user_msg, tag="user")
        self.user_input.delete(0, tk.END)
        self.extract_memory(user_msg)
        threading.Thread(target=self.get_bot_response, args=(user_msg,), daemon=True).start()

    def display_message(self, sender, message, tag="bot"):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"{sender}: {message}\n", tag)
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.yview(tk.END)

    def extract_memory(self, text):
        updated = False
        name_match = re.search(r"my name is (\w+)", text, re.IGNORECASE)
        fav_lang_match = re.search(r"my favorite language is (\w+)", text, re.IGNORECASE)
        if name_match:
            self.memory["name"] = name_match.group(1)
            updated = True
        if fav_lang_match:
            self.memory["favorite_language"] = fav_lang_match.group(1)
            updated = True
        if updated:
            save_memory(self.memory)

    def build_context_prompt(self):
        lang = self.memory.get("learning_language", "English")
        context = (
            f"You are an AI Language Coach helping the user learn to speak {lang}.\n"
            "Correct their sentences, teach vocabulary, and respond in simple sentences.\n"
        )
        for key, value in self.memory.items():
            if key != "learning_language":
                context += f"- User's {key} is {value}.\n"
        return context

    def get_bot_response(self, message):
        try:
            prompt = self.build_context_prompt() + "\nUser: " + message
            response = model.generate_content(prompt)
            bot_reply = response.text.strip()
            self.last_bot_response = bot_reply
            self.display_message("Coach", bot_reply, tag="bot")
        except Exception as e:
            self.display_message("Coach", f"Error: {str(e)}", tag="bot")

# =========== RUN APP ===========
if __name__ == "__main__":
    root = tk.Tk()
    app = AILanguageCoach(root)
    root.mainloop()
