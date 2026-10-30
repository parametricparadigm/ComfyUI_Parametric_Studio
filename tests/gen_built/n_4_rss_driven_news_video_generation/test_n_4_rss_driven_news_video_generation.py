"""Tests for n_4_rss_driven_news_video_generation.py"""
import json
import torch

from n_4_rss_driven_news_video_generation import (
    PSN_RSS_Fetcher,
    PSN_News_Script_Generator,
    PSN_News_Video_Aggregator,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Breaking: AI Advances</title>
      <description>Major breakthrough in AI.</description>
      <link>https://example.com/ai</link>
      <category>Technology</category>
    </item>
    <item>
      <title>Economy Grows</title>
      <description>GDP up 3%.</description>
      <link>https://example.com/econ</link>
      <category>Business</category>
    </item>
    <item>
      <title>Weather Alert</title>
      <description>Storm incoming.</description>
      <link>https://example.com/weather</link>
      <category>Weather</category>
    </item>
  </channel>
</rss>
"""

# 1. RSS fetcher parses valid XML
fetcher = PSN_RSS_Fetcher()
items_json, status = fetcher.run(SAMPLE_RSS, 10, "")
assert status == "success", f"Expected success, got {status}"
items = json.loads(items_json)
assert len(items) == 3, f"Expected 3 items, got {len(items)}"
assert items[0]["title"] == "Breaking: AI Advances"

# 2. RSS fetcher respects max_items
items_json2, _ = fetcher.run(SAMPLE_RSS, 2, "")
items2 = json.loads(items_json2)
assert len(items2) == 2, f"Expected 2 items with max_items=2, got {len(items2)}"

# 3. RSS fetcher category filter
items_json3, _ = fetcher.run(SAMPLE_RSS, 10, "Technology")
items3 = json.loads(items_json3)
assert len(items3) == 1, f"Expected 1 item with Technology filter, got {len(items3)}"
assert items3[0]["title"] == "Breaking: AI Advances"

# 4. RSS fetcher handles invalid XML (bad input)
items_json4, status4 = fetcher.run("not valid xml at all", 10, "")
assert status4.startswith("error"), f"Expected error status, got {status4}"
items4 = json.loads(items_json4)
assert items4 == [], f"Expected empty list, got {items4}"

# 5. RSS fetcher handles empty string
items_json5, status5 = fetcher.run("", 10, "")
assert status5.startswith("error"), f"Expected error for empty input, got {status5}"

# 6. Script generator includes all headlines
gen = PSN_News_Script_Generator()
script, scenes_json = gen.run(items_json, "News Anchor")
assert "Breaking: AI Advances" in script, "Script missing headline 1"
assert "Economy Grows" in script, "Script missing headline 2"
assert "Weather Alert" in script, "Script missing headline 3"
scenes = json.loads(scenes_json)
assert len(scenes) == 3, f"Expected 3 scenes, got {len(scenes)}"

# 7. Script generator with different style
script2, _ = gen.run(items_json, "Casual")
assert "Hey there" in script2, "Casual style opener missing"

# 8. Script generator handles bad input (invalid JSON)
script3, scenes3 = gen.run("not json", "News Anchor")
assert isinstance(script3, str)
scenes3_list = json.loads(scenes3)
assert scenes3_list == [], f"Expected empty scenes for bad input, got {scenes3_list}"

# 9. Video aggregator produces correct thumbnail shape
agg = PSN_News_Video_Aggregator()
path, thumb = agg.run("Some script text", "1280x720", 30)
assert thumb.shape == (1, 720, 1280, 3), f"Expected [1,720,1280,3], got {thumb.shape}"
assert thumb.dtype == torch.float32
assert thumb.min() >= 0.0 and thumb.max() <= 1.0, "Thumbnail values out of [0,1] range"
assert "1280x720" in path, f"Path should contain resolution: {path}"

# 10. Video aggregator 1920x1080
path2, thumb2 = agg.run("Another script", "1920x1080", 60)
assert thumb2.shape == (1, 1080, 1920, 3), f"Expected [1,1080,1920,3], got {thumb2.shape}"
assert "1920x1080" in path2

# 11. Node mappings exist
assert "PSN_RSS_Fetcher" in NODE_CLASS_MAPPINGS
assert "PSN_News_Script_Generator" in NODE_CLASS_MAPPINGS
assert "PSN_News_Video_Aggregator" in NODE_CLASS_MAPPINGS
assert len(NODE_DISPLAY_NAME_MAPPINGS) == 3

# 12. INPUT_TYPES classmethod works
it = PSN_RSS_Fetcher.INPUT_TYPES()
assert "required" in it
assert "feed_xml" in it["required"]

print('ok')
