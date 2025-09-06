from datetime import datetime
import json
from config import line_break

async def click_button(page, role, name, timeout=30000):
    button = await page.get_by_role(role, name=name)
    await button.wait_for(state='visible', timeout=timeout)
    await button.click()


async def fill_text_box(page, role, name, fill_text, timeout=30000):
    text_box = await page.get_by_role(role, name=name)
    await text_box.wait_for(state='visible', timeout=timeout)
    await text_box.fill(fill_text)


def get_timestamp():
    return datetime.now().strftime("%m/%d/%Y - %I:%M:%S %p")


def get_keywords(text):
    with open('keywords.json', 'r') as f:
        keywords_json = json.load(f)

    keywords = keywords_json.get('keywords', [])
    found_keywords = set()
    lower_text = text.lower()

    for keyword in keywords:
        # `\b` is a word boundary, ensuring we match whole words/phrases only
        import re
        regex = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
        if regex.search(lower_text):
            found_keywords.add(keyword)

    return list(found_keywords)


def convert_array_to_json(array):
    return json.dumps(array, indent=4)


def convert_json_to_txt(json_str):
    array = json.loads(json_str)
    output = f"Scrape Time: {get_timestamp()}\n"
    output += f"Found {len(array)} posts.\n"
    output += line_break

    for item in array:
        output += f"{item['name']} : {item['time']}\n"
        output += f"{item['href']}\n"
        output += f"[{', '.join(item['keywords'])}]\n\n"
        output += f"{item['text']}\n"
        output += line_break

    return output


async def write_to_file(data, file_path, append=False):
    try:
        mode = 'a' if append else 'w'
        with open(file_path, mode, encoding='utf-8') as f:
            f.write(data)
        print(f"Posts written to {file_path}")
    except Exception as error:
        print(f"Error writing to file {file_path}:", error)

async def read_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return None


def filter_diff_json(new_json, old_json):
    new_posts = json.loads(new_json)
    old_posts = json.loads(old_json)

    old_post_set = {post['text'].strip() for post in old_posts}
    diff_posts = [post for post in new_posts if post['text'].strip() not in old_post_set]

    return convert_array_to_json(diff_posts)