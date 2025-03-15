# Use a more stable Python base image
FROM python:3.9-bullseye

# Set working directory in container
WORKDIR /app

# Install necessary dependencies for Firefox and Selenium
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
    procps \
    dbus \
    fontconfig \
    libcairo2 \
    libpango-1.0-0 \
    sudo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create directory for Firefox profiles with proper permissions
RUN mkdir -p /tmp/firefox_profiles && chmod 777 /tmp/firefox_profiles
RUN mkdir -p /tmp/logs && chmod 777 /tmp/logs

# Download and install the latest stable geckodriver (0.33.0) for better compatibility with Firefox ESR
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux64.tar.gz \
    && tar -xzf geckodriver-v0.33.0-linux64.tar.gz \
    && chmod +x geckodriver \
    && mv geckodriver /usr/local/bin/ \
    && rm geckodriver-v0.33.0-linux64.tar.gz

# Install Python packages needed for the script
RUN pip install --no-cache-dir selenium==4.12.0 requests

# Copy script to container
COPY script.py /app/

# Set environment variables
ENV DISPLAY=:99
ENV MOZ_HEADLESS=1
ENV PYTHONUNBUFFERED=1

# Create startup script with proper error handling
RUN echo '#!/bin/bash\n\
# Start Xvfb\n\
Xvfb :99 -screen 0 1366x768x24 -ac &\n\
XVFB_PID=$!\n\
echo "Started Xvfb with PID: $XVFB_PID"\n\
\n\
# Wait for Xvfb to start\n\
sleep 2\n\
\n\
# Check if geckodriver is available\n\
if [ ! -f /usr/local/bin/geckodriver ]; then\n\
    echo "ERROR: geckodriver not found!"\n\
    exit 1\n\
fi\n\
\n\
# Check if Firefox is available\n\
if ! command -v firefox-esr &> /dev/null; then\n\
    echo "ERROR: Firefox not found!"\n\
    exit 1\n\
fi\n\
\n\
# Run script with error handling\n\
echo "Starting YouTube view bot..."\n\
python /app/script.py 2>&1 | tee /tmp/logs/script.log\n\
SCRIPT_EXIT=$?\n\
\n\
# Kill Xvfb when done\n\
if ps -p $XVFB_PID > /dev/null; then\n\
    kill $XVFB_PID\n\
fi\n\
\n\
exit $SCRIPT_EXIT' > /app/run.sh \
    && chmod +x /app/run.sh

# Set healthcheck to ensure container is running properly
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD ps aux | grep -q [X]vfb || exit 1

# Set container entrypoint
CMD ["/app/run.sh"]