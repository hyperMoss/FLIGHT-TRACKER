from bs4 import BeautifulSoup
from DrissionPage import WebPage, ChromiumOptions
from time import sleep
import time
import requests
import json
from datetime import datetime

def send_to_feishu(content, webhook_url):
    """发送消息到飞书机器人"""
    try:
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "msg_type": "text",
            "content": {
                "text": content
            }
        }
        response = requests.post(webhook_url, headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            print("✅ 消息已成功发送到飞书")
        else:
            print(f"❌ 发送到飞书失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 发送飞书消息时出错: {e}")

def format_flights_for_feishu(flights):
    """格式化航班信息为飞书消息"""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    message = f"🛫 最低价格航班信息 ({current_time})\n"
    message += "=" * 50 + "\n\n"
    
    for i, flight in enumerate(flights, 1):
        message += f"🏆 第{i}名 - 价格: {flight['price']}\n"
        message += f"✈️ 航空公司: {flight['airline']}\n"
        message += f"🛫 出发: {flight['departure_airport']} {flight['departure_time']}\n"
        message += f"🛬 到达: {flight['arrival_airport']} {flight['arrival_time']}\n"
        message += f"ℹ️ 航班信息: {flight['FlightInformation']}\n"
        message += "-" * 30 + "\n"
    
    return message

def FlightsPage(departurePlace, arrivePlace, departureDate, headless=True):
    # 配置无头浏览器
    if headless:
        co = ChromiumOptions()
        co.headless()  # 设置无头模式
        page = WebPage(chromium_options=co)
    else:
        page = WebPage()
    
    page.get('https://flights.ctrip.com/online/list/oneway-' + departurePlace + '-' + arrivePlace + '?depdate='+ departureDate + '&cabin=y_s_c_f&adult=1&child=0&infant=0')
    # 时间段筛选
    page('#filter_item_time').click()
    sleep(1)
    page("@@u_key=filter_toggle_entry@@u_remark=点击筛选项[FILTER_GROUP_TIME.DEPART/晚上 18~24点]").click()
    sleep(1)
    # 隐藏共享航班
    page('#filter_item_other').click()
    sleep(1)
    page("@@u_key=filter_toggle_entry@@u_remark=点击筛选项[FILTER_GROUP_OTHER.HIDE_SHARED_FLIGHTS/隐藏共享航班]").click()
    for i in range(4):
        sleep(3)
        page.scroll.to_bottom()
    sleep(1)
    soup = BeautifulSoup(page.html, "html.parser")
    page.quit()  # 关闭浏览器释放资源
    return soup

def AirlineNameDiv(FlightsDiv):
    return FlightsDiv.find_all("div",{"class":"airlineName"})

def AirlineNameDivFirst(FlightsDiv):
    return FlightsDiv.find_all("div",{"class":"airline-name"})

def GetDpDiv(FlightsDiv):
    return FlightsDiv.find("div",{"class":"depart-box"})

def GetArrDiv(FlightsDiv):
    return FlightsDiv.find("div",{"class":"arrive-box"})

def GetDpAirport(FlightsDiv):
    return GetDpDiv(FlightsDiv).find("div",{"class":"airport"}).text

def GetDpTime(FlightsDiv):
    return GetDpDiv(FlightsDiv).find("div",{"class":"time"}).text

def GetArrAirport(FlightsDiv):
    return GetArrDiv(FlightsDiv).find("div",{"class":"airport"}).text

def GetArrTime(FlightsDiv):
    return GetArrDiv(FlightsDiv).find("div",{"class":"time"}).text

def GetFlightInformation(FlightsDiv):
    return FlightsDiv.find("div",{"class":"transfer-info-group"}).text

def GetFlightPrice(FlightsDiv):
    return FlightsDiv.find("span",{"class":"price"}).text

def ReviseResult(FlightsDiv,airlineName):
    result={
    'airline': 'null',
    'departure_airport': 'null',
    'arrival_airport': 'null',
    'departure_time': 'null',
    'arrival_time': 'null',
    'FlightInformation':'null',
    'price': 'null'
    }
    result['airline'] = airlineName
    result['departure_airport']=GetDpAirport(FlightsDiv)
    result['arrival_airport']=GetArrAirport(FlightsDiv)
    result['departure_time']=GetDpTime(FlightsDiv)
    result['arrival_time']=GetArrTime(FlightsDiv)     
    result['FlightInformation']=GetFlightInformation(FlightsDiv)
    result['price']=GetFlightPrice(FlightsDiv)
    return result

def DataProcessing(FlightsDiv):   
    try:
        if len(AirlineNameDiv(FlightsDiv)) == 2:
            return ReviseResult(FlightsDiv, [AirlineNameDiv(FlightsDiv)[0].contents[0], AirlineNameDiv(FlightsDiv)[1].contents[0]])
        if len(AirlineNameDiv(FlightsDiv)) == 0:
            return ReviseResult(FlightsDiv, AirlineNameDivFirst(FlightsDiv)[0].text)
    except Exception as e:
        print(f"处理航班数据时出错: {e}")
        return None

def GetTopThreeFlights(allFlightsDiv):
    """获取价格最低的三个航班"""
    flights_data = []
    for FlightsDiv in allFlightsDiv[0:]:
        flight_info = DataProcessing(FlightsDiv)
        print(flight_info)
        if flight_info and flight_info['price'] != 'null':
            try:
                # 提取价格数字
                price_str = flight_info['price'].replace('¥', '').replace(',', '')
                flight_info['price_num'] = int(price_str)
                flights_data.append(flight_info)
            except ValueError:
                continue
    
    # 按价格排序，取前三个
    flights_data.sort(key=lambda x: x['price_num'])
    return flights_data[:3]

def DisplayFlights(flights, webhook_url=None):
    """格式化显示航班信息并推送到飞书"""
    print(f"\n=== 最低价格航班信息 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===")
    print("-" * 80)
    
    for i, flight in enumerate(flights, 1):
        print(f"第{i}名 - 价格: {flight['price']}")
        print(f"  航空公司: {flight['airline']}")
        print(f"  出发: {flight['departure_airport']} {flight['departure_time']}")
        print(f"  到达: {flight['arrival_airport']} {flight['arrival_time']}")
        print(f"  航班信息: {flight['FlightInformation']}")
        print("-" * 40)
    
    # 推送到飞书
    if webhook_url and flights:
        feishu_message = format_flights_for_feishu(flights)
        send_to_feishu(feishu_message, webhook_url)

def CrawlAndDisplay(webhook_url=None):
    """抓取并显示航班信息的主函数"""
    try:
        print("开始抓取航班信息...")
        soup = FlightsPage('sha', 'can', '2025-08-03', headless=False)
        all_flights = soup.find_all("div", {"class": "flight-box"})
        
        if len(all_flights) > 1:
            top_flights = GetTopThreeFlights(all_flights)
            if top_flights:
                DisplayFlights(top_flights, webhook_url)
            else:
                print("未找到有效的航班价格信息")
                if webhook_url:
                    send_to_feishu("⚠️ 未找到有效的航班价格信息", webhook_url)
        else:
            print("未找到航班信息")
            if webhook_url:
                send_to_feishu("⚠️ 未找到航班信息", webhook_url)
            
    except Exception as e:
        error_msg = f"抓取过程中出现错误: {e}"
        print(error_msg)
        if webhook_url:
            send_to_feishu(f"❌ {error_msg}", webhook_url)

def StartScheduledCrawling(interval_minutes=30, webhook_url=None):
    """启动定时抓取任务（使用内置time模块）"""
    print(f"启动定时抓取任务，间隔: {interval_minutes}分钟")
    if webhook_url:
        print("✅ 已配置飞书推送")
    
    while True:
        CrawlAndDisplay(webhook_url)
        print(f"等待 {interval_minutes} 分钟后进行下次抓取...")
        time.sleep(interval_minutes * 60)  # 转换为秒

if __name__ == "__main__":
    # 飞书机器人 webhook 地址
    FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/37da1252-cd91-4492-ac9b-d4f7fe56e6c3"
    
    # 启动定时抓取，每30分钟执行一次，并推送到飞书
    StartScheduledCrawling(15, FEISHU_WEBHOOK)
