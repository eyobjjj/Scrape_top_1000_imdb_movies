# IMDb Top 1000 Movies Scraper

This project scrapes data from IMDb's Top 1000 movies list, downloads available trailers, and saves the results to a CSV file.

## Features

- Scrapes movie details (title, year, runtime, rating, directors, writers, stars, etc.)
- Downloads available movie trailers using `yt_dlp`
- Saves all data to a CSV file
- Allows sorting by popularity, rating, year, and more

## Requirements

- Python 3.7+
- [Playwright](https://playwright.dev/python/)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- pandas

## Installation

```bash
pip install -r requirements.txt
playwright install
```

## Usage

1. Run the script:
    ```bash
    python main.py
    ```
2. Choose the sorting method and number of movies to scrape when prompted.
3. Scraped data and downloaded videos will be saved in the current directory.

## Notes

- Make sure you have a stable internet connection.
- Downloaded videos are saved in the `video/` folder.
- IMDb may change its structure, which could break the scraper.

## License

This project is for educational purposes only.