import feedparser

class RSSFeedValidator:
    def __init__(self, sources):
        self.sources = sources

    def validate_rss_feed(self, url):
        try:
            feed = feedparser.parse(url)
            if feed.bozo:
                raise Exception(feed.bozo_exception)
            return True
        except Exception as e:
            print(f"Invalid RSS feed URL: {url} - {e}")
            return False

    def validate_all_feeds(self):
        valid_feeds = []
        for url in self.sources:
            if self.validate_rss_feed(url):
                valid_feeds.append(url)
        return valid_feeds

# Example usage
if __name__ == "__main__":
    sources = [
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
        "https://www.huffpost.com/section/front-page/feed",
    ]

    validator = RSSFeedValidator(sources)
    valid_feeds = validator.validate_all_feeds()
    print("Valid RSS feeds:")
    for feed in valid_feeds:
        print(feed)