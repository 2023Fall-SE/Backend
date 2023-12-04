from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime
from datetime import datetime
from database import Base

class User(Base):
    """
    id: unique id
    username: 使用者帳戶
    password: hash密碼
    display_name: 使用者想顯示的名稱
    phone: 手機號碼
    license: 使用者駕照
    carpool_money: 代幣數量
    mail: 使用者信箱
    picture: 個人頭像 不確定會不會用 先開
    other_intro: 其他介紹 不確定會不會用 先開
    """

    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    username = Column(String(20), nullable=False)
    password = Column(String(60), nullable=False)
    display_name = Column(String(20), nullable=False)
    phone = Column(String(13))
    license = Column(String(100))  #image URL
    carpool_money = Column(Float, nullable=False)
    mail = Column(String(100))
    picture = Column(String(100))
    other_intro = Column(String(100))   

    def __repr__(self):
        return "<User %r>" % self.id

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class Payment(Base):
    """
    注意: 付款的Payment 應在 Event 結束時被建立起來

    id: unique id
    with_draw_or_top_up: 0 = 付款, 1 = 儲值
    money: 交易金額
    time: 交易時間 (Payment若為付款，付款時需要更新)
    event_id: Payment若為付款則為 FK to event 否則為 null
    isCompleted: Payment若為付款，則用來判斷用戶是否完成付款。
    user_id: 付款者
    transaction_id, order_id: Line Pay產生之訂單id，分別用於Conform APi & Unique transaction
    """

    __tablename__ = "payment"
    id = Column(Integer, primary_key=True)
    with_draw_or_top_up = Column(Integer, nullable=False)
    money = Column(Float, nullable=False)
    time = Column(DateTime, default=datetime.now())
    event_id = Column(Integer, ForeignKey('event.id'))
    isCompleted = Column(Boolean, nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    transaction_id = Column(String(19))    #Line Pay Transaction Id

    def __repr__(self):
        return "<Payment %r>" % self.id

class Event(Base):
    """
    id: unique id
    initiator: 發起者, FK to User
    joiner: 這邊用string, 不做 FK 用偷吃步的方式 "joiner1,joiner2..." 紀錄
    location: 同上用偷吃步的方式, ex: "中正紀念堂,台大,古亭"
    joiner_to_location: 每個joiner的上下車地點, ex: "1-3, 2-3" (1: 中正紀念堂, 2: 台大, 3: 古亭), joiner1一定為initiator
    start_time: 共乘開始時間
    end_time: 共乘結束時間 (在結束時紀錄)
    is_self_drive: 是否是自駕 (若是，程式邏輯應去查看使用者是否有上傳駕照)
    score: 乘客對此共乘的平均評分 (0~5)，這邊也是不想額外開表只能記平均
    rating_count: 有幾個乘客評分了，用來讓你計算上面的平均分
    accounts_payable: Event總共須付的錢 (由initiator在create new event時設定)
    """

    __tablename__ = "event"
    id = Column(Integer, primary_key=True)
    initiator = Column(Integer, ForeignKey('user.id'), nullable=False)
    joiner = Column(String(100), nullable=False)
    location = Column(String(100), nullable=False)
    joiner_to_location = Column(String(100), nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    is_self_drive = Column(Boolean, nullable=False)
    score = Column(Float)
    rating_count = Column(Integer)
    number_of_people = Column(Integer)
    available_seats = Column(Integer)
    accounts_payable = Column(Float, nullable=False)
    status = Column(String(100),  nullable=False)

class Communication(Base):
    """
    id: unique id
    event_id: FK to Event, 發送訊息至哪個 EventId
    sender: FK to User, 發送者的ID
    time: 發送訊息的時間
    content: 發送訊息的內容
    """

    __tablename__ = "communication"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('event.id'), nullable=False)
    sender = Column(String(100),  ForeignKey('user.id'), nullable=False)
    time = Column(DateTime, default=datetime.now())
    content = Column(String(200), nullable=False)

class Notification(Base):

    __tablename__ = "notification"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    type = Column(String(100),  nullable=False)
    time = Column(DateTime, default=datetime.now())
    event_id = Column(Integer, ForeignKey('event.id'), nullable=False)
    content = Column(String(200), nullable=False)
