from flask import Flask, render_template, request, redirect, url_for
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from apscheduler.schedulers.background import BackgroundScheduler
import time
import os
from flask_sqlalchemy import SQLAlchemy
from selenium_stealth import stealth
from datetime import datetime

# 크롬 옵션 설정
# Chrome 옵션을 생성하여 헤드리스 모드를 활성화합니다.
chrome_options = Options()
chrome_options.add_argument('--headless')  # 헤드리스 모드 활성화
chrome_options.add_argument('--disable-gpu')  # GPU 사용 비활성화 (옵션, 헤드리스 모드에서 권장됨)
chrome_options.add_argument('--no-sandbox')  # 샌드박스 모드 비활성화 (옵션)
chrome_options.add_argument('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36')  # 헤더 설정

prd_list_data = []
usrprd_list_data = []

prd_list = []
usrprd = {}

current_date = datetime.now().strftime('%Y%m%d')

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] =\
        'sqlite:///' + os.path.join(basedir, 'database.db')

db = SQLAlchemy(app)

class ScrapePrd(db.Model):
    __tablename__ = f'ScrapePrd_{current_date}'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    discount = db.Column(db.String, nullable=False)
    price = db.Column(db.String, nullable=False)
    link = db.Column(db.String, nullable=False)
    img = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f'{self.name} / {self.price}'

class UserPrd(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    discount = db.Column(db.String, nullable=False)
    price = db.Column(db.String, nullable=False)
    link = db.Column(db.String, nullable=False)
    img = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f'{self.name} / {self.price}'

def create_scrape_table():
    # 데이터베이스 테이블을 생성하는 함수
    with app.app_context():
        db.create_all()

def scroll_down(driver):
    # 스크롤을 반복하여 페이지 끝까지 스크롤하도록 합니다.
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

# 스크래핑 작업 수행
def scrape_data():
    create_scrape_table()

    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(3) # 로딩시까지 얼마나 기다릴지 설정

    # 클라우드 플레어 우회
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
        )
    url = "https://www.coupang.com/np/categories/185669?from=home_C1&traid=home_C1&trcid=10000331878"
    driver.get(url)

    # 스크롤 다운
    scroll_down(driver)

    # 스크롤이 완료된 후 페이지의 소스코드를 가져옵니다.
    page_source = driver.page_source

    # BeautifulSoup를 사용하여 HTML 파싱
    soup = BeautifulSoup(page_source, 'html.parser')

    # 원하는 요소를 선택하여 출력
    prd = soup.select('.renew-badge')
    for i in prd:
        discount = str(i.select_one('.discount-percentage'))
        prd_list.append({
            'name': i.select_one('.name').text.strip(),
            'discount': discount.replace('<span class="discount-percentage">','').replace('</span>',''),
            'price': i.select_one('.price-value').text.strip(),
            'link': 'https://www.coupang.com'+i.select_one('.baby-product-link').get('href'),
            'img': i.select_one('.image img').get('src')
        })

    for i in prd_list:
        with app.app_context():
            prd = ScrapePrd(name=i['name'], discount=i['discount'], price=i['price'], link=i['link'], img=i['img'])
            db.session.add(prd)
            db.session.commit()

    # 웹 드라이버 종료
    driver.quit()

    return prd_list_data

@app.route('/')
def home():
    current_date = datetime.now().strftime('%Y%m%d')

    prd_list_data = ScrapePrd.query.filter(ScrapePrd.__table__.name == f'ScrapePrd_{current_date}').all()
    usrprd_list_data = UserPrd.query.all()

    context = {
        'prd_list_data': prd_list_data,
        'usrprd_list_data': usrprd_list_data
    }

    return render_template('index.html', data=context)

@app.route('/userpick', methods=['POST'])
def userpick():
    create_scrape_table()

    # POST 요청에서 폼 데이터 처리
    userurl = request.form['userurl']

    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(3)

    # 헤드리스 차단 우회
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
        )
    url = userurl
    driver.get(url)

    # 스크롤 다운
    scroll_down(driver)

    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')
    prd = soup.select('.prod-atf-main')

    for i in prd:
        usrprd = {
            'name': i.select_one('.prod-buy-header__title').text.strip(),
            'discount':  i.select_one('.discount-rate').text.strip(),
            'price': i.select_one('.total-price strong').text.strip().replace('원',''),
            'link': userurl,
            'img': i.select_one('.prod-image__detail').get('src')
        }

    prd = UserPrd(name=usrprd['name'], discount=usrprd['discount'], price=usrprd['price'], link=usrprd['link'], img=usrprd['img'])
    db.session.add(prd)
    db.session.commit()

    driver.quit()

    return redirect(url_for('home'))

if __name__ == '__main__':
    scrape_data()
    # 스케줄러 생성
    scheduler = BackgroundScheduler()
    # 스케줄러에 스케줄 추가 (매일 한 번 실행)
    scheduler.add_job(scrape_data, 'interval', days=1)

    # 스케줄러 시작
    scheduler.start()

    # Flask 애플리케이션 실행
    app.run(debug=False)