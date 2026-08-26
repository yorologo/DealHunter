import re

with open("src/dealhunter/providers/uber_eats/browser_transport.py", "r") as f:
    content = f.read()

# Replace _fetch_store_page body
new_js = """
    async def _fetch_store_page(self, store_uuid, offset):
        \"\"\"Fetch one page of getStoreV1 via browser-context fetch.\"\"\"
        fetch_js = f'''
        (async () => {{
            try {{
                const resp = await fetch('/_p/api/getStoreV1?localeCode=mx', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'x-csrf-token': 'x'
                    }},
                    body: JSON.stringify({{
                        storeUuid: '{store_uuid}',
                        catalogSectionOffset: {offset}
                    }})
                }});
                if (resp.status === 403) return JSON.stringify({{error: 'csrf_rejected', httpStatus: 403}});
                if (resp.status === 401) return JSON.stringify({{error: 'login_required', httpStatus: 401}});
                if (!resp.ok) return JSON.stringify({{error: 'http_' + resp.status, httpStatus: resp.status}});

                const data = await resp.json();
                if (data.status !== 'success') return JSON.stringify({{error: 'api_' + (data.status || 'unknown')}});

                const d = data.data || {{}};
                const sections = d.sections || [];
                const csm = d.catalogSectionsMap || {{}};

                // Simply return the raw structures needed by parser.py
                return JSON.stringify({{
                    status: data.status,
                    storeTitle: d.title,
                    storeUuid: d.uuid,
                    slug: d.slug,
                    isOpen: d.isOpen,
                    isOrderable: d.isOrderable,
                    sections: sections,
                    catalogSectionsMap: csm,
                    pagingInfo: d.catalogSectionPagingInfo
                }});
            }} catch (e) {{
                return JSON.stringify({{error: e.message}});
            }}
        }})()
        '''
        try:
            result_str = await self._evaluate(fetch_js, await_promise=True)
            if not result_str:
                return {"error": "empty_response"}
            return json.loads(result_str)
        except TimeoutError:
            return {"error": CAPTURE_TIMEOUT}
        except Exception as e:
            return {"error": str(e)}
"""

# Apply the regex replacement for _fetch_store_page
import re
content = re.sub(r'    async def _fetch_store_page.*?(?=    # -+)', new_js, content, flags=re.DOTALL)

with open("src/dealhunter/providers/uber_eats/browser_transport.py", "w") as f:
    f.write(content)
