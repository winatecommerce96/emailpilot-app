"""
Image proxy API for handling CORS-blocked external images
"""
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
import httpx
import logging
from typing import Optional
from urllib.parse import unquote
import hashlib
import time

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/proxy", tags=["Proxy"])

# Simple in-memory cache for images (TTL: 1 hour)
image_cache = {}
CACHE_TTL = 3600  # 1 hour

@router.get("/image")
async def proxy_image(
    url: str = Query(..., description="URL of the image to proxy"),
    fallback: Optional[str] = Query(None, description="Fallback image path if fetch fails")
):
    """
    Proxy external images to avoid CORS issues.
    Commonly used for Google profile pictures (lh3.googleusercontent.com).
    """
    try:
        # Decode URL if encoded
        image_url = unquote(url)
        
        # Generate cache key
        cache_key = hashlib.md5(image_url.encode()).hexdigest()
        
        # Check cache
        if cache_key in image_cache:
            cached = image_cache[cache_key]
            if cached['timestamp'] + CACHE_TTL > time.time():
                logger.debug(f"Serving cached image for {image_url[:50]}...")
                return Response(
                    content=cached['content'],
                    media_type=cached['content_type'],
                    headers={
                        "Cache-Control": "public, max-age=3600",
                        "Access-Control-Allow-Origin": "*"
                    }
                )
            else:
                # Cache expired
                del image_cache[cache_key]
        
        # Fetch the image
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                image_url,
                headers={
                    "User-Agent": "EmailPilot/1.0",
                    "Accept": "image/*"
                },
                follow_redirects=True
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch image: {response.status_code} for {image_url[:50]}...")
                if fallback:
                    # Return a redirect to the fallback image
                    return Response(
                        status_code=302,
                        headers={"Location": fallback}
                    )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to fetch image: {response.status_code}"
                )
            
            content_type = response.headers.get("content-type", "image/jpeg")
            content = response.content
            
            # Cache the image
            image_cache[cache_key] = {
                'content': content,
                'content_type': content_type,
                'timestamp': time.time()
            }
            
            # Clean old cache entries (simple cleanup)
            if len(image_cache) > 100:
                # Remove oldest entries
                sorted_cache = sorted(image_cache.items(), key=lambda x: x[1]['timestamp'])
                for key, _ in sorted_cache[:20]:  # Remove 20 oldest
                    del image_cache[key]
            
            return Response(
                content=content,
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=3600",
                    "Access-Control-Allow-Origin": "*",
                    "X-Proxied-From": image_url[:50] + "..."
                }
            )
            
    except httpx.TimeoutException:
        logger.error(f"Timeout fetching image: {url[:50]}...")
        if fallback:
            return Response(
                status_code=302,
                headers={"Location": fallback}
            )
        raise HTTPException(status_code=504, detail="Image fetch timeout")
    except Exception as e:
        logger.error(f"Error proxying image: {e}")
        if fallback:
            return Response(
                status_code=302,
                headers={"Location": fallback}
            )
        raise HTTPException(status_code=500, detail="Failed to proxy image")

@router.get("/health")
async def proxy_health():
    """Health check endpoint for proxy service"""
    return {
        "status": "healthy",
        "cache_size": len(image_cache),
        "cache_ttl": CACHE_TTL
    }