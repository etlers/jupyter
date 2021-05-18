"""
    종목 일별 데이터 추출 적재
    python jongmok_day_sum.py --now_dt=2021.05.17 --pre_dt=2021.05.14
"""
import pandas as pd
import requests
import lxml.html as lh
from bs4 import BeautifulSoup as bs
import pymysql
import argparse
# from sqlalchemy import create_engine
from datetime import datetime, timedelta

# pymysql.install_as_MySQLdb()
# import MySQLdb

# engine = create_engine("mysql+mysqldb://etlers:"+"wndyd"+"@localhost/stocks", encoding='utf-8')
# conn = engine.connect()

# current date and time
now_dtm = datetime.now()
now_dt = now_dtm.strftime("%Y.%m.%d")
pre_dtm = now_dtm - timedelta(days=1)
pre_dt = pre_dtm.strftime("%Y.%m.%d")

list_dt = []

jongmok_day_sum = []
# 디비로 저장하기 위한 컬러명
jongmok_day_sum_cols = [
    "JONGMOK_CD", 
    "JONGMOK_NM",
    "PREDAY_RT",
    "DEAL_DT",
    "END_PRICE",
    "GAP",    
    "START_PRICE",
    "HIGH_PRICE",
    "LOW_PRICE",
    "DEAL_AMOUNT",
    "FORGN_POSS_RT",
    "COM_DEAL",
    "FORGN_DEAL",
]


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

    # Delete
    qry = """
        DELETE FROM jongmok_day_sum WHERE DEAL_DT = '%s'
    """ % (now_dt)
    curs.execute(qry)

    whole_string = ""
    for list_row in jongmok_day_sum:
        values_string = "("
        for cols in list_row:
            if type(cols) != str:
                values_string += "'" + str(cols) + "',"
            else:
                values_string += "'" + cols + "',"
        whole_string += values_string[:len(values_string)-1] + ")," + "\n"    
    
    # Multi Insert
    qry = """
        INSERT INTO jongmok_day_sum (JONGMOK_CD, JONGMOK_NM, PREDAY_RT, DEAL_DT, END_PRICE, GAP, START_PRICE, HIGH_PRICE, LOW_PRICE, DEAL_AMOUNT, FORGN_POSS_RT, COM_DEAL, FORGN_DEAL)
        values 
            %s
        """ % (whole_string[:len(whole_string)-2].replace("<td", now_dt))

    f = open("./qry/ins_qry.sql", 'w', encoding="utf-8-sig")
    f.write(qry)
    f.close()
    
    curs.execute(qry)
    conn.commit()


