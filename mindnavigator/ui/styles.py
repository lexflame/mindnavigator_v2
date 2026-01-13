"""Общие стили для фонов с абстрактным математико-физическим рисунком."""

MATH_PHYS_PATTERN = (
    "data:image/svg+xml;base64,"
    "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMjAiIGhl"
    "aWdodD0iMjIwIiB2aWV3Qm94PSIwIDAgMjIwIDIyMCI+CiAgPGcgZmlsbD0ibm9uZSIgc3Ry"
    "b2tlPSJ3aGl0ZSIgc3Ryb2tlLW9wYWNpdHk9IjAuMDgiIHN0cm9rZS13aWR0aD0iMSI+CiAg"
    "ICA8Y2lyY2xlIGN4PSI2MCIgY3k9IjYwIiByPSIyNiIvPgogICAgPGNpcmNsZSBjeD0iMTYw"
    "IiBjeT0iMTUwIiByPSIzMiIvPgogICAgPHBhdGggZD0iTTAgMTEwIFEgMzUgODAgNzAgMTEw"
    "IFQgMTQwIDExMCBUIDIyMCAxMTAiLz4KICAgIDxwYXRoIGQ9Ik0yMCAyMDAgTCAyMDAgMjAi"
    "Lz4KICAgIDxwYXRoIGQ9Ik0zMCAyMCBMIDE5MCAxODAiLz4KICA8L2c+CiAgPGcgZmlsbD0i"
    "bm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLW9wYWNpdHk9IjAuMDYiIHN0cm9rZS13aWR0"
    "aD0iMSI+CiAgICA8cGF0aCBkPSJNMTEwIDAgTCAxMTAgMjIwIi8+CiAgICA8cGF0aCBkPSJN"
    "MCAxMTAgTCAyMjAgMTEwIi8+CiAgPC9nPgo8L3N2Zz4="
)

MATH_PHYS_BACKGROUND = f"""
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #1d2030, stop:0.5 #171a24, stop:1 #12141b);
    background-image: url("{MATH_PHYS_PATTERN}");
    background-position: center;
    background-repeat: repeat;
"""
