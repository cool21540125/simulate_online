"""
TonyChou, 2018/06/21

模擬生產數據
- 每隔幾秒鐘, 產生一筆 資料紀錄
    - 壓力資料 (data_pressure)

- 隨機模擬(此程式 依機率隨機模擬 狀態, 燈號 變化)
    - 狀態資料 (data_status)
    - 燈號資料 (data_towerlight)

- 等待事件發生 (使用 simulate_event_trigger.py 來產生資料)
    - 工單資料 (work_orders)
    - 每筆工單資料內, 皆會有 1~N筆 工單明細資料 (products)
    - 警報資料 (data_alarm)
        - 機台運作過程中, 可能發生一些外界因素, 導致機台停機 or 其他, 發生這些事件時, 機台會拋出 警報資料

參數:
    light_r          : int                  前一筆 紅燈 燈號
    light_y          : int                  前一筆 黃燈 燈號
    light_g          : int                  前一筆 綠燈 燈號
    pressure         : float                目前機械手臂壓力
    chg              : float                改變狀態的機率
    pressure_limit   : int                  機械手臂壓力最大合理值
    tran             : bool                 壓力改變的反轉值(流程使用)
    conn             : {}                   資料庫連線
"""
import threading
import pymysql
from datetime import datetime
import random
from queue import Queue
from pymysql import err
import redis

DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "1qaz@WSX",
    "db": "demo_db",
    "port": 53306,
    "charset": "utf8mb4",
}
REDIS_CONFIG = {"host": "localhost", "port": 56379, "db": 0, "decode_responses": True}

PRESSURE_LIMIT = 20
CHG = 0.2
MAX_POOL_SIZE = 3

pressure = 0
tran = True
v0_status = ""
light_r = 0
light_y = 0
light_g = 1

POOL = Queue(maxsize=MAX_POOL_SIZE)


# 程式開始 ******************************************************


def h_pressure(v):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO `data_pressure` (`src`, `dt`, `v`) VALUES ('toshiba001', %s, %s)",
        (
            datetime.now(),
            v,
        ),
    )
    conn.commit()
    return_conn(conn)


def h_status(v):
    global v0_status
    if v != v0_status:
        conn = get_conn()
        c = conn.cursor()
        c.execute(
            "INSERT INTO `data_status` (`src`, `dt`, `status`) VALUES ('toshiba001', %s, %s)",
            (
                datetime.now(),
                v,
            ),
        )
        conn.commit()
        return_conn(conn)
    v0_status = v


def h1_towerlight(v):
    global light_r
    if v != light_r and v != -1:
        conn = get_conn()
        c = conn.cursor()
        c.execute(
            "INSERT INTO `data_towerlight` (`src`, `kind`, `dt`, `v`) VALUES ('toshiba001', 'red', %(dt)s, %(v)s)",
            {"dt": datetime.now(), "v": v},
        )
        conn.commit()
        return_conn(conn)
    light_r = v


def h2_towerlight(v):
    global light_y
    if v != light_y and v != -1:
        conn = get_conn()
        c = conn.cursor()
        c.execute(
            "INSERT INTO `data_towerlight` (`src`, `kind`, `dt`, `v`) VALUES ('toshiba001', 'yellow', %(dt)s, %(v)s)",
            {"dt": datetime.now(), "v": v},
        )
        conn.commit()
        return_conn(conn)
    light_y = v


def h3_towerlight(v):
    global light_g
    if v != light_g and v != -1:
        conn = get_conn()
        c = conn.cursor()
        c.execute(
            "INSERT INTO `data_towerlight` (`src`, `kind`, `dt`, `v`) VALUES ('toshiba001', 'green', %(dt)s, %(v)s)",
            {"dt": datetime.now(), "v": v},
        )
        conn.commit()
        return_conn(conn)
    light_g = v


