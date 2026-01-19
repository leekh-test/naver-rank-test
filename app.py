import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        result_data = []
        
        # 브라우저 옵션
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36")
        
        driver = None
        
        try:
            # 드라이버 설정 (로컬 vs 서버 자동 감지)
            try:
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
            except:
                options.binary_location = "/usr/bin/chromium"
                service = Service("/usr/bin/chromedriver")
                driver = webdriver.Chrome(service=service, options=options)
            
            # 대기 시간을 위한 도구 준비 (최대 15초 기다림)
            wait = WebDriverWait(driver, 15)

            for idx, keyword in enumerate(keywords):
                status_text.markdown(f"### 🔍 현재 검색 중: **[{keyword}]**")
                progress_bar.progress((idx) / len(keywords))

                driver.get("https://map.naver.com/v5/search")
                
                # ★ 1. 검색창이 뜰 때까지 스마트하게 기다림
                try:
                    search_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input.input_search")))
                    time.sleep(1) # 입력 전 잠깐 대기
                    search_box.clear()
                    search_box.send_keys(keyword)
                    search_box.send_keys(Keys.ENTER)
                except Exception as e:
                    st.error(f"검색창을 찾을 수 없습니다. 네이버가 접속을 차단했을 수 있습니다.")
                    st.image(driver.get_screenshot_as_png(), caption='현재 화면 캡처')
                    raise e

                # ★ 2. iframe(결과창)이 생길 때까지 스마트하게 기다림 + 입장
                try:
                    wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "searchIframe")))
                except Exception as e:
                    st.warning(f"검색 결과 상자(searchIframe) 진입 실패. 스크린샷을 확인하세요.")
                    # iframe 진입 실패 시, 메인 화면을 찍어서 보여줌
                    st.image(driver.get_screenshot_as_png(), caption='에러 발생 시 화면')
                    raise e

                # 스크롤 내리기
                while True:
                    stores = driver.find_elements(By.CSS_SELECTOR, ".place_bluelink")
                    if len(stores) >= max_rank:
                        break
                    
                    if len(stores) > 0:
                        last_store = stores[-1]
                        driver.execute_script("arguments[0].scrollIntoView(true);", last_store)
                        time.sleep(1.5)
                    else:
                        # 가게가 하나도 안 보이면 로딩 대기
                        time.sleep(2)
                        
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
            st.error(f"오류가 발생했습니다: {e}")
            # ★ 에러가 나면 현재 화면을 사진 찍어서 보여줌 (디버깅용)
            if driver:
                st.image(driver.get_screenshot_as_png(), caption='오류 발생 직전 화면')
                driver.quit()