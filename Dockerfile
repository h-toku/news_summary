# Pythonの公式イメージを使用
FROM python:3.10

# 作業ディレクトリを作成
WORKDIR /app

# 必要なファイルをコンテナにコピー
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Flaskアプリのコードをコピー
COPY . /app

# ポート3000を開放
EXPOSE 3000

# アプリを起動
CMD ["python", "app.py"]
