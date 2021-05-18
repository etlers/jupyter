import pandas as pd
import requests
import html5lib
import lxml.html as lh
from bs4 import BeautifulSoup as bs
import pymysql
import datetime

# current date and time
now_dtm = datetime.datetime.now()
run_dt = now_dtm.strftime("%Y-%m-%d")

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


dict_whole = {}

def delete_today(qry):    
    try:
        curs.execute(qry)
    except:
        pass

    conn.commit()
    # conn.close()

def make_delete_qry():
    exec_str = """
        delete from jongmok_day 
         where deal_dt = 
    """
    exec_str += "'" + run_dt + "'"
    delete_today(exec_str)

    exec_str = """
        delete from jongmok_sum
         where deal_dt = 
    """
    exec_str += "'" + run_dt + "'"
    delete_today(exec_str)
    

def make_rslt(list_jongmok):
    for jongmok in list_jongmok:
        base_url = f"https://finance.naver.com/item/frgn.nhn?code={jongmok}&page=1&trader_day=5"
        print(base_url)
        response = requests.get( base_url, headers={"User-agent": "Mozilla/5.0"} )
        soup = bs(response.text, 'html.parser')
        list_sum = str(soup.findAll("table", {"summary": "거래원정보에 관한표이며 일자별 누적 정보를 제공합니다."})).split('\n')
        list_day = str(soup.findAll("table", {"summary": "외국인 기관 순매매 거래량에 관한표이며 날짜별로 정보를 제공합니다."})).split('\n')

        list_cols = ["div", "amount"]
        list_rslt = []

        def make_df(div, amount):
            list_vals.append(div)
            list_vals.append(get_value)
            list_rslt.append(list_vals)

        # 금액 추출
        def get_amount(in_param):
            string_rslt = in_param.replace('<td class="num bg01">', '')
            string_rslt = string_rslt.replace('<td class="num bg02">', '')
            string_rslt = string_rslt.replace('<span class="tah p11">', '')
            string_rslt = string_rslt.replace('<span class="tah p11 nv01">', '')
            string_rslt = string_rslt.replace('<span class="tah p11 red01">', '')
            string_rslt = string_rslt.replace('</span></td>', '')
            string_rslt = string_rslt.replace('<strong class="tah p11 nv01">', '').replace('<strong class="tah p11 red01">', '').replace('</strong>', '')
            string_rslt = string_rslt.replace("(","").replace(")","").replace(",","")

            return string_rslt

        # 매수
        buy_amount = 0
        # 매도
        sell_amount = 0
        list_whole = []
        # 
        dict_buy_sell = {}
        # 매수매도 추출
        for row in list_sum:
            if ("class=" not in row or "table" in row or 'class="bg01"' in row or 'class="bg02"' in row or 'class="bg04' in row or 'class="title' in row):
                continue
            try:
                get_value = int(get_amount(row))
                list_vals = []
                if "bg02" in row:
                    buy_amount += get_value
                elif "bg01" in row:
                    sell_amount += get_value   
                forgn_amount = get_value        
            except:
                pass

        dict_buy_sell["BUY"] = buy_amount
        dict_buy_sell["SELL"] = sell_amount
        dict_buy_sell["FORGN"] = forgn_amount
        list_whole.append((dict_buy_sell))

        idx = 0
        gap_idx = 0
        cprice_idx = 0
        skip_idx = 0
        dict_day_info = {}
        list_day_info = []
        for row in list_day:
            try:
                idx += 1
                row = row.strip()
                if ("table" in row or "<caption>" in row or "<tr" in row or "<th" in row):
                    continue
                row = row.replace("</tr>", "").replace("</td>", "").replace('<td class="num" width="67">', '').replace('</span>', '')
                row = row.replace('<span class="tah p11 nv01">','').replace('<span class="tah p11 red01">','')
                if len(row) > 0:
                    if "하락" in row:
                        next_idx = idx + 1
                    if 'class="tc"' in row:
                        if len(list_day_info) > 0:
                            dict_day_info[dt.replace(".","")] = list_day_info
                            list_day_info = []
                        dt = row.split('<span class="tah p10 gray03">')[1]
                        cprice_idx = idx + 1            
                    if cprice_idx == idx:
                        list_day_info.append(row.split(">")[1].replace(",",""))
                        gap_idx = idx + 1
                    elif gap_idx == idx:
                        list_day_info.append(int(row.replace(",","")) * -1)
                        skip_idx = idx + 4
                    else:
                        if ('img alt' in row or '<span class="tah p10 gray03">' in row): continue
                        row = row.replace("+", "").replace('<span class="tah p11">', '')
                        try:
                            row = row.split(">")[1]
                        except:
                            row
                        list_day_info.append(row.replace(",",""))
            except:
                break

        list_whole.append((dict_day_info))
        dict_whole[jongmok] = list_whole

