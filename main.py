from playwright.sync_api import sync_playwright
import json
import yt_dlp
import os
import pandas as pd


def video_downloader(url, title):
    title = title.replace(":", "~")
    ydl_opts = {
        'outtmpl': f'video/{title}.%(ext)s',  # Output file name
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.imdb.com/',
        }
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        # Get the downloaded file extension (e.g. mp4, mkv)
        info_dict = ydl.extract_info(url, download=False)
        filetype = info_dict.get('ext', 'unknown')
    file_location = os.path.abspath(f'video/{title}.{filetype}')
    return file_location



def save_to_csv(data, max_results, sort_by):
    df = pd.DataFrame(data)
    file_path = f"imdb_top_{max_results}_movies_sorted-by_{sort_by}.csv"
    df.to_csv(file_path, index=False, encoding='utf-8')


def scrape_imdb_top_1000(page, max_results=10, sort_by="moviemeter"):
    page.goto(f"https://www.imdb.com/search/title/?groups=top_1000&sort={sort_by},desc", timeout=60000)

    next_50 = max_results - 1
    next_50 = next_50 // 50
    
    for i in range(next_50):
        see_more_locator = page.locator("//span[@class='ipc-see-more__text']")
        if see_more_locator.count() > 0 and see_more_locator.is_visible():
            see_more_locator.click()
            page.wait_for_timeout(6000)
        else:
            break
    print("Waiting for the page to load...")
    page.wait_for_load_state("networkidle")
    all_list = page.locator("//a[contains(@href, '/title/') and contains(@class, 'ipc-title-link-wrapper')]").all()[:max_results]
    print(len(all_list), "items will be scraped")
    all_data = []
    for item in all_list:
        try:
            href = item.get_attribute("href")
            if not href:
                continue
            
            # Open movie link in a new browser context
            movie_context = page.context.browser.new_context()
            movie_page = movie_context.new_page()
            movie_page.goto(f"https://www.imdb.com{href}", timeout=60000)

            ############################ -- ###########################
            next_data = movie_page.locator("#__NEXT_DATA__").inner_text()
            data = json.loads(next_data)
            
            title = data["props"]["pageProps"]["aboveTheFoldData"]["titleText"]["text"]
            year = data["props"]["pageProps"]["aboveTheFoldData"]["releaseYear"]["year"]
            runtime_sec = data["props"]["pageProps"]["aboveTheFoldData"]["runtime"]["seconds"]
            runtime = data["props"]["pageProps"]["aboveTheFoldData"]["runtime"]["displayableProperty"]["value"]["plainText"]
            rate = data["props"]["pageProps"]["aboveTheFoldData"]["ratingsSummary"]["aggregateRating"]
            rate_count = data["props"]["pageProps"]["aboveTheFoldData"]["ratingsSummary"]["voteCount"]

            
            directors_count = len(data["props"]["pageProps"]["aboveTheFoldData"]["principalCredits"][0]["credits"]) 
            for i in range(directors_count):
                if i == 0:
                    director = data["props"]["pageProps"]["aboveTheFoldData"]["principalCredits"][0]["credits"][i]["name"]["nameText"]["text"]
                else:
                    director += ", " + data["props"]["pageProps"]["aboveTheFoldData"]["principalCredits"][0]["credits"][i]["name"]["nameText"]["text"]

            
            writers_count = len(data["props"]["pageProps"]["aboveTheFoldData"]["principalCredits"][1]["credits"])
            for i in range(writers_count):
                if i == 0:
                    writer = data["props"]["pageProps"]["aboveTheFoldData"]["principalCredits"][1]["credits"][i]["name"]["nameText"]["text"]
                else:
                    writer += ", " + data["props"]["pageProps"]["aboveTheFoldData"]["principalCredits"][1]["credits"][i]["name"]["nameText"]["text"]

            
            interests_count = len(data["props"]["pageProps"]["aboveTheFoldData"]["interests"]["edges"])
            for i in range(interests_count):
                if i == 0:
                    interest = data["props"]["pageProps"]["aboveTheFoldData"]["interests"]["edges"][i]["node"]["primaryText"]["text"]
                else:
                    interest +=", " + data["props"]["pageProps"]["aboveTheFoldData"]["interests"]["edges"][i]["node"]["primaryText"]["text"]

            
            stars_count = len(data["props"]["pageProps"]["mainColumnData"]["cast"]["edges"])
            for i in range(stars_count):
                if i == 0:
                    star = data["props"]["pageProps"]["mainColumnData"]["cast"]["edges"][i]["node"]["name"]["nameText"]["text"]
                else:
                    star +=", " + data["props"]["pageProps"]["mainColumnData"]["cast"]["edges"][i]["node"]["name"]["nameText"]["text"]

            
            video_urls_count = len(data["props"]["pageProps"]["aboveTheFoldData"]["primaryVideos"]["edges"][0]["node"]["playbackURLs"])
            for i in range(video_urls_count):
                if i == 0:
                    video_url = data["props"]["pageProps"]["aboveTheFoldData"]["primaryVideos"]["edges"][0]["node"]["playbackURLs"][i]["url"]
                else:
                    video_url +=", " + data["props"]["pageProps"]["aboveTheFoldData"]["primaryVideos"]["edges"][0]["node"]["playbackURLs"][i]["url"]

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
            print()
            print(f"Scraped: {title} ({year})")
            print(f"Video Location: {video_location}")
            

            movie_page.close()
            movie_context.close()
        except Exception as e:
            print(f"Error processing item: {e}")
            continue
    return all_data    



def main():
    sort = [{"Popularity":"moviemeter"}, {"A-Z":"alpha"}, {"User rating":"user_rating"}, {"Number of ratings":"num_votes"}, {"US box office":"boxoffice_gross_us"}, {"Runtime":"runtime"}, {"Year":"year"}, {"Release date":"release_date"}]

    for num,i in enumerate(sort, start=0):
        for key in i:
            print(num,key)
    s_n = int(input("Enter the number of the sort you want to use: "))
    sort_by = list(sort[s_n].values())[0]
    max_results = int(input("Enter the number of results you want to scrape 1 - 1000: "))
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(locale="en-US")
        
        data = scrape_imdb_top_1000(page, max_results=max_results, sort_by=sort_by)
        save_to_csv(data, max_results=max_results, sort_by=sort_by)
        browser.close()



if __name__ == "__main__":
    try:
        main()
        print("DONE")
    except Exception as e:
        print(f"Script failed: {e}")
        raise e


