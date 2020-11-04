# Do what

模擬一個生產線上的機械手臂的生產過程產生的資料流

情境:

工作人員將棧板推至固定位置後(上面放了待加工的料件), 拿工單掃描條碼後,

手臂開始去搜尋相對應的料件(搜尋時間)

之後開始進行生產加工(加工時間)


# Environment

Python3.6+

pip install -r requirements.txt


# How to use

開啟 3 個 Terminal

Terminal 1

    docker-compose up

**確定 Step1 DB 環境初始化完成後再繼續底下的動作**

Terminal 2

    venv/bin/python simulate_production.py

Terminal 3

    venv/bin/python simulate_event_trigger.py 
