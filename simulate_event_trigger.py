"""
TonyChou, 2018/06/25

模擬生產數據
1. 觸發 警報
    - 機台運作過程中, 可能發生一些外界因素, 導致機台停機 or 其他, 發生這些事件時, 機台會拋出 警報資料

2. 觸發 刷工單
    - 工單資料 (work_orders)
    - 每筆工單資料內, 皆會有 1~N筆 工單明細資料 (products)

    假設 5:08:30 開始模擬 881 警報事件, 持續 60 秒
    爾後 5:08:40 開始模擬 881 警報事件, 持續  5 秒
    則 881 警報事件會在 5:08:45 以後消失
    
NOTE:
    搜尋時間 && 加工時間, X~Gamma(a, b)
    X 為特定事件的等候時間
        a: 形狀母數
        b: 比例母數
    E(X) = ab
    Var(X) = ab^2
"""
import redis
import pymysql
from datetime import datetime
from queue import Queue
import time
import random
import numpy as np
import threading


REDIS_CONFIG = {"host": "localhost", "port": 56379, "db": 0, "decode_responses": True}

MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "1qaz@WSX",
    "db": "demo_db",
    "port": 53306,
    "charset": "utf8mb4",
}

MAX_POOL_SIZE = 30  # MySQL 連線數

POOL = Queue(maxsize=MAX_POOL_SIZE)


def get_conn():
    conn = POOL.get(True)
    return conn


def return_conn(conn):
    return POOL.put(conn)


def init_conn_poll():  # 初始化, 清空 Table...

    global r
    redis_pool = redis.ConnectionPool(**REDIS_CONFIG)
    r = redis.StrictRedis(connection_pool=redis_pool)

    for _ in range(0, MAX_POOL_SIZE):
        try:
            conn = pymysql.Connect(**MYSQL_CONFIG)
            POOL.put(conn)
        except Exception as err:
            print(err)


def qry_wo_list():  # 到 MySQL 找出所有的 工單單號
    conn = get_conn()
    c = conn.cursor()
    try:
        res = []
        c.execute("SELECT `wo` FROM `work_orders`;")
        qry = c.fetchall()
        for i in qry:
            res.append(i[0])
    except Exception as err:
        raise Exception(f"資料庫連線異常! qry_wo_list() 內發生錯誤: {err}")
    finally:
        return_conn(conn)
    return res


def qry_product_list():  # 到 MySQL 找出所有的 產品序號
    conn = get_conn()
    c = conn.cursor()
    try:
        product_list = []
        c.execute("SELECT `serial` FROM `products`;")
        qry = c.fetchall()
        for i in qry:
            product_list.append(i[0])
    except:
        raise Exception("資料庫連線異常! qry_products_list() 內發生錯誤")
    finally:
        return_conn(conn)
    return product_list


def simulate_alarm():  # 模擬 警報事件發生
    """
    1. 輸入 alarm 代碼 (立刻發生)
    2. 輸入 alarm 事件 持續幾秒　 合理範圍 [1,172800] (一秒鐘 ~ 兩天)
    3. 把模擬出來的警報資料, 丟到 redis 的 alarms set

    alarm發生的時間點 : 所有該輸入的都輸入完(且都合理)
    """

    def remove_alarm(code, alarm_last):  # alarm_last 秒後, 排除 alarm code 為 code 的 警報事件
        time.sleep(alarm_last)
        r.srem("alarms", code)

    # 1
    conn = get_conn()
    try:
        with conn.cursor() as c:
            while True:
                if c.execute("SELECT * FROM alarms;") == 0:
                    print("請先塞資料到 「alarms」 Table, (目前它都是空的)")

                else:
                    print("----- ↓↓↓ 警報代碼 請看下面 ↓↓↓ -----")
                    for i in c.fetchall():
                        print(i[0], " : ", i[1])
                    print("----- ↑↑↑ 警報代碼 請看上面 ↑↑↑ -----")
                    print()

                    code = input("輸入 警報代碼(數字):")
                    if code == "":
                        break

                    else:
                        if c.execute(f"SELECT 1 FROM `alarms` WHERE code={code}") == 0:
                            print()
                            print(f"*** 警報代碼無效 : {code} , 沒事發生 ***")
                            print()

                        else:
                            # 2
                            alarm_last = input("警報事件 持續幾秒. (直接按 Enter, 預設為 30 秒) : ")
                            alarm_last = "30" if alarm_last == "" else alarm_last

                            try:
                                alarm_last = int(alarm_last)  # input 字串 -> 整數
                                if 0 < alarm_last <= 172800:  # 限制最多只能模擬 2 天

                                    # 3 輸入的資料都合理後, 開始模擬警報發生
                                    r.sadd("alarms", code)
                                    threading.Thread(
                                        target=remove_alarm, args=(code, alarm_last)
                                    ).start()
                                    print()
                                    print(
                                        f"*** 開始模擬警報事件, 事件代碼: {code}, 持續 {alarm_last} 秒 ***"
                                    )
                                    print()

                                else:
                                    print()
                                    print("警報事件 發生持續時間超過 172800秒(2天) ***")
                                    print()

                            except Exception as err:
                                print()
                                print(f"持續時間非為整數")
                                print()

    except Exception as err:
        print(f"*** 其他錯誤 {err} ***")

    finally:
        return_conn(conn)


