FROM alpine:3.19

RUN apk add --no-cache mysql-client curl jq bash tzdata \
    && curl -O https://dl.min.io/client/mc/release/linux-amd64/mc \
    && chmod +x mc \
    && mv mc /usr/local/bin/mc

ENV TZ=Asia/Ho_Chi_Minh

COPY backup.sh /backup.sh
RUN chmod +x /backup.sh

CMD ["/backup.sh"]