#!/usr/bin/env python3

import feedparser
from datetime import datetime
import tkinter as tk
from tkinter import ttk
import webbrowser
from dateutil.parser import parse
import pytz
import requests
import time
import threading
import json

import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def reformat_date(input_string):
    try:
        dt = parse(input_string)
        pacific = pytz.timezone('America/Los_Angeles')
        dt = dt.astimezone(pacific) if dt.tzinfo else pacific.localize(dt)
        return dt.strftime("%a, %d %b %Y %H:%M:%S")
    except Exception:
        return "Error parsing date/time string"

def analyze_content(url):
    try:
        print(f"Analyzing content for URL: {url}")

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": f"Summarize the article in 5 or fewer sentences, marking key words, phrases, and ticker symbols with **. Limit to 150 tokens. Do not include introductions or explanations. URL: {url}",
                }
            ],
            model="llama3-8b-8192",
        )
        return chat_completion.choices[0].message.content
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            return "Rate limit exceeded. Please try again later."
        print(f"HTTPError: {e.response.status_code} - {e.response.text}")
        return "Error analyzing content"
    except Exception as e:
        print(f"Exception: {str(e)}")
        return "Error analyzing content"

def fetch_and_analyze_rss(sources, article_limit):
    result = []
    try:
        with open("articles_log.json", "r") as file:
            logged_articles = json.load(file)
    except FileNotFoundError:
        logged_articles = []

    for source in sources:
        feed = feedparser.parse(source)
        for entry in feed.entries[:article_limit]:
            title = entry.get('title', 'No Title')
            url = entry.get('link', 'No URL')

            # Check if the article is already logged
            existing_article = next((article for article in logged_articles if article[0] == title and article[2] == url), None)
            if existing_article:
                result.append(existing_article)
                print(f"Article already logged: {title} from {existing_article[4]}")
                continue

            published_date = entry.get('published', 'No Date')
            analysis = analyze_content(url)

            source_name = feed.feed.get('title', 'Unknown Source')
            formatted_date = reformat_date(published_date)
            new_article = [title, formatted_date, url, analysis, source_name]
            result.append(new_article)
            log_article(new_article)
            print(f"Fetched and analyzed article: {title} from {source_name}")

    return sorted(result, key=lambda x: datetime.strptime(x[1], '%a, %d %b %Y %H:%M:%S'), reverse=True)

def log_article(article):
    try:
        with open("articles_log.json", "r") as file:
            logged_articles = json.load(file)
    except FileNotFoundError:
        logged_articles = []

    logged_articles.append(article)
    with open("articles_log.json", "w") as file:
        json.dump(logged_articles, file)

