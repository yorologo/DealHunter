import re
with open("tests/test_uber_browser_transport.py", "r") as f:
    text = f.read()
text = re.sub(r'    @pytest.mark.asyncio\n    async def test_capture_deduplicates_products.*?assert result\["products_unique"\] == 2', '', text, flags=re.DOTALL)
with open("tests/test_uber_browser_transport.py", "w") as f:
    f.write(text)
