# Use Debian Bullseye as base for better Firefox compatibility
FROM debian:bullseye-slim

# Set working directory
WORKDIR /app

# Install required dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    firefox-esr \
    wget \
    bzip2 \
    xvfb \
    dbus-x11 \
    libdbus-glib-1-2 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxt6 \
    libpci3 \
    procps \
    psmisc \
    libcairo2 \
    libpango-1.0-0 \
    xfce4-terminal \
    libatk1.0-0 \
    libasound2 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libnspr4 \
    libnss3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip3 install --no-cache-dir selenium==4.10.0 psutil

# Create directories
RUN mkdir -p /tmp/firefox_profiles && chmod 777 /tmp/firefox_profiles
RUN mkdir -p /tmp/logs && chmod 777 /tmp/logs

# Download older, more stable geckodriver
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.32.0/geckodriver-v0.32.0-linux64.tar.gz \
    && tar -xzf geckodriver-v0.32.0-linux64.tar.gz \
    && chmod +x geckodriver \
    && mv geckodriver /usr/local/bin/ \
    && rm geckodriver-v0.32.0-linux64.tar.gz

# Copy script to container
COPY script.py /app/

# Set environment variables
ENV DISPLAY=:99
ENV MOZ_HEADLESS=1
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
# Start a lightweight window manager\n\
echo "Ensuring X server is running..."\n\
sleep 2\n\
\n\
# Verify Firefox installation\n\
echo "Checking Firefox installation..."\n\
firefox-esr --version\n\
\n\
# Verify geckodriver installation\n\
echo "Checking geckodriver installation..."\n\
geckodriver --version\n\
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
pkill -f firefox || true\n\
pkill -f geckodriver || true\n\
\n\
if ps -p $XVFB_PID > /dev/null; then\n\
    kill $XVFB_PID\n\
fi\n\
\n\
exit $SCRIPT_EXIT' > /app/run.sh \
    && chmod +x /app/run.sh

CMD ["/app/run.sh"]