class NewsSummarizerApp:
    def __init__(self, root):
        print("Initializing NewsSummarizerApp...")
        self.root = root
        self.root.title("News Summarizer")
        self.root.geometry("800x1200")
        print("Window title and geometry set.")

        self.sources = [
        "https://www.marketwatch.com/rss/topstories",
        "https://www.businessinsider.com/rss",
        "https://seekingalpha.com/feed.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "https://feeds.bbci.co.uk/news/rss.xml",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://www.theguardian.com/world/rss",
        "https://www.forbes.com/most-popular/feed/",
        "https://www.ft.com/?format=rss",
        "https://www.npr.org/rss/rss.php?id=1001",
        "https://www.latimes.com/local/rss2.0.xml",
        ]
        self.article_limit = 10
        self.articles = []
        self.seen_articles = set()
        self.timer = None
        self.countdown = 60
        print("Sources and initial variables set.")

        self.panel_frame = tk.Frame(self.root)
        self.panel_frame.pack(anchor='n')
        print("Panel frame created and packed.")

        self.latest_update_label = tk.Label(self.panel_frame, text="", font=("Helvetica", 10, "bold"))
        self.latest_update_label.pack(side=tk.LEFT)
        print("Latest update label created and packed.")

        self.countdown_label = tk.Label(self.panel_frame, text="", font=("Helvetica", 10))
        self.countdown_label.pack(side=tk.LEFT, padx=10)
        print("Countdown label created and packed.")

        self.search_entry = tk.Entry(self.panel_frame, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=10)
        print("Search entry created and packed.")

        self.search_button = tk.Button(self.panel_frame, text="Search", command=self.search_articles)
        self.search_button.pack(side=tk.LEFT)
        print("Search button created and packed.")

        self.is_paused = False  # Add a flag to track the pause state
        print("Pause state initialized.")

        self.pause_button = tk.Button(self.panel_frame, text="Pause", command=self.toggle_pause)
        self.pause_button.pack(side=tk.LEFT, padx=10)
        print("Pause button created and packed.")

        self.canvas = tk.Canvas(self.root)
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        print("Canvas, scrollbar, and scrollable frame created.")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        print("Scrollable frame bind configured.")

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        print("Canvas and scrollbar packed.")

        self.root.bind_all("<MouseWheel>", self.on_mousewheel)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        print("MouseWheel and WM_DELETE_WINDOW bindings set.")

        self.update_articles()
        self.update_countdown()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_button.config(text="Continue")
            if self.timer:
                self.timer.cancel()
            print("Updates paused.")
        else:
            self.pause_button.config(text="Pause")
            self.update_articles()
            print("Updates continued.")

    def update_articles(self):
        if self.is_paused:
            return
        fresh_articles = fetch_and_analyze_rss(self.sources, self.article_limit)
        fresh_articles = [article for article in fresh_articles if article[2] not in self.seen_articles]
        for article in fresh_articles:
            self.seen_articles.add(article[2])
            log_article(article)
            self.articles.append(article)
        self.articles.sort(key=lambda x: datetime.strptime(x[1], '%a, %d %b %Y %H:%M:%S'), reverse=True)
        self.display_articles()
        self.latest_update_label.config(text=f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")
        self.countdown = 60
        self.timer = threading.Timer(60.0, self.update_articles)
        self.timer.start()
        print("Articles updated and countdown started.")

    def update_countdown(self):
        if self.is_paused:
            self.countdown_label.config(text="Updates Paused")
        else:
            if self.countdown > 0:
                self.countdown_label.config(text=f"Next Update in: {self.countdown}s")
                self.countdown -= 1
        self.root.after(1000, self.update_countdown)

    def on_close(self):
        if self.timer:
            self.timer.cancel()
        self.root.destroy()

    def on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def open_url(self, url):
        webbrowser.open(url)

    def display_articles(self, articles=None):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        articles = articles or self.articles
        for article in articles:
            source_label = tk.Label(self.scrollable_frame, text=f"{article[1]} | {article[4]}", fg="grey", font=("Helvetica", 8))
            source_label.pack(anchor='w', pady=(10, 0))

            title_label = tk.Label(self.scrollable_frame, text=article[0], font=("Helvetica", 14, "bold"), fg="blue", cursor="hand2", wraplength=750, justify="left")
            title_label.pack(anchor='w')
            title_label.bind("<Button-1>", lambda e, url=article[2]: self.open_url(url))

            # Handle bold text (separated by ** in the summary)
            parts = article[3].split('**')
            summary_text_widget = tk.Text(self.scrollable_frame, wrap="word", font=("Helvetica", 10), height=8, width=100, relief="flat")
            summary_text_widget.pack(anchor='w', padx=10)
            
            for i, part in enumerate(parts):
                if i % 2 == 0:  # Non-bold text
                    summary_text_widget.insert(tk.END, part)
                else:  # Bold text
                    summary_text_widget.insert(tk.END, part, ("bold",))
            
            summary_text_widget.tag_configure("bold", font=("Helvetica", 10, "bold"))
            summary_text_widget.config(state=tk.DISABLED)

    def search_articles(self):
        query = self.search_entry.get().lower()
        filtered_articles = [article for article in self.articles if query in article[0].lower() or query in article[4].lower() or query in article[3].lower()]
        self.display_articles(filtered_articles)

if __name__ == '__main__':
    root = tk.Tk()
    app = NewsSummarizerApp(root)
    app.display_articles()
    root.mainloop()