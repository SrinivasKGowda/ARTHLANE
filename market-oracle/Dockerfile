FROM python:3.11-slim
RUN useradd --system --uid 10001 arthlane
WORKDIR /app
COPY server.py index.html ./
USER arthlane
ENV HOST=0.0.0.0 PYTHONUNBUFFERED=1
EXPOSE 8765
CMD ["python", "server.py"]
