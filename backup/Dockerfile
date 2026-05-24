FROM debian:bullseye-slim

RUN apt-get update && apt-get install -y default-mysql-client curl jq bash tzdata ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sL https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc \
    && chmod +x /usr/local/bin/mc

ENV TZ=Asia/Ho_Chi_Minh

COPY backup.sh /backup.sh
RUN chmod +x /backup.sh

CMD ["/backup.sh"]