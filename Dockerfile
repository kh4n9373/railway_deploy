FROM python:3.9

# Cập nhật hệ thống và cài đặt các gói cần thiết
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    firefox-esr \
    && rm -rf /var/lib/apt/lists/*

# Tải xuống và cài đặt Geckodriver
ENV GECKODRIVER_VERSION 0.34.0
RUN wget -q "https://github.com/mozilla/geckodriver/releases/download/v$GECKODRIVER_VERSION/geckodriver-v$GECKODRIVER_VERSION-linux64.tar.gz" \
    && tar -xzf geckodriver-v$GECKODRIVER_VERSION-linux64.tar.gz \
    && mv geckodriver /usr/local/bin/ \
    && chmod +x /usr/local/bin/geckodriver \
    && rm geckodriver-v$GECKODRIVER_VERSION-linux64.tar.gz

# Cài đặt thư viện Python cần thiết
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép mã nguồn vào container
COPY . /app

# Chạy script
CMD ["python", "your_script.py"]
