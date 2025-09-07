import os
from dotenv import load_dotenv
from flask import jsonify
import asyncio
from playwright.async_api import async_playwright
import smtplib
from email.mime.text import MIMEText

from .config import url, selectors
from .helpers import (
    click_button,
    fill_text_box,
    get_keywords,
    convert_array_to_json,
    convert_json_to_txt,
    write_to_file,
    read_from_file,
    filter_diff_json,
    get_timestamp
)

load_dotenv()

async def login_to_nextdoor(page, email, password):
    await page.goto(f"{url}/login/")

    await fill_text_box(page, "textbox", "Email", email)
    await fill_text_box(page, "textbox", "Password", password)
    await click_button(page, "button", "Log in")


def get_users_pass():
    users = os.getenv("NEXTDOOR_USERS", "").split(",")
    passwords = os.getenv("NEXTDOOR_PASSES", "").split(",")

    if len(users) != len(passwords):
        raise ValueError("Number of users and passwords do not match")

    return [
        {"email": user.strip(), "password": password.strip()}
        for user, password in zip(users, passwords)
    ]


async def scroll_to_load_posts(page, duration_sec=30):
    await click_button(page, "button", "Filter")
    await click_button(page, "menuitem", "Recent")

    await page.wait_for_selector(selectors["post"], timeout=30000)

    start_time = asyncio.get_event_loop().time()
    while (asyncio.get_event_loop().time() - start_time) < duration_sec:
        await page.evaluate("window.scrollBy(0, 20 * window.innerHeight)")
        await page.wait_for_timeout(1000)


async def extract_post_data(page):
    post_elements = await page.query_selector_all(selectors["post"])
    filtered_posts = []

    for post in post_elements:
        try:
            name = await post.query_selector(selectors["name"])
            text = await post.query_selector(selectors["text"])
            time = await post.query_selector(selectors["time"])

            name_text = (await name.text_content()) if name else ""
            text_text = (await text.text_content()) if text else ""
            time_text = (await time.text_content()) if time else ""
            href = (await name.get_attribute("href")) if name else ""

            keywords = get_keywords(text_text)

            if keywords:
                filtered_posts.append({
                    "name": name_text.strip(),
                    "text": text_text.strip(),
                    "time": time_text.strip(),
                    "href": f"{url.strip()}{href.strip()}",
                    "keywords": keywords
                })
        except Exception as e:
            print(f"Error extracting post data: {e}")

    return filtered_posts


def get_absolute_path(relative_path):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, relative_path)


async def write_files(filtered_posts):
    old_json = await read_from_file(get_absolute_path(os.getenv("JSON_FILE_PATH"))) or "[]"
    old_txt = await read_from_file(get_absolute_path(os.getenv("TXT_FILE_PATH"))) or ""

    posts_json = convert_array_to_json(filtered_posts)
    posts_txt = convert_json_to_txt(posts_json)
    await write_to_file(posts_json, get_absolute_path(os.getenv("JSON_FILE_PATH")))
    await write_to_file(posts_txt, get_absolute_path(os.getenv("TXT_FILE_PATH")))

    if old_json:
        diff_posts_json = filter_diff_json(posts_json, old_json)
        diff_posts_txt = convert_json_to_txt(diff_posts_json)
        await write_to_file(diff_posts_json, get_absolute_path(os.getenv("DIFF_JSON_FILE_PATH")))
        await write_to_file(diff_posts_txt, get_absolute_path(os.getenv("DIFF_TXT_FILE_PATH")))

        await write_to_file(old_json, get_absolute_path(os.getenv("PREV_JSON_FILE_PATH")))
        await write_to_file(old_txt, get_absolute_path(os.getenv("PREV_TXT_FILE_PATH")))

        return convert_json_to_txt(diff_posts_json) if len(eval(diff_posts_json)) > 0 else ""
    return posts_txt


async def send_nextdoor_update_email(text, subject="Nextdoor Posts"):
    if not text:
        print("No new posts to send via email.")
        return

    msg = MIMEText(text)
    msg["Subject"] = subject
    msg["From"] = os.getenv("EMAIL_USER")
    msg["To"] = os.getenv("EMAIL_USER")

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
            server.send_message(msg)
        print("Email sent!")
    except Exception as e:
        print(f"Error sending email: {e}")


async def log_run_time():
    log_time = get_timestamp()
    json_file = await read_from_file(get_absolute_path(os.getenv("JSON_FILE_PATH")))
    num_posts = len(eval(json_file)) if json_file else 0

    log_message = f"NextDoor Scraper : {log_time} : {num_posts} Posts\n"
    await write_to_file(log_message, get_absolute_path(os.getenv("LOG_FILE_PATH")), append=True)


async def scrape_nextdoor_posts():
    all_filtered_posts = []

    try:
        accounts = get_users_pass()
        async with async_playwright() as p:
            for account in accounts:
                browser = None
                try:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    try:
                        await login_to_nextdoor(page, account["email"], account["password"])
                    except Exception as login_error:
                        print(f"Login failed for account {account['email']}: {login_error}")
                        if browser:
                            await browser.close()
                        continue

                    await scroll_to_load_posts(page, 20)
                    filtered_posts = await extract_post_data(page)
                    all_filtered_posts.extend(filtered_posts)
                    await page.wait_for_timeout(2000)
                except Exception as error:
                    print(f"Error processing account {account['email']}:", error)
                finally:
                    if browser:
                        await browser.close()

        email_txt = await write_files(all_filtered_posts)
        await send_nextdoor_update_email(email_txt, "Nextdoor Posts - Multiple Accounts")
        await log_run_time()
    except Exception as error:
        await send_nextdoor_update_email(str(error), "Nextdoor Scraper Error")


async def scrape_nextdoor_posts_endpoint():
    try:
        await scrape_nextdoor_posts()
        return jsonify({"status": "success"})
    except Exception as error:
        return jsonify({"status": "error", "message": str(error)}), 500
