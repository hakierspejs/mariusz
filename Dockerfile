FROM python as nasz_python

WORKDIR /app

ADD ./requirements.txt .
ADD ./setup.py .
ADD ./mariusz ./mariusz/

RUN pip install -r requirements.txt
RUN python setup.py install

RUN mkdir /user && chown 1000:1000 /user
WORKDIR /user
ENV HOME=/user

USER 1000

FROM alpine/git as nasz_git
ADD ./.git/ /git
RUN git -C /git rev-parse HEAD > /tmp/commit-id
RUN git -C /git log HEAD --oneline | wc -l > /tmp/commit-no
RUN git -C /git show -s --format=%ci HEAD > /tmp/commit-date
FROM nasz_python
COPY --from=nasz_git /tmp/commit-id /tmp/commit-id
COPY --from=nasz_git /tmp/commit-no /tmp/commit-no
COPY --from=nasz_git /tmp/commit-date /tmp/commit-date

ENTRYPOINT mariusz-bot
