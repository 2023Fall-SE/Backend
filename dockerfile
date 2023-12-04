# 使用官方 Python 映像
FROM python:3.9

# 設定工作目錄
WORKDIR /app

COPY . .

# 安裝 FastAPI 和 Uvicorn
RUN pip install -r /app/requirements.txt

# 安裝 SQLite3
RUN apt-get update && \
    apt-get install -y sqlite3

# 建立 volume 用於持久性數據共享
VOLUME ["/app/license"]

VOLUME ["/app/database"]

# 開放 FastAPI 服務埠
EXPOSE 8080

# 定義啟動應用程式的指令
CMD python /app/main.py