"""
VisionarySTEM agents — Phase 3 multi-step planner.

Cấu trúc:
- tools.py: registry các tool có thể gọi (web_search, analyze_url, library_load...)
- planner.py: Gemini structured output → Plan có nhiều steps
- executor.py: async sequential runner, yield SSE events cho frontend narrate
"""
