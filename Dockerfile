# Use Debian Bullseye as base
FROM debian:bullseye-slim

# Set working directory
WORKDIR /app

# Install required dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    wget \
    gnupg \
    xvfb \
    dbus-x11 \
    procps \
    psmisc \
    unzip \
    # Chrome dependencies
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libxshmfence1 \
    xdg-utils \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome WebDriver
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d. -f1) \
    && CHROME_DRIVER_VERSION=$(wget -qO- "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}") \
    && wget -q "https://chromedriver.storage.googleapis.com/${CHROME_DRIVER_VERSION}/chromedriver_linux64.zip" \
    && unzip chromedriver_linux64.zip \
    && mv chromedriver /usr/local/bin/ \
    && chmod +x /usr/local/bin/chromedriver \
    && rm chromedriver_linux64.zip

# Install Python packages
RUN pip3 install --no-cache-dir selenium==4.10.0 psutil

# Create directories
RUN mkdir -p /tmp/chrome_profiles && chmod 777 /tmp/chrome_profiles
RUN mkdir -p /tmp/logs && chmod 777 /tmp/logs

# Copy script to container
COPY script.py /app/

# Set environment variables
ENV DISPLAY=:99
ENV PYTHONUNBUFFERED=1
ENV NUM_THREADS=3
ENV TOTAL_VIEWS=1000
ENV MAX_RETRIES=3

# Create startup script
RUN echo '#!/bin/bash\n\
# Start Xvfb\n\
echo "Starting Xvfb..."\n\
Xvfb :99 -screen 0 1366x768x24 -ac +extension GLX +render -noreset &\n\
XVFB_PID=$!\n\
\n\
# Verify Chrome installation\n\
echo "Checking Chrome installation..."\n\
google-chrome --version\n\
\n\
# Verify chromedriver installation\n\
echo "Checking chromedriver installation..."\n\
chromedriver --version\n\
\n\
# Start DBUS\n\
echo "Starting DBUS..."\n\
mkdir -p /var/run/dbus\n\
dbus-daemon --system || true\n\
\n\
# Run the script\n\
echo "Starting YouTube view bot..."\n\
python3 /app/script.py 2>&1 | tee /tmp/logs/script.log\n\
SCRIPT_EXIT=$?\n\
\n\
# Clean up\n\
echo "Cleaning up..."\n\
pkill -f chrome || true\n\
pkill -f chromedriver || true\n\
\n\
if ps -p $XVFB_PID > /dev/null; then\n\
    kill $XVFB_PID\n\
fi\n\
\n\
exit $SCRIPT_EXIT' > /app/run.sh \
    && chmod +x /app/run.sh

CMD ["/app/run.sh"]