class Product:
    def __init__(self, woid):
        """
        初始化一件產品, 並隨機模擬該產品的相關欄位
        """
        self.name = "AAAA"
        self.id_utype = random.choice(self._init_fields("wo_utypes"))
        self.woid = woid
        self.serial = self._init_serial()
        self.dt_search = None
        self.dt_start = None
        self.dt_end = None

    def _init_fields(self, table):
        """
        依 table Name , 抓出所有 id 欄位, 並組成 list 回傳
        ex: return [1, 2, 3, 4]
        """
        conn = get_conn()
        c = conn.cursor()
        c.execute("select `id` from `" + table + "`;")
        res = c.fetchall()
        lst = [i[0] for i in res]

        conn.commit()
        return_conn(conn)
        return lst

    def _init_serial(self):
        """
        回傳唯一的一組 serial Number, 並將他組成 '0000001' (前面補滿0)
        ex: 現在已有 0000001, 0000002
            則回傳 0000003
        """
        i = 0
        while True:
            i += 1
            ser = "{0:07}".format(i)
            tmp = self.name + ser
            if tmp not in list_products:  # 名稱有重複的話, 序號 +1
                list_products.append(tmp)
                return tmp


class WorkOrder:
    def __init__(self, number_of_products):
        self._date = datetime.now()
        self.date = self._date.strftime("%Y%m%d")  # 工單 編單日期
        self.dt_start = None  # 工單 刷單時間
        self.dt_end = None  # 工單 結束生產時間
        self.wo = self._init_wo_serial()  # 工單 單號
        self.amt = number_of_products  # 工單內 產品數量
        self.products = []  # 工單內 產品明細清單
        self._init_products()

    def _init_products(self):  # 設定工單內的產品明細
        """
        隨機模擬此工單內, 有 1~12 個產品, 它們的明細 && 開始搜尋時間(dt_search), 開始加工時間(dt_start), 結束加工時間(dt_end)
        """
        for _ in range(0, self.amt):
            self.products.append(Product(self.wo))

    def _init_wo_serial(self):  # return <str> 工單單號
        """
        工單單號 名稱格式 「866_yyyymmdd<series>」  "866_" 是隨便取的工單分類名稱
        <series> 為 001, 002, 003, 代表這是當天的第幾張工單
        假設現在已有 001, 002, 003, 004
        則此函數會回傳 005
        """
        i = 0
        while True:
            i += 1
            ser = "{0:03}".format(i)
            tmp = "866_" + self.date + ser
            if tmp not in list_work_orders:  # 名稱有重複的話, 序號 +1
                self.serial = i  # 工單 當天的 流水號
                return tmp


