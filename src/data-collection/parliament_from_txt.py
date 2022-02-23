from cmath import inf
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from time import sleep
from database import Database
import os
import getopt, sys
import re
import json

def scrape_by_id(driver, id):
    url = f"https://sprs.parl.gov.sg/search/topic?reportid={id}"
    if not scrape_by_url(driver, url):
        url = f"https://sprs.parl.gov.sg/search/sprs3topic?reportid={id}"
        scrape_by_url(driver, url)

def scrape_by_url(driver, url):
    driver.get(url)

    db = Database('parliament.db', 'parliament')
    
    try:
        content = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, '//*[@id="showTopic"]/div')))
        if content.text == "undefined":
            return False

        section = ''
        title_text = ''
        sitting_date_text = ''
        parliament_number = ''
        rows = WebDriverWait(driver, 3).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'table tr')))
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, 'td')
            if len(cells) == 2:
                info_type, info = cells
                if info_type.text.lower() == "section name:":
                    section = info.text.strip()
                if info_type.text.lower() == "title:":
                    title_text = info.text.strip()
                if info_type.text.lower() == "sitting date:":
                    sitting_date_text = info.text.strip()
                if info_type.text.lower() == "parliament no:":
                    parliament_number = info.text.strip()

        match = re.search(r"reportid=.*", driver.current_url)
        id = match.group()[9:]
        path = f"parliament\\{parliament_number}\\{id}.json"

        if not os.path.exists(f"parliament\\{parliament_number}"):
            os.mkdir(f"parliament\\{parliament_number}")

        # remove noise text
        driver.execute_script("""
            document.querySelector("table[border='1']")?.remove();
            document.querySelector(".hansardcustom table")?.remove();
            document.querySelectorAll("b,strong").forEach((element) => {
                if (element.innerText.startsWith("Column: ")) {
                    element.remove();
                }                
            });
            document.querySelectorAll("p[align='left']").forEach((element) => {
                if (element.innerText.startsWith("Column: ")) {
                    element.remove();
                }
            });
        """)
        text = content.text
        #text = " ".join([re.sub(r"^1[0-2]|0?[1-9].[0-5]?[0-9] ?[ap].m.$", "", line.strip(), flags=re.IGNORECASE) 
        #                    for line in text.splitlines() if line.strip()])
        lines = [re.sub(r"^1[0-2]|0?[1-9].[0-5]?[0-9] ?[ap].m.$", "", line.strip(), flags=re.IGNORECASE) for line in text.splitlines() if line.strip()]
        lines = [re.sub(r"Column: \d+", "", line, flags=re.IGNORECASE) for line in lines]
        lines = [re.sub(r"\[.*speaker.*in the chair.*\]", "", line, flags=re.IGNORECASE) for line in lines]
        def augment_with_hashes(match):
            return f"#{match.group()}#"
        lines = [re.sub(r"^.*:", augment_with_hashes, line, flags=re.IGNORECASE) for line in lines]
        text = " ".join(lines)
        speaker_loc = [speaker.span() for speaker in re.finditer("#(.*?)#", text)]
        if (len(speaker_loc) == 0):
            with open(f"{path}", "w", encoding="utf-8") as f:
                f.write(json.dumps({
                    "id": id,
                    "section": section,
                    "title": title_text,
                    "date": sitting_date_text,
                    "speeches": [{
                        "name": None, 
                        "speech": text
                    }],
                }))
            db.save_record(sitting_date_text, title_text, driver.current_url, path)
        else:
            speaker_starts, speaker_ends = list(zip(*speaker_loc))
            speech_text_starts = speaker_ends[:]
            speech_text_ends = speaker_starts[1:] + (-1,)
            speeches_loc = list(zip(speaker_starts, speaker_ends, speech_text_starts, speech_text_ends))
            speeches = {
                "id": id,
                "section": section,
                "title": title_text,
                "date": sitting_date_text,
                "speeches": [
                {
                    "name": text[name_start+1:name_end-1], 
                    "speech": text[speech_text_start:(speech_text_end if speech_text_end != -1 else None)]
                } for (name_start, name_end, speech_text_start, speech_text_end) in speeches_loc
            ]}
            with open(f"{path}", "w", encoding="utf-8") as f:
                f.write(json.dumps(speeches))
            db.save_record(sitting_date_text, title_text, driver.current_url, path)
            return True
    except Exception as e:
        with open("errors.log", "a", encoding="utf-8") as f:
            f.write(f"{driver.current_url}: {str(e)}\n")
            return False

def main():
    urls_file = None
    ids_file = None
    start = 0
    end = None
    try:
        opts, args = getopt.getopt(sys.argv[1:], "u:i:s:e:")
        for opt, arg in opts:
            if opt == '-u':
                urls_file = arg
            if opt == '-i':
                ids_file = arg
            if opt == '-s':
                start = int(arg)
            if opt == '-e':
                end = int(arg)
    except getopt.GetoptError as err:
        print(err)  # will print something like "option -a not recognized"
        quit()

    assert urls_file != None or ids_file != None, "-u or -i is required!"

    driver = webdriver.Chrome(service=Service("chromedriver.exe"))

    if urls_file:
        with open(urls_file, "r") as f:
            urls = f.readlines()
            for url in urls[start:(end if not end else None)]:
                scrape_by_url(driver, url)
    if ids_file:
        with open(ids_file, "r") as f:
            ids = f.readlines()
            for id in ids[start:(end if not end else None)]:
                scrape_by_id(driver, id)

    driver.close()

if __name__ == "__main__":
    main()