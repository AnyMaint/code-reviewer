FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    apt-get clean

WORKDIR /app

# Copy everything except docker/ into /app
COPY . /app/
RUN rm -rf /app/docker


RUN pip3 install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python3", "review.py", "--vcsp", "bitbucket", "--deep", "--full-context", "--llm", "chatgpt", "grok", "--mode", "comments", "--add_statistic_info"]
