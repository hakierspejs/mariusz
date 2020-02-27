FROM python as nasz_python

ADD ./requirements.txt .
RUN pip install -r requirements.txt
ADD ./main.py .

FROM alpine/git as nasz_git
ADD ./.git/ /git
RUN git -C /git rev-parse HEAD > /tmp/commit-id
RUN git -C /git log HEAD --oneline | wc -l > /tmp/commit-no
RUN git -C /git show -s --format=%ci HEAD > /tmp/commit-date
FROM nasz_python
COPY --from=nasz_git /tmp/commit-id /tmp/commit-id
COPY --from=nasz_git /tmp/commit-id /tmp/commit-no
COPY --from=nasz_git /tmp/commit-id /tmp/commit-date

ENTRYPOINT ./main.py