def execute(jongmok_cd, jongmok_nm):
    now_dt = list_dt[0]
    pre_dt = list_dt[1]
    dict_forgn_poss = {}
    dict_company_value = {}
    list_day_value = []

    def get_company_buy_sell(jongmok):
        base_url = f"https://finance.naver.com/item/frgn.nhn?code={jongmok}&page=1&trader_day=1"
        response = requests.get( base_url, headers={"User-agent": "Mozilla/5.0"} )
        soup = bs(response.text, 'html.parser')
        list_company = str(soup.findAll("table", {"summary": "거래원정보에 관한표이며 일자별 누적 정보를 제공합니다."})).split('\n')
        idx = 0
        list_amount = []        
        for row in list_company:
            print_tf = False
            if "num bg01" in row:
                print_tf = True
                sell_sign = -1
            elif "num bg02" in row:
                print_tf = True
                sell_sign = 1
            elif "<span class" in row:
                print_tf = True
            elif "title" in row:
                print_tf = True
            
            if print_tf:
                row = row.strip()
                row = row.replace('<td class="num bg01">', "").replace('<td class="num bg02">', "").replace('<span class="tah p11 nv01">', "")
                row = row.replace('<span class="tah p11">', "").replace('</span>', "").replace('<span class="tah p11 red01">', "")
                row = row.replace('</span>', "").replace(",", "").replace('</td>', "")
                if len(row) == 0: continue
                if "title" in row:
                    try:
                        company_nm = row.split(">")[2]
                    except:
                        company_nm = ""
                else:
                    idx += 1
                    list_amount.append(company_nm)
                    try:
                        list_amount.append(str(sell_sign * int(row)))
                    except:
                        list_amount.append("0")
                    dict_company_value[idx] = list_amount
                    list_amount = []        


    def get_up_down_percent(jongmok):
        base_url = f"https://finance.naver.com/item/sise.nhn?code={jongmok}"
        response = requests.get( base_url, headers={"User-agent": "Mozilla/5.0"} )
        soup = bs(response.text, 'html.parser')
        list_sum = str(soup.findAll("table", {"summary": "주요시세 정보에 관한표 입니다."})).split('\n')
        print_tf = False
        idx = 0
        for row in list_sum:
            if "등락률" in row:
                print_tf = True
            elif "전일가" in row:
                print_tf = False

            if print_tf:
                idx += 1
                if idx == 4:
                    try:
                        preday_rt = float(row.strip().replace("%", ""))
                    except:
                        preday_rt = 0
                    list_day_value.append(str(preday_rt))
        list_forgn = str(soup.findAll("table", {"summary": "외국인한도주식수 정보"})).split('\n')
        idx = 0
        if len(list_forgn) > 0:
            for row in list_forgn:
                if "td" in row :
                    idx += 1
                    dict_forgn_poss[idx] = row.replace('<td><em>', "").replace('</em></td>', "").replace("%", "").replace(",", "")
        else:
            for idx in range(3):
                idx += 1
                dict_forgn_poss[idx] = 0


    def get_sise_day(jongmok_cd):
        base_url = f"https://finance.naver.com/item/sise_day.nhn?code={jongmok_cd}"
        response = requests.get( base_url, headers={"User-agent": "Mozilla/5.0"} )
        soup = bs(response.text, 'html.parser')
        list_day = str(soup.findAll("table", {"class": "type2"})).split('\n')
        print_tf = False
        for row in list_day:
            if (now_dt in row):
                print_tf = True
            elif (pre_dt in row):
                print_tf = False
            if print_tf:
                row = row.replace('<td class="num">', "")
                row = row.replace('<span class="tah p11">', "")
                row = row.replace('</span>', "")
                row = row.replace('</td>', "")
                row = row.replace('<img alt=', "")
                row = row.replace(",", "")
                row = row.replace('"', "")
                row = row.strip()
                if ("</tr" in row or "<tr" in row or len(row.strip()) == 0):
                    pass
                else:
                    # 날짜, 종가, 증감, 전일비, 시가, 고가, 저가, 거래량
                    list_day_value.append(row.split(" ")[0])


    get_up_down_percent(jongmok_cd)
    get_sise_day(jongmok_cd)
    get_company_buy_sell(jongmok_cd)

    list_jongmok = []
    list_jongmok.append(jongmok_cd)
    list_jongmok.append(jongmok_nm)

    idx = 0
    for val in list_day_value:    
        if idx != 3:
            list_jongmok.append(val)
        idx += 1

    try:
        list_jongmok.append(dict_forgn_poss[3])
    except:
        list_jongmok.append("0")

    company_amount = 0
    forgn_amount = 0

    for key, listval in dict_company_value.items():
        if listval[0] == "외국계추정합":
            forgn_amount = listval[1].replace("(", "").replace(")", "")
        else:
            try:
                company_amount += int(listval[1])
            except:
                company_amount += 0
    list_jongmok.append(company_amount)
    list_jongmok.append(forgn_amount)

    if len(jongmok_day_sum_cols) == len(list_jongmok):
        jongmok_day_sum.append(list_jongmok)
    else:
        print(list_jongmok)
        # 등락이 없어 맞질 않음. 일자를 넣고 맞춰줌
        list_temp = []
        for idx in range(len(list_jongmok)):
            if idx == 3:
                list_temp.append(now_dt)
            elif idx == 5:
                list_temp.append(0)
                list_temp.append(list_jongmok[idx])
            else:
                list_temp.append(list_jongmok[idx])
        jongmok_day_sum.append(list_temp)
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--now_dt', type=str, default=None)
    parser.add_argument('--pre_dt', type=str, default=None)
    args = parser.parse_args()
    list_dt.append(args.now_dt)
    list_dt.append(args.pre_dt)

    if len(args.now_dt) != 10:
        print("No Now Date")

    df_jongmok = pd.read_csv("./csv/jongmok_list.csv", encoding="CP949")

    try:
        df_jongmok = df_jongmok[["단축코드", "한글 종목약명"]]
        df_jongmok = df_jongmok.rename(columns = {'단축코드': 'JONGMOK_CD', '한글 종목약명': 'JONGMOK_NM'}, inplace = False)
    except:
        pass

    now_dtm_start = datetime.now()
    # list_jongmok = []
    for index, row in df_jongmok.iterrows():
        print(row["JONGMOK_CD"], row["JONGMOK_NM"])
        execute(row["JONGMOK_CD"], row["JONGMOK_NM"])
    # execute("200580", "nonmae")
    # execute("035720", "kakao")
    # execute("138040", "nonmae")
    # 추출한 데이터가 존재하면 디비에 저장
    if len(jongmok_day_sum) > 0:
        save_data()
    
    now_dtm_end = datetime.now()
    print("#" * 50)
    print(now_dtm_start, now_dtm_end)
    print(now_dtm_end - now_dtm_start)
    print("#" * 50)
    # df_price_info = pd.DataFrame(jongmok_day_sum, columns=jongmok_day_sum_cols)
    # Update가 안되고 컬럼까지 변경되어 사용 불가. Insert만 됨
    # df_price_info.to_sql(name="jongmok_day_sum", con=engine, if_exists='replace', index=False)