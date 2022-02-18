from time import sleep
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from database import Database
import re
import json
import os
import getopt
import sys
import pandas as pd

def open_link_in_tab(driver, link):
    actions = ActionChains(driver)
    actions.key_down(Keys.CONTROL)
    actions.click(link)
    actions.perform()

def search_google(section, start = 0):
    start = pd.date_range('2012-02-01','2022-02-01' , freq='7D')
    start = start.strftime("%#m-%#d-%Y").tolist()
    end = pd.date_range('2012-02-07','2022-02-01' , freq='7D')
    end = end.strftime("%#m-%#d-%Y").tolist()
    periods = list(zip(start,end))

    if os.path.exists("todayonline") is False:
        os.makedirs("todayonline")

    chrome_options = Options()
    chrome_options.add_argument('user-data-dir=C:\\Users\\ktkhu\\Desktop\\Exeter\\ECMM451\\src\\data-collection\\profile')
    driver = webdriver.Chrome(service=Service("chromedriver.exe"), options=chrome_options)
    driver.get("https://www.google.com/")
    input = driver.find_element(By.CSS_SELECTOR, "form[role='search'] input[name='q']")
    input.send_keys(f"Singapore site:www.todayonline.com/{section}")
    input.send_keys(Keys.RETURN)
    menu = WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[id='hdtb-msb'] div[class='hdtb-mitem']")))
    menu[2].click()
    sleep(1)
    tools = driver.find_element(By.ID, "hdtb-tls")
    tools.click()
    sleep(1)
    *_, sorted_by = driver.find_elements(By.CSS_SELECTOR, "div[id='hdtbMenus'] div[class='KTBKoe']")
    sorted_by.click()
    driver.find_element(By.CSS_SELECTOR, "div[id='lb'] a").click()
    sleep(1)

    for period in periods[start:]:
        from_date, to_date = period

        try:
            period = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[id='hdtbMenus'] div[class='KTBKoe']")))
            period.click()
            sleep(1)

            *_, custom_range = driver.find_elements(By.CSS_SELECTOR, "div[id='lb'] g-menu-item")
            custom_range.click()
            sleep(1)

            fdate, tdate = driver.find_elements(By.CSS_SELECTOR, "form[id='T3kYXe'] input[type='text']")
            fdate.clear()
            tdate.clear()
            fdate.send_keys(from_date)
            tdate.send_keys(to_date)

            driver.find_element(By.CSS_SELECTOR, "form[id='T3kYXe'] g-button").click()
            sleep(1)

            last_page = False
            n = 0
            while last_page is False:
                links = driver.find_elements(By.CSS_SELECTOR, "div[id='rso'] g-card a")
                hrefs = [link.get_attribute("href") for link in links]
                n += len(hrefs)
                with open(f"todayonline_urls.txt", "a") as f:
                    f.write("\n".join(hrefs))
                    f.write("\n")
                
                try:
                    next_btn = driver.find_element(By.CSS_SELECTOR, "a[id='pnnext']")
                    driver.execute_script("arguments[0].scrollIntoView();", next_btn)
                    next_btn.click()
                except NoSuchElementException as e:
                    last_page = True
            
            with open("todayonline.log", "a") as f:
                f.write(f"Finish: {from_date} {to_date} {n}\n")

        except TimeoutException as e:
            with open("error.log", "a") as f:
                f.write(f"Timeout: {from_date} {to_date}\n")

    driver.close()

def main():
    start = None
    end = None
    try:
        opts, args = getopt.getopt(sys.argv[1:], "s:e:")
        for opt, arg in opts:
            if opt == '-s':
                start = int(arg)
            elif opt == '-e':
                end = int(arg)
    except getopt.GetoptError as err:
        print(err)
        quit()

    if os.path.exists("todayonline") is False:
        os.makedirs("todayonline")

    search_google("commentary")
    search_google("big-read")

    assert os.path.exists("todayonline_urls.txt"), "todayonline_urls.txt NOT found!"
    assert start != None, "Argument -s is required!"
    assert end != None, "Argument -e is required!"

    with open("todayonline_urls.txt", "r") as f:
        txt = f.read()
        urls = [line.strip() for line in txt.splitlines() if line.strip()]

    db = Database('todayonline.db', 'todayonline')

    driver = webdriver.Chrome(service=Service("chromedriver.exe"))

    for url in urls[start:(end+1)]:
        driver.get(url)

        try:
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "section div[class='text']")))      
            date = driver.find_element(By.CSS_SELECTOR, "div[class='article__row article__row--']")
            title = driver.find_element(By.CSS_SELECTOR, "section h1[class='h1 h1--page-title']")
            data = driver.find_element(By.CSS_SELECTOR, "section div[class='text']")
            text = " ".join([line.strip() for line in data.text.splitlines() if line.strip()])
            url = driver.current_url
            *_, filename = url[8:].split("/")
            path = f"todayonline\\{filename}.json"
            with open(f"{path}", "w", encoding="utf-8") as f:
                f.write(json.dumps({
                    "title": title.text,
                    "date": date.text[10:],
                    "content": text
                })) 
                db.save_record(date.text, title.text, url, path)
            
        except (TimeoutException, StaleElementReferenceException, NoSuchElementException, IndexError) as e:
            with open("errors.log", "a", encoding='utf-8') as f:
                f.write(f"Error: {driver.current_url} {str(e)}")

    driver.close()

if __name__ == "__main__":
    main()