def h_alarm(alarms_ing):
    """
    input
        ex: alarms_ing = {'563', '991'}  # 表示在這個時間點, 有 '563' 及 '991' 的警報正在發生

    這邊邏輯有點複雜...
    尋找 Table : data_alarm, 看是不是有 未完結警報 及 正在發生警報
    在依照各自應有邏輯下去作處理(看應該要 insert 一筆到DB 還是去 update 資料庫的 dt_end 欄位)

    過去沒有 未結警報 : data_alarm 不存在 dt_end is NULL 的資料紀錄
    過去　有 未結警報 : data_alarm 　存在 dt_end is NULL 的資料記錄
    """
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT `alarm` FROM `data_alarm` WHERE `dt_end` IS NULL;")
    alarms_ed = c.fetchall()

    c.execute("SELECT `wo` FROM `work_orders` WHERE `dt_end` IS NULL;")
    wo_ing = c.fetchone()
    wo_string = ""

    if wo_ing:
        wo_string = "工單單號 : " + wo_ing[0] + " 生產中..."

    if len(alarms_ed) > 0 and len(alarms_ing) > 0:
        print(
            f"{wo_string} ; A: alarms_ing: {repr(alarms_ing)} ; alarms_ed: {repr(alarms_ed)}"
        )

        for uu in alarms_ed:
            if uu[0] not in alarms_ing:
                c.execute(
                    "UPDATE `data_alarm` SET `dt_end` = %(dt)s WHERE `dt_end` IS NULL AND `alarm` = %(alarm)s",
                    {"dt": datetime.now(), "alarm": uu[0]},
                )

        for ii in alarms_ing:
            if (ii,) not in alarms_ed:
                c.execute(
                    "INSERT INTO `data_alarm` (`src`, `dt_start`, `alarm`) VALUES ('toshiba001', %(dt)s, %(alarm)s)",
                    {"dt": datetime.now(), "alarm": ii},
                )

    elif len(alarms_ed) > 0 and len(alarms_ing) == 0:
        print(wo_string + " ; B: alarms_ed: " + repr(alarms_ed))
        c.execute(
            "UPDATE `data_alarm` SET `dt_end` = %(dt)s WHERE `dt_end` IS NULL",
            {"dt": datetime.now()},
        )

    elif len(alarms_ed) == 0 and len(alarms_ing) > 0:
        print(wo_string + " ; C: alarms_ing: " + repr(alarms_ing))
        for ii in alarms_ing:
            c.execute(
                "INSERT INTO `data_alarm` (`src`, `dt_start`, `alarm`) VALUES ('toshiba001', %(dt)s, %(alarm)s)",
                {"dt": datetime.now(), "alarm": ii},
            )

    else:
        print(wo_string + " ; D: 無警報發生~~" + datetime.now().strftime("%H:%m:%S"))

    conn.commit()
    return_conn(conn)


def set_interval(func, hdlr, sec):
    e = threading.Event()
    while not e.wait(sec):
        hdlr(func())


def d_alarm():
    alarms_ing = r.smembers("alarms")
    # print(alarms_ing)
    return alarms_ing


def d_pressure():
    # 回傳 ex: <class 'float'> 18.53

    global tran, pressure
    if tran:
        pressure += round(random.random() * 2, 2)
        if pressure > PRESSURE_LIMIT:
            tran = False
            pressure = PRESSURE_LIMIT
    else:
        pressure -= round(random.random() * 2, 2)
        if pressure < 0:
            tran = True
            pressure = 0
    return pressure


def d_status():
    # 回傳 ex : <class 'str'> 'down'

    if random.random() < CHG:
        return random.choice(status_list)
    else:
        return "run"


def d_towerlight():
    if random.random() < CHG:
        """
        一定機率的條件下(random.random() < CHG),
        燈號顏色會變  但因為個人偷懶(程式好寫)
        有可能上次是 1(亮), 此次達到改變的條件後(random.random() < CHG)
        改變後又為 1(亮), 則這種狀況不在此 function 處理
        """
        return random.choice([0, 1, 2])
    else:
        return -1


