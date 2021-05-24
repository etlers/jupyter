import pandas as pd
import time
import requests
from bs4 import BeautifulSoup as bs
import send_slack_message as ssm

def except_word(headline):
    result_tf = False

    list_word = [
        "이혼", "결혼" "부동산", "LH", "한국주택공사", "분양", "전세", "월세", "전월세", "민간임대", "공공임대" ,"다주택", 
        "사망", "산재", "상품권", "쿠폰", "유니폼", "아파트", "할인", "국토부"
    ]
    for word in list_word:
        if word in headline:
            result_tf = True
            break

    return result_tf

def replace_word(word):
    list_remove = [
        '<span class="cluster_head_sub_topic', "</span>", "</a>", "</div>", "…", "\'"
    ]
    for val in list_remove:
        word = word.replace(val, "")
    word = word.replace("&amp;","&").replace("銀","은행").replace("▲","").replace("&gt;",">").replace("&lt;","<")
    word = word.replace("&eq;","=")

    return word

list_filtered = []

def get_news():
    base_url = f"https://news.naver.com/main/main.nhn?mode=LSD&mid=shm&sid1=101"
    response = requests.get( base_url, headers={"User-agent": "Mozilla/5.0"} )
    soup = bs(response.text, 'html.parser')
    list_div_class = [
        "_persist",
        "section_body",
    ]
    list_check_tag = [
        '<div class="cluster_text_lede">',
        '<span class="cluster_head_sub_topic">',
        '<a class="cluster_thumb_link nclicks(cls_eco.clsart)"',
        '<a class="cluster_text_headline nclicks(cls_eco.clsart)"',
    ]

    for div_class in list_div_class:
        list_news = str(soup.findAll("div", {"class": div_class})).split('\n')
        for row in list_news:
            if except_word(row): continue
            for tag in list_check_tag:
                if tag in row:
                    filtered_row = replace_word(row.replace(tag,""))
                    try:
                        filtered_row = filtered_row.split('">')[1]
                    except:
                        pass
                    filtered_row = filtered_row.strip()
                    if len(filtered_row) == 0: continue
                    if (filtered_row[:1] == '"' or filtered_row[:1] == '“'):
                        filtered_row = filtered_row[1:]
                    list_filtered.append("- " + filtered_row)
          
for idx in range(5):
    get_news()
    time.sleep(10)
    
list_filtered = list(set(list_filtered))
list_filtered = sorted(list_filtered)
df_news = pd.DataFrame(list_filtered, columns=["헤드라인"])

msg = ""
for row in list_filtered:
    msg += row + "\n"

# 최종 슬랙으로 뉴스 헤드라인 던지기
ssm.send_message_to_slack(msg)