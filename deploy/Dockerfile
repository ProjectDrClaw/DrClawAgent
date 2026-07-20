# Base images — override with --build-arg for environments without ACR access.
ARG NODE_IMAGE=node:20-slim
# Distroless image only: binary lives at /uv (python-*-slim variants do not).
ARG UV_IMAGE=ghcr.io/astral-sh/uv:latest

# -----------------------------------------------------------------------------
# Stage 1: build console frontend (dist not committed in repo).
# -----------------------------------------------------------------------------
FROM ${NODE_IMAGE} AS console-builder
WORKDIR /app
COPY console /app/console
RUN cd /app/console && npm ci --include=dev && npm run build

# Alias for uv binary so COPY --from can reference a build-arg image.
FROM ${UV_IMAGE} AS uv-src

# -----------------------------------------------------------------------------
# Stage 2: runtime image with Python, Chromium, and app.
# -----------------------------------------------------------------------------
FROM ${NODE_IMAGE}

# ENV variables
ENV NODE_ENV=production
ENV WORKSPACE_DIR=/app
ENV DRCLAW_WORKING_DIR=/app/working
ENV DRCLAW_SECRET_DIR=/app/working.secret
ENV DRCLAW_BACKUP_DIR=/app/working.backups

# Channel filtering: use DRCLAW_DISABLED_CHANNELS (exclusion, recommended)
# or DRCLAW_ENABLED_CHANNELS (whitelist). Override at runtime with -e.
# Build-time QWENPAW_* args are still accepted by scripts/docker_build.sh.
ARG DRCLAW_DISABLED_CHANNELS="imessage"
ENV DRCLAW_DISABLED_CHANNELS=${DRCLAW_DISABLED_CHANNELS}
ARG DRCLAW_ENABLED_CHANNELS=""
ENV DRCLAW_ENABLED_CHANNELS=${DRCLAW_ENABLED_CHANNELS}

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --fix-missing \
    curl  \
    python3  \
    python3-pip  \
    python3-venv \
    build-essential  \
    libssl-dev  \
    git  \
    supervisor  \
    vim  \
    gettext-base \
    xfce4 \
    xfce4-terminal \
    xvfb \
    dbus-x11 \
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
  && rm -rf /var/lib/apt/lists/* \
  && apt-get clean


RUN apt-get update && apt-get install -y --fix-missing \
    chromium \
    chromium-sandbox \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxtst6 \
    libnss3 \
    libglib2.0-0 \
    libdrm2 \
    libgbm1 \
    libasound2 \
    fonts-liberation \
    libu2f-udev \
  && rm -rf /var/lib/apt/lists/* \
  && apt-get clean


RUN apt-get update && apt-get install -y --fix-missing \
    libreoffice \
    poppler-utils \
    qpdf \
    pdftk-java \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    tesseract-ocr-chi-tra \
    tesseract-ocr-eng \
    pandoc \
    imagemagick \
    ffmpeg \
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
  && rm -rf /var/lib/apt/lists/* \
  && apt-get clean


RUN sed -i 's/^CHROMIUM_FLAGS=""/CHROMIUM_FLAGS="--no-sandbox"/' /usr/bin/chromium

# Playwright: use system Chromium (already installed above).
ENV PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium
# Avoid Playwright downloading its own browser when executable_path is used.
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
# Indicate running in container (used e.g. for Chromium --no-sandbox).
ENV DRCLAW_RUNNING_IN_CONTAINER=1

WORKDIR ${WORKSPACE_DIR}

RUN python3 -m venv venv
ENV PATH="/app/venv/bin:$PATH"

COPY pyproject.toml setup.py README.md ./
COPY src ./src
COPY docs/ ./src/qwenpaw/docs/
# Inject console dist from build stage (repo does not commit dist).
COPY --from=console-builder /app/console/dist/ ./src/qwenpaw/console/
# Speed up Python package installation with uv.
COPY --from=uv-src /uv /bin/uv
RUN uv pip install --no-cache-dir . && rm -rf ./build
# Install npm packages for pptx/docx generation skills globally
RUN npm install -g pptxgenjs docx react-icons react react-dom sharp

# Dr.Claw app port (default 8088). Override at runtime with -e DRCLAW_PORT=3000.
ENV DRCLAW_PORT=8088

COPY deploy/config/supervisord.conf.template /etc/supervisor/conf.d/supervisord.conf.template
COPY --chmod=755 deploy/entrypoint.sh /entrypoint.sh

EXPOSE 8088

CMD ["/entrypoint.sh"]
