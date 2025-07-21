import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
from playwright.sync_api import sync_playwright, Page
import yt_dlp
from tqdm import tqdm
import argparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def video_downloader(url: str, title: str) -> str:
    title = title.replace(":", "~")
    output_dir = Path("video")
    output_dir.mkdir(exist_ok=True)
    ydl_opts = {
        'outtmpl': str(output_dir / f"{title}.%(ext)s"),
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.imdb.com/',
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        info_dict = ydl.extract_info(url, download=False)
        filetype = info_dict.get('ext', 'unknown')
    file_location = str(output_dir / f"{title}.{filetype}")
    return file_location


def save_to_csv(data: List[Dict[str, Any]], max_results: int, sort_by: str) -> None:
    df = pd.DataFrame(data)
    file_path = f"imdb_top_{max_results}_movies_sorted-by_{sort_by}.csv"
    df.to_csv(file_path, index=False, encoding='utf-8')
    logging.info(f"Saved data to {file_path}")


def extract_names(credits: List[Dict[str, Any]]) -> str:
    return ", ".join([c["name"]["nameText"]["text"] for c in credits])


def extract_interests(edges: List[Dict[str, Any]]) -> str:
    return ", ".join([e["node"]["primaryText"]["text"] for e in edges])


def extract_stars(edges: List[Dict[str, Any]]) -> str:
    return ", ".join([e["node"]["name"]["nameText"]["text"] for e in edges])


def extract_video_urls(edges: List[Dict[str, Any]]) -> str:
    if not edges:
        return ""
    return ", ".join([u["url"] for u in edges[0]["node"].get("playbackURLs", [])])


def scrape_imdb_top_1000(page: Page, max_results: int = 10, sort_by: str = "moviemeter") -> List[Dict[str, Any]]:
    page.goto(f"https://www.imdb.com/search/title/?groups=top_1000&sort={sort_by},desc", timeout=60000)
    next_50 = (max_results - 1) // 50
    for _ in range(next_50):
        see_more_locator = page.locator("//span[@class='ipc-see-more__text']")
        if see_more_locator.count() > 0 and see_more_locator.is_visible():
            see_more_locator.click()
            page.wait_for_timeout(6000)
        else:
            break
    page.wait_for_load_state("networkidle")
    all_list = page.locator("//a[contains(@href, '/title/') and contains(@class, 'ipc-title-link-wrapper')]").all()[:max_results]
    logging.info(f"{len(all_list)} items will be scraped")
    all_data = []
    for item in tqdm(all_list, desc="Scraping movies"):
        try:
            href = item.get_attribute("href")
            if not href:
                continue
            movie_context = page.context.browser.new_context()
            movie_page = movie_context.new_page()
            movie_page.goto(f"https://www.imdb.com{href}", timeout=60000)
            next_data = movie_page.locator("#__NEXT_DATA__").inner_text()
            data = json.loads(next_data)
            props = data["props"]["pageProps"]
            above = props["aboveTheFoldData"]
            main_col = props.get("mainColumnData", {})
            title = above["titleText"]["text"]
            year = above["releaseYear"]["year"]
            runtime_sec = above["runtime"]["seconds"]
            runtime = above["runtime"]["displayableProperty"]["value"]["plainText"]
            rate = above["ratingsSummary"].get("aggregateRating")
            rate_count = above["ratingsSummary"].get("voteCount")
            director = extract_names(above["principalCredits"][0]["credits"])
            writer = extract_names(above["principalCredits"][1]["credits"])
            interest = extract_interests(above.get("interests", {}).get("edges", []))
            star = extract_stars(main_col.get("cast", {}).get("edges", []))
            video_url = extract_video_urls(above.get("primaryVideos", {}).get("edges", []))
            if video_url:
                video_location = video_downloader(video_url.split(",")[0], title)
            else:
                video_location = "No video available"
            new_data = {
                "title": title,
                "year": year,
                "runtime_sec": runtime_sec,
                "runtime": runtime,
                "rate": rate,
                "rate_count": rate_count,
                "director": director,
                "writer": writer,
                "interest": interest,
                "star": star,
                "video_url": video_url,
                "video_location": video_location
            }
            all_data.append(new_data)
            logging.info(f"Scraped: {title} ({year})")
            movie_page.close()
            movie_context.close()
        except Exception as e:
            logging.error(f"Error processing item: {e}")
            continue
    return all_data


def main():
    parser = argparse.ArgumentParser(description="Scrape IMDb Top 1000 Movies")
    parser.add_argument("-m","--max_results", type=int, default=10, help="Number of results to scrape (1-1000)")
    parser.add_argument("-s","--sort_by", type=str, default="moviemeter", help="Sort by field")
    parser.add_argument("-h","--headless", action="store_true", help="Run browser in headless mode")
    args = parser.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        page = browser.new_page(locale="en-US")
        data = scrape_imdb_top_1000(page, max_results=args.max_results, sort_by=args.sort_by)
        save_to_csv(data, max_results=args.max_results, sort_by=args.sort_by)
        browser.close()


if __name__ == "__main__":
    try:
        main()
        logging.info("DONE")
    except Exception as e:
        logging.error(f"Script failed: {e}")
        raise