def simulate_work_order():  # 模擬 刷工單事件發生
    """
    程式會模擬現場 刷工單 的事件, 開始進行生產
    同一段時間內, 只能有一個工單內的產品在生產...
    """

    def start_making_fake_data(wo):  # 開始模擬工單內的資料
        """
        隨著時間, 動態更新 工單 && 工單內產品 的生產明細時間
        """

        def producing_product(wo, i):  # 開始生產產品
            time.sleep(np.random.gamma(4, 3))  # sleep... 開始生產~生產完成 的時間

            # 紀錄 products 的 dt_end
            conn = get_conn()
            c = conn.cursor()
            c.execute(
                "UPDATE `products` SET `dt_end` = %(dt)s WHERE `serial` = %(serial)s AND `dt_end` IS NULL",
                {"dt": datetime.now(), "serial": wo.products[i].serial},
            )
            conn.commit()
            return_conn(conn)

            # 處理 工單 的 完成時間
            if wo.amt == i + 1:
                _conn = get_conn()
                c = _conn.cursor()
                c.execute(
                    "UPDATE `work_orders` SET `dt_end` = %(dt)s WHERE `wo` = %(wo_serial)s AND `dt_end` IS NULL",
                    {"wo_serial": wo.wo, "dt": datetime.now()},
                )
                _conn.commit()
                return_conn(_conn)

                # print('*** 工單模擬完畢. 工單代碼= ' + wo.wo + ', 產品數量 = ' + str(wo.amt) + ' ***')

        # 處理 刷工單 的 起始時間
        _conn = get_conn()
        c = _conn.cursor()
        c.execute(
            "INSERT INTO `work_orders` (`wo`, `fk_machine_code`, `dt_start`, `amt`) VALUES (%(wo)s, 'toshiba001', %(dt)s, %(amt)s)",
            {"wo": wo.wo, "dt": datetime.now(), "amt": wo.amt},
        )
        _conn.commit()
        return_conn(_conn)

        # 每隔一段時間, 模擬各個產品的 搜尋, 開始, 結束時間
        for i in range(wo.amt):
            time.sleep(random.randint(3, 5))  # sleep... 搜尋前準備時間
            dt_searching = datetime.now()  # 開始搜尋的時間點
            time.sleep(np.random.gamma(6, 3))  # sleep... 開始找~找到了 的時間
            dt_starting = datetime.now()  # 開始生產的時間點
            t = threading.Thread(
                target=producing_product, args=(wo, i)
            )  # 異步處理, 分離前一筆開始生產 && 下一筆開始尋找
            t.start()

            # 紀錄 products 的 dt_search 及 dt_start
            _conn = get_conn()
            c = _conn.cursor()
            c.execute(
                "INSERT INTO `products` (`serial`, `fk_wo`, `fk_machine_code`, `fk_utype_id`, `dt_search`, `dt_start`) VALUES (%(serial)s, %(wo)s, 'toshiba001', %(utype)s, %(dt_search)s, %(dt_start)s)",
                {
                    "serial": wo.products[i].serial,
                    "wo": wo.wo,
                    "utype": wo.products[i].id_utype,
                    "dt_search": dt_searching,
                    "dt_start": dt_starting,
                },
            )
            _conn.commit()
            return_conn(_conn)

    _conn = get_conn()
    c = _conn.cursor()
    c.execute("SELECT 1 FROM `work_orders` WHERE `dt_end` IS NULL;")  # 查 未完成個工單 有幾張
    ing = c.fetchall()
    return_conn(_conn)

    if len(ing) > 0:
        print()
        print("*** 上一張工單仍在進行中, 無法產生新的模擬資料 ***")
        print("*** 請自行刪除以利後續模擬 or 等待它結束 ***")
        print("*** 手動刪除指令 : 「DELETE FROM `products` WHERE `dt_end` IS NULL;」 ***")
        print("*** 手動刪除指令 : 「DELETE FROM `work_orders` WHERE `dt_end` IS NULL;」 ***")
        print()

    else:
        amt = input("此工單有 幾個產品 (1~12). (直接按 Enter, 預設為 4 個) : ")
        try:
            amt = 4 if amt == "" else int(amt)
            if amt < 1 or amt > 12 or amt != int(amt):
                raise ValueError

            wo = WorkOrder(number_of_products=amt)
            # t = multiprocessing.Process(target=start_making_fake_data, args=(wo,))    # 不同線呈之間無法共享已初始化的連線
            t = threading.Thread(target=start_making_fake_data, args=(wo,))
            t.start()

            print()
            print(f"*** 開始模擬 刷工單, 工單代碼={wo.wo}, 產品數量 = {wo.amt} ***")
            print()

        except ValueError:
            print(f"*** 合理範圍 : 1~12 之間的整數, 你卻輸入 {amt}! ***")


if __name__ == "__main__":
    """
    執行程式後, 使用者輸入
    1 -> 模擬 警報事件發生
    2 -> 模擬 刷工單事件發生
    """
    init_conn_poll()
    global list_work_orders, list_products

    while True:
        print("========== 事件模擬器 ==========")
        m = input("1 : 觸發 警報事件 \n2 : 觸發 刷工單事件 \n  請輸入 : ")

        if m == "1":  # 警報
            simulate_alarm()

        elif m == "2":  # 工單
            list_work_orders = qry_wo_list()
            list_products = qry_product_list()
            simulate_work_order()

        else:
            break