def init_table():
    global status_list
    conn = get_conn()
    c = conn.cursor()

    # 產品 dt_end 沒紀錄 -> 刪除
    c.execute("DELETE FROM `products` WHERE `dt_end` IS NULL;")
    conn.commit()

    # 工單 dt_end 沒紀錄 -> 刪除相關 products && wo
    c.execute("SELECT `wo` FROM `work_orders` WHERE `dt_end` IS NULL;")
    dead_wo = c.fetchall()
    if len(dead_wo) > 0:
        dead_wo = dead_wo[0][0]  # [(wo,)] 取第一個值 (即 wo)
        c.execute("DELETE FROM `products` WHERE `fk_wo` = %(wo)s", {"wo": dead_wo})
        conn.commit()
        c.execute("DELETE FROM `work_orders` WHERE `dt_end` IS NULL;")
        conn.commit()

    # 比對燈號是否正常
    c.execute("SELECT DISTINCT(`kind`) FROM `data_towerlight`;")
    lights = c.fetchall()
    if len(lights) < 3:
        c.execute("DELETE FROM `data_towerlight`;")
        conn.commit()

        c.execute(
            "INSERT INTO `data_towerlight` (`src`, `kind`, `dt`, `v`) VALUES ('toshiba001', 'red',    %(dt)s, %(v)s)",
            {"dt": datetime.now(), "v": light_r},
        )
        c.execute(
            "INSERT INTO `data_towerlight` (`src`, `kind`, `dt`, `v`) VALUES ('toshiba001', 'yellow', %(dt)s, %(v)s)",
            {"dt": datetime.now(), "v": light_y},
        )
        c.execute(
            "INSERT INTO `data_towerlight` (`src`, `kind`, `dt`, `v`) VALUES ('toshiba001', 'green',  %(dt)s, %(v)s)",
            {"dt": datetime.now(), "v": light_g},
        )
        conn.commit()

    # 初始化 警報資料
    r.delete("alarms")
    c.execute("DELETE FROM `data_alarm` WHERE `dt_end` IS NULL;")
    conn.commit()

    # 初始化 狀態清單 status_list
    c.execute('SELECT `code` FROM `status` WHERE `code` != "x";')
    query_list = c.fetchall()
    status_list = [s[0] for s in query_list]

    return_conn(conn)


def init_conn_poll():
    global r
    redis_pool = redis.ConnectionPool(**REDIS_CONFIG)
    r = redis.StrictRedis(connection_pool=redis_pool)

    for _ in range(0, MAX_POOL_SIZE):
        try:
            conn = pymysql.Connect(**DB_CONFIG)
            POOL.put(conn)
        except err.MySQLError as error:
            print(error)


def get_conn():
    conn = POOL.get(True)
    return conn


def return_conn(conn):
    return POOL.put(conn)


if __name__ == "__main__":
    """
    1. 建立連線, 初始化 Tables
    2. 每秒鐘有 機台資料 (data_status, data_towerlight) && 機械手臂壓力資料 (data_pressure)
    3. 聆聽警報事件, 處理 警報資料 (data_alarm)
    4. 聆聽刷工單事件, 處理 工單(work_orders) && 產品(products) 生產過程紀錄
    """
    # 1
    init_conn_poll()
    init_table()

    # 2
    p_mthread = threading.Thread(
        target=set_interval, args=(d_pressure, h_pressure, 5)
    )  # 壓力
    s_mthread = threading.Thread(
        target=set_interval, args=(d_status, h_status, 1)
    )  # 狀態
    t1_mthread = threading.Thread(
        target=set_interval, args=(d_towerlight, h1_towerlight, 1)
    )  # 燈號 red
    t2_mthread = threading.Thread(
        target=set_interval, args=(d_towerlight, h2_towerlight, 1)
    )  # 燈號 yellow
    t3_mthread = threading.Thread(
        target=set_interval, args=(d_towerlight, h3_towerlight, 1)
    )  # 燈號 green
    a_mthread = threading.Thread(target=set_interval, args=(d_alarm, h_alarm, 1))  # 警報
    #
    p_mthread.start()
    s_mthread.start()
    t1_mthread.start()
    t2_mthread.start()
    t3_mthread.start()
    a_mthread.start()
