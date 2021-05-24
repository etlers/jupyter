"""
    투자자별 매매동향
     - https://finance.naver.com/sise/investorDealTrendDay.nhn?bizdate=20210520&sosok=
"""
import pandas as pd
import requests
import html5lib
import lxml.html as lh
from bs4 import BeautifulSoup as bs
import pymysql
import datetime, yaml

with open('./config/jongmok.yaml') as stream:
    try:
        dict_dt = yaml.safe_load(stream)
        now_dt = dict_dt['NOW_DT']
        pre_dt = dict_dt['PRE_DT']
    except yaml.YAMLError as exc:
        print(exc)

conn = pymysql.connect(
    host = '127.0.0.1', # host name
    user = 'etlers', # user name
    password = 'wndyd', # password
    db = 'stocks', # db name
    charset = 'utf8'
)
curs = conn.cursor()

df_jongmok = pd.read_csv("./csv/jongmok_list.csv", encoding="CP949")

try:
    df_jongmok = df_jongmok[["단축코드", "한글 종목약명"]]
    df_jongmok = df_jongmok.rename(columns = {'단축코드': 'JONGMOK_CD', '한글 종목약명': 'JONGMOK_NM'}, inplace = False)
except:
    pass

list_day_invest_cols = [
    "날짜",
    "개인",
    "외국인",
    "기관계",
    "금융투자",
    "보험",
    "투신(사모)",
    "은행",
    "기타금융기관",
    "연기금등"
    "기타법인",
]

# 일자별 합계
def calc_day_sum(list_day):
    result_val = 0
    for val in list_day:
        try:
            int_val = int(val)
        except:
            int_val = 0
        result_val += int_val
    return result_val


def execute(sosok_cd):
    list_whole = []
    
    def save_data():
        # MySQL Connection 연결
        conn = pymysql.connect(
            host='localhost', 
            user='etlers', 
            password='wndyd', 
            db='stocks', 
            charset='utf8'
        )
        curs = conn.cursor(pymysql.cursors.DictCursor)

        for list_row in list_whole:
            day_sum = calc_day_sum(list_row)
            qry = f"""
                INSERT INTO day_invest
                    (DEAL_DT, DIV_CD, PRIVATE, FORGN, COMPANY, FINN_INVEST, INSURANCE, PRI_FUND, BANK, ETC_FINN, KIGEUM, ETC_COMP, DAY_SUM)
                VALUES (
                    '{list_row[0]}',
                    '{sosok_cd}',
                    {list_row[1]},
                    {list_row[2]},
                    {list_row[3]},
                    {list_row[4]},
                    {list_row[5]},
                    {list_row[6]},
                    {list_row[7]},
                    {list_row[8]},
                    {list_row[9]},
                    {list_row[10]},
                    {day_sum}
                )
                ON DUPLICATE KEY UPDATE
                    PRIVATE = {list_row[1]}, 
                    FORGN = {list_row[2]},
                    COMPANY = {list_row[3]},
                    FINN_INVEST = {list_row[4]},
                    INSURANCE = {list_row[5]},
                    PRI_FUND = {list_row[6]},
                    BANK = {list_row[7]},
                    ETC_FINN = {list_row[8]},
                    KIGEUM = {list_row[9]},
                    ETC_COMP = {list_row[10]},
                    DAY_SUM = {day_sum}
            """
            curs.execute(qry)
        conn.commit()


    list_day_invest = []
    param_dt = now_dt.replace(".","")
    base_url = f"https://finance.naver.com/sise/investorDealTrendDay.nhn?bizdate={param_dt}&sosok={sosok_cd}"
    # print(base_url)
    response = requests.get( base_url, headers={"User-agent": "Mozilla/5.0"} )
    soup = bs(response.text, 'html.parser')
    list_day_sum = str(soup.findAll("table", {"summary": "일자별 순매수에 관한 표 입니다."})).split('\n')
    for row in list_day_sum:
        if "<td class=" not in row: continue
        date_tf = False
        if "date2" in row:
            date_tf = True
            if len(list_day_invest) > 0:
                list_whole.append(list_day_invest)
            list_day_invest = []
        filtered_data = row.split(">")[1].replace("</td","").strip()
        if len(filtered_data) == 0: continue
        if date_tf:
            filtered_data = "20" + filtered_data
        list_day_invest.append(filtered_data.replace(",",""))
    list_whole.append(list_day_invest)
     
    save_data()

if __name__ == "__main__":
    # 코스피
    execute("01")
    # 코스닥
    execute("02")
    