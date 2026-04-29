FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py card_generator.py clippings_parser.py config.py epub_reader.py state.py ./

CMD ["python3", "bot.py"]