def execute_list():    
    df_jongmok = pd.read_csv("./csv/jongmok_list.csv", encoding="CP949")

    try:
        df_jongmok = df_jongmok[["단축코드", "한글 종목약명"]]
        df_jongmok = df_jongmok.rename(columns = {'단축코드': 'JONGMOK_CD', '한글 종목약명': 'JONGMOK_NM'}, inplace = False)
    except:
        pass

    for jongmok_cd in list_jongmok:
        try:
            jongmok_nm = df_jongmok.loc[df_jongmok.JONGMOK_CD == jongmok_cd]["JONGMOK_NM"].values[0]
        except:
            jongmok_nm = ""
        
        if len(jongmok_nm) > 0:
            dict_val = dict_whole[jongmok_cd][0]
            exec_str = """
            insert into jongmok_sum (JONGMOK_CD, JONGMOK_NM, DEAL_DT, BUY_AMOUNT, SELL_AMOUNT, FORGN_AMOUNT)
            values (
                '%s',
                '%s',
                NOW(),
                cast('%s' as int),
                cast('%s' as int),
                cast('%s' as int))
            """ % (jongmok_cd, jongmok_nm, dict_val["BUY"], dict_val["SELL"], dict_val["FORGN"])
            try:
                curs.execute(exec_str)
            except:
                pass
            
            dict_val = dict_whole[jongmok_cd][1]
            for key, value in dict_val.items():
                exec_str = """
                    insert into jongmok_day (JONGMOK_CD, JONGMOK_NM, DEAL_DT, END_PRICE, VS_PREDAY, VS_PREDAY_RT, DEAL_AMOUNT, COMPANY_DEAL, FORGN_DEAL, FORGN_POSS, FORGN_POSS_RT)
                    values ("""
                exec_str += "'" + jongmok_cd + "', '" + jongmok_nm + "', '" + key + "',"
                for idx in range(len(value)):
                    if idx == 6:
                        exec_str += "'" + value[idx] + "',"
                    elif "." in value[idx]:
                        exec_str += "cast('" + value[idx].replace("%", "") + "' as float),"
                    else:
                        exec_str += "cast('" + value[idx].replace("%", "") + "' as int),"
                exec_str = exec_str[:len(exec_str)-1] + ")"
                try:
                    curs.execute(exec_str)
                except:
                    pass
        
    conn.commit()
    conn.close()

def execute():
    for index, row in df_jongmok.iterrows():
        jongmok_cd = row["JONGMOK_CD"]
        jongmok_nm = row["JONGMOK_NM"]
        print(jongmok_cd, jongmok_nm)
        
        if len(jongmok_nm) > 0:
            dict_val = dict_whole[jongmok_cd][0]
            exec_str = """
            insert into jongmok_sum (JONGMOK_CD, JONGMOK_NM, DEAL_DT, BUY_AMOUNT, SELL_AMOUNT, FORGN_AMOUNT)
            values (
                '%s',
                '%s',
                NOW(),
                cast('%s' as int),
                cast('%s' as int),
                cast('%s' as int))
            """ % (jongmok_cd, jongmok_nm, dict_val["BUY"], dict_val["SELL"], dict_val["FORGN"])
            try:
                curs.execute(exec_str)
            except:
                pass
            
            dict_val = dict_whole[jongmok_cd][1]
            for key, value in dict_val.items():
                exec_str = """
                    insert into jongmok_day (JONGMOK_CD, JONGMOK_NM, DEAL_DT, END_PRICE, VS_PREDAY, VS_PREDAY_RT, DEAL_AMOUNT, COMPANY_DEAL, FORGN_DEAL, FORGN_POSS, FORGN_POSS_RT)
                    values ("""
                exec_str += "'" + jongmok_cd + "', '" + jongmok_nm + "', '" + key + "',"
                for idx in range(len(value)):
                    if idx == 6:
                        exec_str += "'" + value[idx] + "',"
                    elif "." in value[idx]:
                        exec_str += "cast('" + value[idx].replace("%", "") + "' as float),"
                    else:
                        exec_str += "cast('" + value[idx].replace("%", "") + "' as int),"
                exec_str = exec_str[:len(exec_str)-1] + ")"
                try:
                    curs.execute(exec_str)
                except:
                    pass
        
    conn.commit()
    conn.close()    

if __name__ == "__main__":
    # 당일 데이터는 삭제
    make_delete_qry()
    # list_jongmok = ["005930", "035720", "122630"]
    list_jongmok = []
    for index, row in df_jongmok.iterrows():
        list_jongmok.append(row["JONGMOK_CD"])
    # 데이터 추출 생성
    make_rslt(list_jongmok)
    # DB로 결과 저장
    execute()