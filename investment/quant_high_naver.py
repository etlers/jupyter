import pandas as pd
import requests
import lxml.html as lh
from bs4 import BeautifulSoup as bs
import time
import sys
import yaml

sys.path.append("C:/Users/etlers/Documents/project/python/common")

import date_util as DU
import conn_db as DB
import common_util as CU


# 환경변수 추출
with open('./config/quant_high.yaml') as stream:
    try:
        dict_dt = yaml.safe_load(stream)
        url_param = dict_dt['url_param']
        query_param = dict_dt['query_param']
    except yaml.YAMLError as exc:
        print(exc)

# 추출할 URL
kospi_url = url_param["kospi_url"]
kosdak_url = url_param["kosdak_url"]

# 조건 데이터 추출쿼리 및 변수
from_rt = query_param["from_rt"]
to_rt = query_param["to_rt"]
from_price = query_param["from_price"]
to_price = query_param["to_price"]
extract_qry = f"""
WITH T1 AS (
SELECT DEAL_DTM
     , JONGMOK_NM
     , UP_RT
     , NOW_PRICE
     , NOW_AMOUNT
     , LAG(NOW_AMOUNT, 1) OVER(PARTITION BY JONGMOK_NM ORDER BY DEAL_DTM) AS PRE_AMOUNT
  FROM quant_high
 WHERE 1 = 1
   AND PRE_VS_RT BETWEEN {from_rt} AND {to_rt}
   AND NOW_PRICE BETWEEN {from_price} AND {to_price}
),
T2 AS (
SELECT MAX(DEAL_DTM) AS DEAL_DTM
  FROM quant_high
)
SELECT JONGMOK_NM
     , UP_RT
     , NOW_PRICE
     , GAP_AMOUNT
     , UP_AMOUNT_RT
  FROM (SELECT JONGMOK_NM
		       , UP_RT
		       , NOW_PRICE
		       , NOW_AMOUNT - PRE_AMOUNT AS GAP_AMOUNT
		       , CAST(FLOOR(ROUND((NOW_AMOUNT - PRE_AMOUNT) / PRE_AMOUNT, 2) * 100) AS INT) AS UP_AMOUNT_RT
		    FROM T2
		   INNER JOIN T1
		      ON T1.DEAL_DTM = T2.DEAL_DTM) TT
 WHERE UP_AMOUNT_RT > 10
 ORDER BY UP_AMOUNT_RT DESC
"""

# 종목 명칭, 코드 딕셔너리
dict_jongmok = CU.make_dic_jongmok_list()
# 진행 상태.
# 1: 추출, 2: 매수, 3: 매도, 9: 종료
dict_status = {
    "status": 1
}
# 기본 금액
base_amount = dict_dt["base_amount"]


# 데이터 크롤링
def get_qunat_high(base_url, list_deal_amount):
    response = requests.get( base_url, headers={"User-agent": "Mozilla/5.0"} )
    soup = bs(response.text, 'html.parser')
    list_quant_high = str(soup.findAll("table", {"class": "type_2"})).split('\n')

    start_tf = False
    idx = 0
    list_jongmok = []

    for val_string in list_quant_high:
        strip_val = val_string.strip()
        if '<td class="no">' in strip_val:
            idx = 0
            if (len(list_jongmok) > 0):
                if (list_jongmok[2].count(' ') == 0 and list_jongmok[4] > 0):
                    list_deal_amount.append(list_jongmok)
            list_jongmok = []
            start_tf = True
        if strip_val[:2] == '</': continue
        if start_tf == False: continue
        if '<td class="number">' == strip_val: continue

        idx += 1

        if idx == 3:
            strip_val = strip_val.split(">")[2].split("<")[0]
        elif idx == 5:
            if 'nv01' in strip_val:
                num_sign = -1
            else:
                num_sign = 1
            continue
        elif idx == 6:
            try:
                strip_val = str(int(strip_val.replace(",","")) * num_sign)
            except:
                strip_val = "0"
        else:
            try:
                strip_val = strip_val.split(">")[1].split("<")[0]
                if len(strip_val) == 0: continue
            except:
                pass

        try:
            if strip_val.count(".") > 0:
                strip_val = float(strip_val.replace(",",""))
            else:
                strip_val = int(strip_val.replace(",",""))
        except:
            strip_val = strip_val.replace("+", "")

        list_jongmok.append(strip_val)

    # 최종 저장을 위한 리스트로 저장
    if (list_jongmok[2].count(' ') == 0 and list_jongmok[4] > 0):
        list_deal_amount.append(list_jongmok)

    return list_deal_amount


