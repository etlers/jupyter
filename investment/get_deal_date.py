"""
    삼성전자 종목으로 최종 및 이전 일자 추출
"""
import requests
from bs4 import BeautifulSoup as bs

def execute(jongmok_cd):
    base_url = f"https://finance.naver.com/item/sise_day.nhn?code={jongmok_cd}"
    response = requests.get( base_url, headers={"User-agent": "Mozilla/5.0"} )
    soup = bs(response.text, 'html.parser')
    list_day = str(soup.findAll("table", {"class": "type2"})).split('\n')
    idx = 0
    file_yaml = open("./config/jongmok.yaml", 'w')
    
    for row in list_day:
        if '<span class="tah p10 gray03">' in row:
            idx += 1
            if idx > 2: break
            row = row.split('<span class="tah p10 gray03">')[1].replace('</span></td>','')
            if idx == 1:
                file_yaml.write("NOW_DT: " + row + "\n")
            elif idx == 2:
                file_yaml.write("PRE_DT: " + row + "\n")
    file_yaml.write("WEBHOOK_URL: https://hooks.slack.com/services/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")
    file_yaml.close()

if __name__ == "__main__":
    execute("005930")