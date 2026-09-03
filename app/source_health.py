from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.logger import logger


class SourceHealth:

    def __init__(self, failure_threshold=3):

        self.failure_threshold = failure_threshold

        self.consecutive_failures = 0

        self.is_down = False

        self.down_since = None


    def success(self):

        was_down = self.is_down

        downtime = None

        if was_down and self.down_since:

            downtime = (
                datetime.now(timezone.utc)
                - self.down_since
            ).total_seconds()


        self.consecutive_failures = 0

        self.is_down = False

        self.down_since = None


        if was_down:

            logger.info(
                "Aircraft source recovered"
            )


        return {
            "recovered": was_down,
            "downtime": downtime
        }


    def failure(self):

        self.consecutive_failures += 1


        logger.warning(
            "Aircraft source failure %d/%d",
            self.consecutive_failures,
            self.failure_threshold
        )


        if (
            self.consecutive_failures >= self.failure_threshold
            and not self.is_down
        ):

            self.is_down = True

            self.down_since = datetime.now(
                timezone.utc
            )

            logger.error(
                "Aircraft source DOWN"
            )

            return {
                "down": True
            }


        return {
            "down": False
        }


    @staticmethod
    def format_time(dt):

        if not dt:

            return "-"


        return dt.astimezone(
            ZoneInfo("Asia/Kolkata")
        ).strftime(
            "%d %b %Y, %H:%M:%S IST"
        )


source_health = SourceHealth()
