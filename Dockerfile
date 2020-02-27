FROM python as nasz_python

ADD ./requirements.txt .
RUN pip install -r requirements.txt
ADD ./main.py .

FROM alpine/git as nasz_git
ADD ./.git/ /git
RUN git -C /git rev-parse HEAD > /tmp/commit-id
RUN git -C /git log HEAD --oneline | wc -l > /tmp/commit-no
FROM nasz_python
COPY --from=nasz_git /tmp/commit-id /tmp/commit-id
COPY --from=nasz_git /tmp/commit-id /tmp/commit-no

ENTRYPOINT ./main.py
