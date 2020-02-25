FROM python as nasz_python

WORKDIR /app

ADD ./requirements.txt .
ADD ./setup.py .
ADD ./mariusz ./mariusz/

RUN pip install -r requirements.txt
RUN python setup.py install

FROM alpine/git as nasz_git
ADD ./.git/ /git
RUN git -C /git rev-parse HEAD > /tmp/commit-id

FROM nasz_python
COPY --from=nasz_git /tmp/commit-id /tmp/commit-id

ENTRYPOINT mariusz-bot
