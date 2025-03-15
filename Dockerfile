# Sử dụng image Python mới hơn với các thư viện cần thiết
FROM python:3.9-slim

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Cài đặt các gói phụ thuộc cần thiết, bao gồm tất cả các phụ thuộc của Firefox
RUN apt-get update && apt-get install -y \
    firefox-esr \
    wget \
    bzip2 \
    xvfb \
    libxtst6 \
    libgtk-3-0 \
    libdbus-glib-1-2 \
    libx11-xcb1 \
    libxt6 \
    libpci3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Tạo thư mục cho Firefox profiles và cấp quyền
RUN mkdir -p /tmp/firefox_profiles && chmod 777 /tmp/firefox_profiles

# Tải và cài đặt geckodriver phiên bản mới nhất (0.36.0) cho Firefox 128+
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.36.0/geckodriver-v0.36.0-linux64.tar.gz \
    && tar -xzf geckodriver-v0.36.0-linux64.tar.gz \
    && chmod +x geckodriver \
    && mv geckodriver /usr/local/bin/ \
    && rm geckodriver-v0.36.0-linux64.tar.gz

# Cài đặt các gói Python cần thiết
RUN pip install --no-cache-dir selenium==4.16.0

# Sao chép script đã sửa đổi vào container
COPY script.py /app/

# Thiết lập môi trường display cho Firefox
ENV DISPLAY=:99

# Tạo script chạy với Xvfb
RUN echo '#!/bin/bash\nXvfb :99 -screen 0 1366x768x24 &\nsleep 1\npython /app/script.py' > /app/run.sh \
    && chmod +x /app/run.sh

# Thiết lập điểm vào cho container
CMD ["/app/run.sh"]