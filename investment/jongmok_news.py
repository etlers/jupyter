import pandas as pd
import requests, time
import lxml.html as lh
from bs4 import BeautifulSoup as bs
import os
import pymysql
from datetime import datetime, timedelta
from requests.models import Response
from selenium import webdriver

selenium_dir = "../../chromedriver/"
driver = webdriver.Chrome(selenium_dir + "chromedriver.exe")

positive_word = [
    "상장", "믿고", "믿다", "믿음", "투자", "협업", "진출", "인수", "강세", "투자 유치"
]

def save_data(jongmok_cd, jongmok_nm, list_jongmok_news):
    # MySQL Connection 연결
    conn = pymysql.connect(
        host='localhost', 
        user='etlers', 
        password='wndyd', 
        db='stocks', 
        charset='utf8'
    )
    curs = conn.cursor(pymysql.cursors.DictCursor)

    for list_row in list_jongmok_news:
        qry = """
            INSERT INTO jongmok_news
                (NEWS_DT, JONGMOK_CD, JONGMOK_NM, HEAD_LINE, POS_CNT, NEG_CNT)
            VALUES (
            '%s',
            '%s',
            '%s',
            '%s',
            '%s',
            '%s'
            )
            ON DUPLICATE KEY UPDATE
            POS_CNT = 0
        """ % (list_row[1], jongmok_cd, jongmok_nm, list_row[0], 0, 0)

        curs.execute(qry)
    conn.commit()

def execute(jongmok_cd, jongmok_nm):
    dict_jongmok_news = {}
    base_url = f"https://finance.naver.com/item/news_news.nhn?code={jongmok_cd}&page=&sm=title_entity_id.basic&clusterId="
    driver.get(base_url)
    # driver.switch_to.frame('news')
    response = driver.page_source
    list_news = response.split('\n')        
    list_jongmok_news = []
    list_temp = []                
    for row in list_news:
        if ('<a href="/item/news_read.nhn?article_id' in row or '<td class="date">' in row):
            try:
                list_temp.append(row.split('"_top">')[1].replace("</a>", "").replace('<span class="ico_reply"></span>', "").replace("'", "''"))
                list_jongmok_news.append(list_temp)
            except:
                list_temp.append(row.replace("\t","").replace('<td class="date">',"").replace("</td>","").strip().split(" ")[0])
                list_jongmok_news.append(list_temp)
                list_temp = []
    dict_jongmok_news[jongmok_cd] = list_jongmok_news    
    save_data(jongmok_cd, jongmok_nm, list_jongmok_news)


if __name__ == "__main__":
    df_jongmok = pd.read_csv("./csv/jongmok_list.csv", encoding="CP949")

    try:
        df_jongmok = df_jongmok[["단축코드", "한글 종목약명"]]
        df_jongmok = df_jongmok.rename(columns = {'단축코드': 'JONGMOK_CD', '한글 종목약명': 'JONGMOK_NM'}, inplace = False)
    except:
        pass

    for index, row in df_jongmok.iterrows():
        print(row["JONGMOK_CD"], row["JONGMOK_NM"])
        execute(row["JONGMOK_CD"], row["JONGMOK_NM"])
    driver.close()