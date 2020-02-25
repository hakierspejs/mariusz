FROM python
ADD ./requirements.txt .
RUN pip install -r requirements.txt
ADD ./main.py .
ENTRYPOINT ./main.py
