"""
Report Formatter for AI Signal Scout.
Formats the top 5 signals into a Persian intelligence report.
"""

from typing import List, Dict
import html


def format_persian_report(signals: List[Dict]) -> str:
    """
    Format a list of signals into a Persian report.

    Args:
        signals: List of signal dictionaries with keys:
            - title: str
            - score: float
            - what_happened: str (max 3 lines)
            - why_it_matters: str
            - eli5: str
            - x_angle: str
            - source_url: str

    Returns:
        Formatted Persian report string.
    """
    if not signals:
        return ""

    header = "🤖 AI Signal Scout\nگزارش هوش مصنوعی روزانه\n"
    report_parts = [header]

    for i, signal in enumerate(signals, 1):
        # Escape special characters for Telegram MarkdownV2 if needed, but we'll use plain text for now
        # For simplicity, we are not using Markdown in this version, but we can add it later.
        title = signal.get('title', 'بدون عنوان')
        score = signal.get('score', 0)
        # Handle None score
        if score is None:
            score = 0
        what_happened = signal.get('what_happened', '').strip()
        why_it_matters = signal.get('why_it_matters', '').strip()
        eli5 = signal.get('eli5', '').strip()
        x_angle = signal.get('x_angle', '').strip()
        source_url = signal.get('source_url', '')

        # Ensure what_happened is at most 3 lines
        lines = what_happened.split('\n')
        if len(lines) > 3:
            what_happened = '\n'.join(lines[:3]) + '...'

        signal_section = (
            f"\n{i}. {title}\n"
            f"امتیاز: {score:.1f}\n"
            f"چه اتفاقی افتاد: {what_happened}\n"
            f"چرا مهم است: {why_it_matters}\n"
            f"ELI5: {eli5}\n"
            f"چرا برای X مهم است: {x_angle}\n"
            f"منبع: {source_url}\n"
        )
        report_parts.append(signal_section)

    return ''.join(report_parts)


def escape_markdown_v2(text: str) -> str:
    """
    Escape Telegram MarkdownV2 special characters.
    See: https://core.telegram.org/bots/api#formatting-options
    """
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in text)


if __name__ == "__main__":
    # Example usage
    test_signals = [
        {
            "title": "O1-Mini Released",
            "score": 92.5,
            "what_happened": "OpenAI released O1-Mini, a smaller version of their reasoning model.\n"
                           "It is optimized for mobile devices and has lower latency.\n"
                           "The model is available via API.",
            "why_it_matters": "This makes advanced reasoning models accessible on edge devices,\n"
                              "potentially enabling new applications in robotics and IoT.",
            "eli5": "Imagine a smart brain that can fit in your phone and help you solve hard problems.",
            "x_angle": "This could spark discussions about the future of mobile AI and privacy.",
            "source_url": "https://openai.com/o1-mini"
        }
    ]
    print(format_persian_report(test_signals))