from selenium import webdriver
import time

from selenium.webdriver.chrome.options import Options

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import random as rd
import csv

def s():
    rdsleep = rd.uniform(1,3)
    time.sleep(rdsleep)

options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("useAutomationExtension", False)
options.add_experimental_option("detach", True)


chrome = webdriver.Chrome(options=options)
time.sleep(1)

chrome.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
})
s()

titles = []  # 제목 저장 리스트
base_url = "https://web.joongna.com/search/%EC%95%84%EC%9D%B4%ED%8F%B015?excludeSoldOutProductYn=N&page="


def get_text(driver, selector, default=""):
    try:
        return driver.find_element(By.CSS_SELECTOR, selector).text.strip()
    except:
        return default

def get_dd_values(driver):
    """dt 텍스트를 key로, dd 텍스트를 value로 매핑"""
    result = {}
    try:
        dts = driver.find_elements(By.CSS_SELECTOR, 'dt.whitespace-pre-line.text-14')
        dds = driver.find_elements(By.CSS_SELECTOR, 'dd.whitespace-pre-line.text-14')
        for dt, dd in zip(dts, dds):
            result[dt.text.strip()] = dd.text.strip()
    except:
        pass
    return result

rows = []  # CSV에 저장할 데이터

for page in range(1,2):          #스크랩할 페이지 범위
    this_url = base_url + str(page) 
    chrome.get(this_url)
    s()

    #페이지당 상품별 url 수집
    product_links = chrome.find_elements(By.CSS_SELECTOR, 'a.w-full')
    product_urls = []
    
    #href속성 추출
    for link in product_links:
        href = link.get_attribute('href')

        if href and '/product/' in href:
            product_urls.append(href)
    s()

    # 각 상품 스크랩
    for i, url in enumerate(product_urls):
        s()
        chrome.get(url)
        s()
        
        #제목 추출
        try:
            # 제목
            title = get_text(chrome, 'h1.whitespace-pre-line')

            # 가격
            price = get_text(chrome, 'span.whitespace-pre-line.text-32.font-bold')

            # 본문
            content = get_text(chrome, 'p.text-16')

            # 신뢰지수
            trust = get_text(chrome, 'span[aria-label]')

            # 검수 데이터 (dt → dd 매핑)
            dd = get_dd_values(chrome)
            model    = dd.get('모델명', '')
            color    = dd.get('컬러', '')
            status   = dd.get('상태', '')
            damage   = dd.get('파손,찍힘', '')
            screen   = dd.get('화면불량', '')
            function = dd.get('기능불량', '')
            battery  = dd.get('배터리', '')
            care     = dd.get('케어플러스', '')

            rows.append({
                '제목': title,
                '모델명': model,
                '컬러': color,
                '상태': status,
                '파손,찍힘': damage,
                '화면불량': screen,
                '기능불량': function,
                '배터리': battery,
                '케어플러스': care,
                '본문': content,
                '신뢰지수': trust,
                '가격': price,
            })

            print(f"[{i+1}] {title} / {price}")

        except Exception as e:
            print(f"오류: {url} → {e}")
            

        chrome.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);") #스크롤; 봇 감지 방지
        
        if i % 10 == 0 and i != 0:                         #일정 단위별 랜덤 휴식; 봇 감지 방지
            time.sleep(rd.uniform(10, 20))
        
        #테스트 과부하 방지용 limit
        if len(rows)>= 20:
            break
    
    

    time.sleep(rd.uniform(3, 6))

with open("joongna_002.csv", "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=['제목','모델명','컬러','상태','파손,찍힘','화면불량','기능불량','배터리','케어플러스','본문','신뢰지수','가격'])
    writer.writeheader()
    writer.writerows(rows)

print(f"\n완료! 총 {len(rows)}개 저장 → joongna_002.csv")