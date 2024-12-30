FROM python:3.13 as nasz_python

WORKDIR /app

RUN apt-get update && apt-get install -y dumb-init && apt-get clean

ADD ./requirements.txt .
RUN pip install -r requirements.txt

ADD ./setup.py .
ADD ./mariusz ./mariusz/
RUN python setup.py install

RUN mkdir /user && chown 1000:1000 /user
WORKDIR /user
ENV HOME=/user

FROM alpine/git as nasz_git
ADD ./.git/ /git
RUN git -C /git rev-parse HEAD > /tmp/commit-id
RUN git -C /git log HEAD --oneline | wc -l > /tmp/commit-no
RUN git -C /git show -s --format=%ci HEAD > /tmp/commit-date
FROM nasz_python
COPY --from=nasz_git /tmp/commit-id /tmp/commit-id
COPY --from=nasz_git /tmp/commit-no /tmp/commit-no
COPY --from=nasz_git /tmp/commit-date /tmp/commit-date

ENTRYPOINT ["dumb-init", "--", "python3.13", "-m", "mariusz.main"]
