"""
Telegram Bot notification system for the AI/ML Job Alert System.
Sends formatted job alerts via Telegram Bot API using HTML formatting.
Automatically splits messages that exceed Telegram's 4096 char limit.
"""

import logging
import os
import time
from datetime import datetime
from typing import Optional

import requests

from config.settings import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TELEGRAM_API_URL,
    TELEGRAM_MAX_MESSAGE_LENGTH,
    RETRY_ATTEMPTS,
    RETRY_DELAY,
    IST,
)
from core.models import JobListing

logger = logging.getLogger(__name__)


class TelegramBot:
    """Sends job alert notifications via Telegram Bot API."""

    def __init__(self, bot_token: str = "", chat_id: str = ""):
        self.bot_token = bot_token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID
        self.api_url = TELEGRAM_API_URL.format(token=self.bot_token)

    @property
    def _is_dry_run(self) -> bool:
        """Check dry run at runtime (not import time) so CLI --dry-run works."""
        return os.environ.get("DRY_RUN", "false").lower() == "true"

    def send_job_alerts(
        self,
        new_jobs: list[JobListing],
        stats: dict,
    ) -> bool:
        """
        Send formatted job alert to Telegram.
        Returns True if message was sent successfully.
        """
        if not new_jobs:
            logger.info("No new jobs to send.")
            return self._send_no_jobs_message(stats)

        # Build the message
        messages = self._format_job_messages(new_jobs, stats)

        # Send each message chunk
        success = True
        for i, message in enumerate(messages):
            if not self._send_message(message):
                success = False
                logger.error(f"Failed to send message chunk {i + 1}/{len(messages)}")
            else:
                logger.info(f"Sent message chunk {i + 1}/{len(messages)}")
                time.sleep(1)  # Avoid Telegram rate limits

        return success

    def _format_job_messages(
        self,
        jobs: list[JobListing],
        stats: dict,
    ) -> list[str]:
        """Format jobs into Telegram HTML messages, splitting if necessary."""
        now_ist = datetime.now(IST).strftime("%d %b %Y, %I:%M %p IST")

        # Header
        header = (
            "🚀 <b>AI/ML Fresher Job Alert</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {now_ist}\n"
            f"📊 New Jobs Since Last Run: <b>{len(jobs)}</b>\n"
            f"🔍 Sources: {stats.get('successful_sources', '?')}/{stats.get('total_sources', '?')} active\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        )

        # Format each job
        job_blocks = []
        for i, job in enumerate(jobs, 1):
            prestige_bar = self._get_prestige_bar(job.company_prestige_score)
            source_emoji = self._get_source_emoji(job.source_platform)
            salary_display = self._format_salary(job)
            date_display = self._format_date(job.posting_date)

            easy_badge = " ⚡ <b>Easy Apply</b>" if job.source_platform == "linkedin_easy_apply" else ""
            block = (
                f"<b>{i}. {self._escape_html(job.company_name)}</b>{easy_badge}\n"
                f"   📋 {self._escape_html(job.job_title)}\n"
                f"   📍 {self._escape_html(job.location)}{date_display}\n"
                f"   💰 {salary_display}\n"
                f"   🏅 {prestige_bar} ({job.company_prestige_score}/10)\n"
                f"   {source_emoji} {self._escape_html(job.source_platform)}\n"
                f"   🔗 <a href=\"{job.apply_url}\">Apply Now</a>\n\n"
            )
            job_blocks.append(block)

        # Summary
        if jobs:
            top_salary = max(
                (j.estimated_salary_lpa or 0 for j in jobs), default=0
            )
            top_companies = ", ".join(
                sorted(set(j.company_name for j in jobs[:5]))
            )

            # Source health summary
            source_health = []
            for src_name, src_data in stats.get("source_results", {}).items():
                count = src_data.get("jobs_found", 0)
                status = src_data.get("status", "unknown")
                if count > 0:
                    source_health.append(f"✅ {src_name}: {count}")
                elif "success" in status:
                    source_health.append(f"⚪ {src_name}: 0")
                else:
                    source_health.append(f"❌ {src_name}")

            summary = (
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "📈 <b>Summary</b>\n"
                f"• Total New Jobs: {len(jobs)}\n"
                f"• Highest Est. Salary: ₹{top_salary} LPA\n"
                f"• Top Companies: {self._escape_html(top_companies)}\n\n"
                "🔍 <b>Source Health</b>\n"
                + "\n".join(source_health) + "\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "<i>Powered by AI/ML Job Alert System</i> 🤖"
            )
        else:
            summary = ""

        # Split into chunks that fit Telegram's message limit
        messages = []
        current_message = header

        for block in job_blocks:
            if len(current_message) + len(block) > TELEGRAM_MAX_MESSAGE_LENGTH - 500:
                messages.append(current_message)
                current_message = "🏆 <b>Jobs (continued)</b>\n\n"

            current_message += block

        current_message += summary

        # If even the last message is too long, split it
        if len(current_message) > TELEGRAM_MAX_MESSAGE_LENGTH:
            messages.append(current_message[:TELEGRAM_MAX_MESSAGE_LENGTH - 100])
            remaining = current_message[TELEGRAM_MAX_MESSAGE_LENGTH - 100:]
            while remaining:
                chunk = remaining[:TELEGRAM_MAX_MESSAGE_LENGTH - 100]
                messages.append(chunk)
                remaining = remaining[TELEGRAM_MAX_MESSAGE_LENGTH - 100:]
        else:
            messages.append(current_message)

        return messages

    def _format_date(self, date_str: str) -> str:
        if not date_str:
            return ""
        try:
            d = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return f"\n   📅 Posted: {d.strftime('%d %b %Y')}"
        except Exception:
            return f"\n   📅 Posted: {self._escape_html(str(date_str)[:10])}"

    def _format_salary(self, job: JobListing) -> str:
        """Format salary display with confidence indicator."""
        if job.salary:
            return self._escape_html(job.salary)

        if job.estimated_salary_lpa:
            confidence = job.salary_confidence or "medium"
            conf_emoji = {"high": "🟢", "medium": "🟡", "low": "🟠"}.get(confidence, "⚪")
            return f"~₹{job.estimated_salary_lpa} LPA {conf_emoji} ({confidence} est.)"

        return "Not disclosed"

    def _get_prestige_bar(self, score: int) -> str:
        """Create a visual prestige bar."""
        filled = min(score, 10)
        return "█" * filled + "░" * (10 - filled)

    def _send_no_jobs_message(self, stats: dict = None) -> bool:
        """Send a notification when no new jobs are found."""
        now_ist = datetime.now(IST).strftime("%d %b %Y, %I:%M %p IST")

        # Source summary
        source_lines = []
        if stats and "source_results" in stats:
            for src_name, src_data in stats.get("source_results", {}).items():
                count = src_data.get("jobs_found", 0)
                status = src_data.get("status", "unknown")
                if count > 0:
                    source_lines.append(f"✅ {src_name}: {count} raw")
                elif "success" in status:
                    source_lines.append(f"⚪ {src_name}: 0")
                else:
                    source_lines.append(f"❌ {src_name}")

        source_text = "\n".join(source_lines) if source_lines else "No source data"

        message = (
            "📭 <b>AI/ML Job Alert — No New Jobs</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {now_ist}\n\n"
            "No new AI/ML fresher opportunities found since the last run.\n"
            "All discovered jobs were already reported in previous alerts.\n\n"
            "🔍 <b>Source Health</b>\n"
            f"{source_text}\n\n"
            "The system will check again at the next scheduled time.\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Powered by AI/ML Job Alert System</i> 🤖"
        )
        return self._send_message(message)

    def _send_message(self, text: str) -> bool:
        """Send a single message via Telegram Bot API using HTML."""
        if self._is_dry_run:
            logger.info(f"[DRY RUN] Would send Telegram message ({len(text)} chars)")
            logger.debug(f"[DRY RUN] Message preview:\n{text[:500]}")
            return True

        if not self.bot_token or not self.chat_id:
            logger.error("Telegram bot token or chat ID not configured!")
            return False

        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        for attempt in range(RETRY_ATTEMPTS):
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    timeout=30,
                )

                if response.status_code == 200:
                    return True

                # If HTML parsing fails, try plain text as last resort
                if response.status_code == 400 and "parse" in response.text.lower():
                    logger.warning("HTML parse failed, falling back to plain text")
                    return self._send_plain_text(text)

                logger.warning(
                    f"Telegram API error (attempt {attempt + 1}): "
                    f"{response.status_code} - {response.text}"
                )

            except requests.exceptions.RequestException as e:
                logger.warning(f"Telegram request error (attempt {attempt + 1}): {e}")

            time.sleep(RETRY_DELAY * (attempt + 1))

        logger.error("Failed to send Telegram message after all retries")
        return False

    def _send_plain_text(self, html_text: str) -> bool:
        """Fallback: strip HTML tags and send as plain text."""
        import re
        plain_text = re.sub(r'<[^>]+>', '', html_text)

        payload = {
            "chat_id": self.chat_id,
            "text": plain_text,
            "disable_web_page_preview": True,
        }

        try:
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=30,
            )
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.error(f"Telegram plain text fallback failed: {e}")
            return False

    def _escape_html(self, text: str) -> str:
        """Escape special characters for Telegram HTML."""
        if not text:
            return ""
        text = str(text)
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        return text

    def _get_source_emoji(self, source: str) -> str:
        """Get emoji for a source platform."""
        emojis = {
            "greenhouse": "🌱",
            "lever": "🔧",
            "linkedin": "💼",
            "linkedin_easy_apply": "⚡",
            "naukri": "🇮🇳",
            "wellfound": "🚀",
            "foundit": "🔍",
            "google_jobs": "🔎",
            "careers_page": "🏢",
            "custom_career": "🏢",
            "cutshort": "✂️",
            "instahyre": "📱",
            "ashby": "🎯",
            "workday": "🏦",
            "smartrecruiters": "🔵",
        }
        return emojis.get(source, "📌")

    def test_connection(self) -> bool:
        """Test the Telegram bot connection."""
        if self._is_dry_run:
            logger.info("[DRY RUN] Skipping Telegram connection test")
            return True

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                bot_name = data.get("result", {}).get("username", "Unknown")
                logger.info(f"Telegram bot connected: @{bot_name}")
                return True
            else:
                logger.error(f"Telegram bot connection failed: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Telegram connection test error: {e}")
            return False
