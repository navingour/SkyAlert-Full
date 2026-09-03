#!/bin/bash

case "$1" in
    start)
        sudo systemctl start skyalert skyalert-web skyalert-worker
        ;;
    stop)
        sudo systemctl stop skyalert skyalert-web skyalert-worker
        ;;
    restart)
        sudo systemctl restart skyalert skyalert-web skyalert-worker
        ;;
    status)
        sudo systemctl status skyalert skyalert-web skyalert-worker
        ;;
    logs)
        sudo journalctl -u skyalert -u skyalert-web -u skyalert-worker -f
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        ;;
esac
