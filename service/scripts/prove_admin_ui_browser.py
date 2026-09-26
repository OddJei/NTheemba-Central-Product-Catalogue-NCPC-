"""Drive the NCPC-07 same-origin UI in disposable local Chrome via CDP."""
# ruff: noqa: E501

from __future__ import annotations

import asyncio
import base64
import json
import uuid
from pathlib import Path
from typing import Any
from urllib.request import urlopen

import websockets

DEBUG_URL = "http://127.0.0.1:9222/json"
ADMIN_TOKEN = "ncpc-proof-bootstrap-token-local-only"
OUT_DIR = Path(__file__).resolve().parents[3] / "output" / "playwright"


async def prove() -> None:
    targets = json.loads(urlopen(DEBUG_URL, timeout=10).read())
    target = next(item for item in targets if item["type"] == "page" and "/admin" in item["url"])
    async with websockets.connect(target["webSocketDebuggerUrl"], max_size=2**24) as socket:
        request_id = 0

        async def call(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
            nonlocal request_id
            request_id += 1
            current_id = request_id
            await socket.send(json.dumps({"id": current_id, "method": method, "params": params or {}}))
            while True:
                response = json.loads(await asyncio.wait_for(socket.recv(), timeout=25))
                if response.get("id") == current_id:
                    assert "error" not in response, response
                    return response["result"]

        async def evaluate(expression: str) -> Any:
            response = await call("Runtime.evaluate", {"expression": expression, "awaitPromise": True, "returnByValue": True})
            result = response["result"]
            assert "exceptionDetails" not in result, result
            return result.get("value")

        await call("Page.enable")
        await evaluate(
            f"localStorage.ncpcToken={json.dumps(ADMIN_TOKEN)}; "
            "location.href='http://127.0.0.1:8097/admin'; 'navigated'"
        )
        await asyncio.sleep(4)
        required = [
            "Dashboard", "Review Queue", "Review Workspace", "Catalogue Search", "Product Detail",
            "Variant Detail", "Barcode Claims / Conflict Review", "Duplicate / Merge Review",
            "Publications / Release History", "BusinessCoverage", "Audit",
        ]
        text = await evaluate("document.body.innerText")
        assert all(screen in text for screen in required), text

        browser_ref = f"NCPC07-UI-BROWSER-{uuid.uuid4().hex[:10]}"
        submission = await evaluate(f"""
            document.querySelector('#submitRef').value={json.dumps(browser_ref)};
            document.querySelector('#submitName').value='NCPC07 Browser Canonical';
            document.querySelector('#submitVariant').value='NCPC07 Browser 500 ml';
            document.querySelector('button[onclick=\"submitProduct()\"]').click();
            new Promise(resolve => setTimeout(() => resolve(JSON.parse(document.querySelector('#out').textContent)), 800));
        """)
        assert submission["success"] is True, submission
        review_id = submission["data"]["review_id"]

        review = await evaluate(f"""
            show('Review Workspace'); document.querySelector('#reviewId').value={json.dumps(review_id)};
            Array.from(document.querySelectorAll('button')).find(button => button.textContent === 'Open selected review').click();
            new Promise(resolve => setTimeout(() => resolve(JSON.parse(document.querySelector('#out').textContent)), 500));
        """)
        assert review["data"]["review_id"] == review_id

        decision = await evaluate("""
            show('Review Queue'); document.querySelector('#outcome').value='APPROVE_NEW';
            document.querySelector('#rationale').value='synthetic browser workflow verified';
            document.querySelector('button[onclick=\"decide()\"]').click();
            new Promise(resolve => setTimeout(() => resolve(JSON.parse(document.querySelector('#out').textContent)), 800));
        """)
        assert decision["success"] is True and "ncpc_product_id" in decision["data"], decision
        product_id, variant_id = decision["data"]["ncpc_product_id"], decision["data"]["ncpc_variant_id"]

        published = await evaluate("""
            show('Publications / Release History'); document.querySelector('#releaseVersion').value='NCPC07-UI-BROWSER-R1';
            publish(); new Promise(resolve => setTimeout(() => resolve(JSON.parse(document.querySelector('#out').textContent)), 800));
        """)
        assert published["success"] is True, published

        product = await evaluate(f"""
            show('Product Detail'); document.querySelector('#productId').value={json.dumps(product_id)};
            product(); new Promise(resolve => setTimeout(() => resolve(JSON.parse(document.querySelector('#out').textContent)), 500));
        """)
        assert product["success"] is True and product["data"]["ncpc_product_id"] == product_id, product

        searched = await evaluate(f"""
            show('Catalogue Search'); document.querySelector('#query').value={json.dumps(product_id)};
            search(); new Promise(resolve => setTimeout(() => resolve(JSON.parse(document.querySelector('#out').textContent)), 500));
        """)
        assert searched["data"]["candidates"][0]["ncpc_variant_id"] == variant_id

        verified = await evaluate(f"""
            show('Variant Detail'); document.querySelector('#productId').value={json.dumps(product_id)};
            document.querySelector('#variantId').value={json.dumps(variant_id)};
            verify(); new Promise(resolve => setTimeout(() => resolve(JSON.parse(document.querySelector('#out').textContent)), 500));
        """)
        assert verified["data"]["ncpc_variant_id"] == variant_id

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        desktop = await call("Page.captureScreenshot", {"format": "png"})
        (OUT_DIR / "ncpc07-admin-desktop.png").write_bytes(base64.b64decode(desktop["data"]))
        await call("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True})
        mobile = await call("Page.captureScreenshot", {"format": "png"})
        (OUT_DIR / "ncpc07-admin-mobile.png").write_bytes(base64.b64decode(mobile["data"]))
        print(f"NCPC_SERVICE_ALIGNED_ADMIN_UI_RUNTIME_READY {product_id} {variant_id}")


if __name__ == "__main__":
    asyncio.run(prove())
