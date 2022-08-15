"""
    달러 인덱스가 올라가면 유가는 내려가고 유가가 내려가면 원달러 환율도 내려가는 흐름을 보인다.
"""
from locale import currency
import requests
import sys
import time, datetime
from bs4 import BeautifulSoup as bs
import pandas as pd

sys.path.append("/home/ubuntu/etlers/pysrc/pycom")

# import send_slack_message as SSM
# import common_util as CU

url_index = "https://kr.investing.com/currencies/us-dollar-index"
url_currency = "https://kr.investing.com/currencies/usd-krw"
url_kodex = "https://finance.naver.com/"

line_len = 70


# Preday Currency
now_dt = datetime.datetime.now().strftime("%Y.%m.%d")

url_usd_krw = "https://finance.naver.com//marketindex/exchangeDailyQuote.naver?marketindexCd=FX_USDKRW"
headers = {
    "referer" : url_usd_krw,    
    "user-agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36" 
}
url = url_usd_krw
res = requests.get(url=url, headers=headers)
df_data = pd.read_html(res.text)[0]
preday_currency = df_data[df_data["날짜"]["날짜"] < now_dt]["매매기준율"].head(1)["매매기준율"].unique()[0]


def get_soup(url):
    response = requests.get( url, headers={"User-agent": "Mozilla/5.0"} )
    soup = bs(response.text, 'html.parser')

    return soup


def make_usd_index():
    soup = get_soup(url_index)

    historical_usd_idx = soup.find("div",{"class":"clear overviewDataTable overviewDataTableWithTooltip"})

    if historical_usd_idx is None: return -1

    idx = 0
    dict_usd_idx = {}
    for row in historical_usd_idx:
        row_string = str(row).strip()
        if len(row_string) == 0: continue
        idx += 1
        temp = str(row_string.split('<span class="float_lang_base_1">')[1:]).replace("['","")
        list_temp = temp.replace("</span><span class=","").split('"float_lang_base_2 bold">')
        dict_usd_idx[idx] = [list_temp[0].replace(" ",""), list_temp[1].replace("</span></div>']","")]
    
    return dict_usd_idx


# Now Currency & 52 weeks average
def make_usd_krw():
    soup = get_soup(url_currency)

    current_usd_krw = soup.find("div",{"class":"instrument-price_instrument-price__3uw25 flex items-end flex-wrap font-bold"})
    current_usd_krw = float(str(current_usd_krw).split("instrument-price-last")[1].split("</span>")[0].replace('">','').replace(",",""))
    
    dict_usd_krw = {}
    
    idx = 0
    dict_usd_krw[idx] = current_usd_krw
    
    currency_range = soup.find("div",{"class":"mb-5 bg-background-surface border-b-2 pb-5 instrumentOverview_overview-section__2hN4A"})
    currency_range = str(currency_range).split("52주 변동폭")[1].split("1년 변동률")[0]
    list_range = currency_range.split("<span>")
    
    for val in list_range:
        try:
            num_value = float(val.replace(",","").replace("</span>",""))
            idx += 1
            dict_usd_krw[idx] = num_value
        except:
            pass
    
    return dict_usd_krw


print("#" * 50)
print("# Index - [Real Time VS Rate] Run Time")
print("#" * 50)

idx = 0
while True:
    now_dtm = datetime.datetime.now()
    run_dt = now_dtm.strftime("%Y%m%d")
    run_dtm = now_dtm.strftime("%Y-%m-%d %H:%M:%S")

    # USD Index 52w Average
    try:
        dict_usd_idx = make_usd_index()
        dict_usd_krw = make_usd_krw()
        
        year_avg_idx = (float(dict_usd_idx[10][1].split(" - ")[0].replace(",","")) + float(dict_usd_idx[10][1].split(" - ")[1].replace(",",""))) / 2
        # Now Index
        cur_idx = float(dict_usd_idx[4][1].replace(",",""))
        # USD KRW 52w Average
        year_avg_cur = (dict_usd_krw[1] + dict_usd_krw[2]) / 2
        # Now Currency
        now_cur = dict_usd_krw[0]
        # Dollar Gap Rate
        # usd_gap_rate = cur_idx / now_cur * 100
        # Dollar Gap Rate - 52w
        year_avg_usd_gap_rate = year_avg_idx / year_avg_cur * 100
        # Proper USD KRW
        
        proper_cur = round(cur_idx / year_avg_usd_gap_rate * 100, 2)
        now_rate = round((now_cur / proper_cur) * 100, 2)
        preday_rate = round((now_cur / preday_currency) * 100, 2)
        now_cur = '{:.2f}'.format(round(now_cur, 2))
        now_rate = '{:.2f}'.format(round(now_rate, 2))
        preday_rate = '{:.2f}'.format(round(preday_rate, 2))
        preday_gap = '{:.2f}'.format(round(float(now_cur) - float(preday_currency), 2))
        
        proper_cur = '{:.2f}'.format(round(cur_idx / year_avg_usd_gap_rate * 100, 2))
        result = f" {proper_cur} [{now_cur} {now_rate}% {preday_gap} {preday_rate}%] [{run_dtm.split(' ')[1]}]"
        print(result)
    except Exception as e:
        print(e)
    
    time.sleep(60)
