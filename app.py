import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import pandas as pd
from datetime import datetime

# --- 페이지 설정 ---
st.set_page_config(page_title="네이버 플레이스 순위 확인기", page_icon="🔍")

st.title("🔍 네이버 플레이스 순위 확인기")
st.markdown("매장명과 키워드만 입력하면, 실시간 순위를 엑셀로 만들어드립니다.")

# --- 사용자 입력 ---
col1, col2 = st.columns(2)
with col1:
    my_store_name = st.text_input("내 매장명 (예: 쇼지 삼성본점)")
with col2:
    max_rank = st.number_input("조회할 등수 (최대 100위)", min_value=10, max_value=100, value=50, step=10)

keywords_input = st.text_area("검색할 키워드 (쉼표 , 로 구분)", "삼성동 일식, 삼성동 맛집, 코엑스 점심")

# --- 실행 버튼 ---
if st.button("🚀 순위 확인 시작하기"):
    if not my_store_name:
        st.error("매장명을 입력해주세요!")
    else:
        keywords = [k.strip() for k in keywords_input.split(',')]
        
        st.info(f"검색을 시작합니다... (화면은 뜨지 않고 뒤에서 작동합니다)")
        
        # 진행률 표시 바
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        result_data = []
        
        # ==========================================
        # ★ 브라우저 옵션 설정 (공통)
        # ==========================================
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # 화면 안 보이게
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36")
        
        driver = None
        
        try:
            # ----------------------------------------------
            # ★ 핵심: 내 컴퓨터 vs 서버 컴퓨터 구분해서 실행
            # ----------------------------------------------
            try:
                # 1. 내 컴퓨터(윈도우/맥)에서 실행할 때
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
            except:
                # 2. 서버(Streamlit Cloud/리눅스)에서 실행할 때
                # 서버에는 크롬이 /usr/bin/chromium에 설치됩니다.
                options.binary_location = "/usr/bin/chromium"
                service = Service("/usr/bin/chromedriver")
                driver = webdriver.Chrome(service=service, options=options)
            # ----------------------------------------------
            
            for idx, keyword in enumerate(keywords):
                status_text.markdown(f"### 🔍 현재 검색 중: **[{keyword}]**")
                progress_bar.progress((idx) / len(keywords))

                driver.get("https://map.naver.com/v5/search")
                time.sleep(2)

                search_box = driver.find_element(By.CSS_SELECTOR, "input.input_search")
                search_box.clear()
                search_box.send_keys(keyword)
                search_box.send_keys(Keys.ENTER)
                time.sleep(2)

                driver.switch_to.frame("searchIframe")

                # 스크롤 내리기
                while True:
                    stores = driver.find_elements(By.CSS_SELECTOR, ".place_bluelink")
                    if len(stores) >= max_rank:
                        break
                    last_store = stores[-1]
                    driver.execute_script("arguments[0].scrollIntoView(true);", last_store)
                    time.sleep(1.5)
                    if len(driver.find_elements(By.CSS_SELECTOR, ".place_bluelink")) == len(stores):
                        break
                
                # 순위 찾기
                stores = driver.find_elements(By.CSS_SELECTOR, ".place_bluelink")
                rank_text = "순위 밖"
                
                for i, store in enumerate(stores):
                    name = store.text.strip()
                    if my_store_name in name:
                        rank_text = f"{i+1}위"
                        break
                
                result_data.append({
                    "날짜": datetime.now().strftime("%Y-%m-%d"),
                    "시간": datetime.now().strftime("%H:%M"),
                    "키워드": keyword,
                    "매장명": my_store_name,
                    "순위": rank_text
                })
                
                driver.switch_to.default_content()

            progress_bar.progress(100)
            status_text.success("✅ 모든 검색이 완료되었습니다!")
            driver.quit()

            st.divider()
            st.subheader("📊 검색 결과")
            df = pd.DataFrame(result_data)
            st.dataframe(df)

            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 엑셀(CSV) 다운로드",
                data=csv,
                file_name='플레이스_순위결과.csv',
                mime='text/csv',
            )

        except Exception as e:
            st.error(f"에러가 발생했습니다: {e}")
            if driver:
                driver.quit()