# 데이터 크롤링 적재
def get_save_data():
    list_result = []
    # KOSPI Data
    list_result = get_qunat_high(kospi_url, list_result)
    # KOSDAK Data
    list_result = get_qunat_high(kosdak_url, list_result)
    # 데이터가 없으면 빠져나감
    if len(list_result) == 0:
        return False
    # 데이터프레임 생성
    list_cols = ["RANK","UP_RT","JONGMOK_NM","NOW_PRICE","PRE_VS_RT","UP_DN_RT","BUY_PRICE","SELL_PRICE","NOW_AMOUNT","END_AMOUNT","PER"]
    df_quant = pd.DataFrame(list_result, columns=list_cols)    
    df_quant["DEAL_DTM"] = DU.get_now_datetime_string()
    df_quant = df_quant[["DEAL_DTM","JONGMOK_NM","UP_RT","NOW_AMOUNT","END_AMOUNT","NOW_PRICE","BUY_PRICE","SELL_PRICE","PRE_VS_RT","UP_DN_RT"]]
    df_quant["UP_DN_RT"] = df_quant["UP_DN_RT"].str.replace("%","").astype(float)
    df_quant["UP_RT"] = df_quant["UP_RT"].astype(int)
    # 데이터프레임 디비로 저장
    DB.transaction_data_df(df_quant, "quant_high")

    return True


# 매도됐는지 확인
def check_sell_stock():
    # 매도까지 됐다면 다시 데이터 추출할 수 있는 상태로 변경
    dict_status["status"] = 1


# 종목 추출 & 매수, 매도 처리
def process_func():

    # 매수
    def buy_stocks(jongmok_cd, now_price):
        # 시장가 매수를 위한 상한가 10원 단위로 계산한 기준 금액
        base_price = int((now_price * 1.3) / 10) * 10
        # 계산한 매수량
        buy_ea = int(base_amount / base_price)
        dict_status["status"] = 2

    # 구매한 금액, 수량
    def get_buy_price():
        buy_ea = 87
        buy_price = 11405

        return buy_price, buy_ea

    # 매도
    def sell_stocks(jongmok_cd, sell_price, sell_ea):
        dict_status["status"] = 3

    
    # 추출한 데이터
    list_extract_data = DB.query_data(extract_qry)
    # 없으면 빠져나감
    if len(list_extract_data) == 0:
        return False
    # 존재하면 처리로 들어감
    for list_data in list_extract_data:
        try:
            now_price = list_data[2]
            jongmok_nm = list_data[0]
            jongmok_cd = dict_jongmok[jongmok_nm]
            # 종목코드가 존재하는지 확인
            print(jongmok_nm, jongmok_cd, now_price)
            # 조건에 맞으면 구매
            buy_stocks(jongmok_cd, now_price)
            # 구매한 금액 추출
            base_price, sell_ea = get_buy_price()
            # 구매한 금액에 3% 추가해서 매도
            sell_price = int((base_price * 1.03) / 10) * 10
            # 매도
            sell_stocks(jongmok_cd, sell_price, sell_ea)
            break
        except:
            pass

    # 매도까지 됐는지 확인
    while True:
        if check_sell_stock():
            break
        else:
            time.sleep(1)

    return True


# 실행
def execute():    
    # process_func()
    # return 1

    # 최초 시작전 이전 데이터는 모두 지움. 당일 데이터로만 함
    qry = """
        truncate table quant_high
    """
    DB.transaction_data(qry)

    idx = 0
    # 시간 동안 수행
    while True:
        # 종료상태면 빠져나감
        if dict_status["status"] == 9:
            break
        # 일시 추출
        now_dtm = DU.get_now_datetime_string()
        now_tm = now_dtm.split(" ")[1].replace(":","")
        # 최초 30초 쌓인 후의 데이터부터 시작
        if now_tm < "090010":
            print("Waiting:", now_dtm)
            time.sleep(1)
            continue
        # 10시까지만 수행
        elif now_tm > "093000":
            print("Finish!!")
            break
        
        # 데이터 크롤링 그리고 디비로 적재
        if get_save_data():
            pass
            # # 종목 추출
            # if process_func():
            #     # 15분 이상 남았으면 다시 시작
            #     if now_tm < "094500":
            #         continue
            #     # 아니면 마감
            #     else:
            #         dict_status["status"] = 9
        idx += 1
        # 9시 30분 전에는 5초단위
        if now_tm < "093000":
            print(idx, "Save & Waiting...")
            time.sleep(10)
        # 이후는 15초 단위
        else:
            print(idx, "Save & Waiting...")
            time.sleep(15)

    # 매도까지 됐는지 확인
    # while True:
    #     # 매도까지 됐다면 종료
    #     if check_sell_stock():
    #         break
    #     time.sleep(1)
    

if __name__ == "__main__":
    execute()