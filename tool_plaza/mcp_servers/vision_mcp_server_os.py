# Copyright 2025 Miromind.ai
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import io
import logging
import os

import aiohttp
import requests
from fastmcp import FastMCP
from PIL import Image
from src.logging.logger import setup_mcp_logging

logger = logging.getLogger("miroflow")

VISION_API_KEY = os.environ.get("VISION_API_KEY")
VISION_BASE_URL = os.environ.get("VISION_BASE_URL")
VISION_MODEL_NAME = os.environ.get("VISION_MODEL_NAME")

# 图片大小限制（10MB）
MAX_IMAGE_SIZE = 10 * 1024 * 1024

# Initialize FastMCP server
setup_mcp_logging(tool_name=os.path.basename(__file__))
mcp = FastMCP("vision-mcp-server-os")


def guess_mime_media_type_from_extension(file_path: str) -> str:
    """Guess the MIME type based on the file extension."""
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    if ext in [".jpg", ".jpeg"]:
        return "image/jpeg"
    elif ext == ".png":
        return "image/png"
    elif ext == ".gif":
        return "image/gif"
    else:
        return "image/jpeg"  # Default to JPEG if unknown


def resize_image_if_needed(image_bytes: bytes, max_size: int = MAX_IMAGE_SIZE) -> tuple[bytes, str]:
    """Resize image if it exceeds max_size, maintaining aspect ratio.

    Args:
        image_bytes: Original image bytes
        max_size: Maximum size in bytes (default 10MB)

    Returns:
        Tuple of (resized_image_bytes, mime_type)
    """
    original_size = len(image_bytes)

    if original_size <= max_size:
        # No resize needed
        img = Image.open(io.BytesIO(image_bytes))
        mime_type = f"image/{img.format.lower()}" if img.format else "image/jpeg"
        return image_bytes, mime_type

    logger.info(f"Image too large ({original_size} bytes), resizing...")

    # Open image
    img = Image.open(io.BytesIO(image_bytes))
    original_format = img.format or "JPEG"
    original_width, original_height = img.size

    logger.info(f"Original dimensions: {original_width}x{original_height}, format: {original_format}")

    # Calculate resize ratio based on file size
    # Estimate: reduce dimensions by sqrt of size ratio
    size_ratio = original_size / max_size
    dimension_ratio = size_ratio ** 0.5

    # Calculate new dimensions
    new_width = int(original_width / dimension_ratio)
    new_height = int(original_height / dimension_ratio)

    # Ensure minimum dimensions
    min_dimension = 512
    if new_width < min_dimension or new_height < min_dimension:
        if new_width < new_height:
            new_width = min_dimension
            new_height = int(original_height * (min_dimension / original_width))
        else:
            new_height = min_dimension
            new_width = int(original_width * (min_dimension / original_height))

    logger.info(f"Resizing to: {new_width}x{new_height}")

    # Resize image
    img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Convert to RGB if necessary (for JPEG)
    if img_resized.mode in ("RGBA", "LA", "P"):
        if original_format.upper() == "JPEG":
            # Convert RGBA to RGB for JPEG
            background = Image.new("RGB", img_resized.size, (255, 255, 255))
            if img_resized.mode == "P":
                img_resized = img_resized.convert("RGBA")
            background.paste(img_resized, mask=img_resized.split()[-1] if img_resized.mode == "RGBA" else None)
            img_resized = background

    # Save to bytes with quality adjustment
    output = io.BytesIO()
    save_format = original_format.upper()

    if save_format == "JPEG" or save_format == "JPG":
        # Try different quality levels until size is acceptable
        for quality in [85, 75, 65, 55, 45]:
            output.seek(0)
            output.truncate()
            img_resized.save(output, format="JPEG", quality=quality, optimize=True)
            if len(output.getvalue()) <= max_size:
                break
        mime_type = "image/jpeg"
    elif save_format == "PNG":
        img_resized.save(output, format="PNG", optimize=True)
        mime_type = "image/png"
    else:
        # Default to JPEG for other formats
        if img_resized.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img_resized.size, (255, 255, 255))
            if img_resized.mode == "P":
                img_resized = img_resized.convert("RGBA")
            background.paste(img_resized, mask=img_resized.split()[-1] if img_resized.mode == "RGBA" else None)
            img_resized = background
        img_resized.save(output, format="JPEG", quality=85, optimize=True)
        mime_type = "image/jpeg"

    resized_bytes = output.getvalue()
    final_size = len(resized_bytes)

    logger.info(f"Resized image size: {final_size} bytes (reduced by {(1 - final_size/original_size)*100:.1f}%)")

    if final_size > max_size:
        logger.warning(f"Resized image still exceeds max size, but proceeding anyway")

    return resized_bytes, mime_type


@mcp.tool()
async def visual_question_answering(image_path_or_url: str, question: str) -> str:
    """Ask question about an image or a video and get the answer with a vision language model.

    Args:
        image_path_or_url: The path of the image file locally or its URL.
        question: The question to ask about the image.

    Returns:
        The answer to the image-related question.
    """
    logger.info(f"Vision tool called with image: {image_path_or_url[:100]}, question: {question[:100]}")

    messages_for_llm = [
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": None}},
                {
                    "type": "text",
                    "text": question,
                },
            ],
        }
    ]

    headers = {
        "Authorization": f"Bearer {VISION_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        # Check if it's a relative path (just filename) and provide helpful error
        if not image_path_or_url.startswith(('/', 'http://', 'https://', 'data:')):
            error_msg = (
                f"Error: Invalid image path '{image_path_or_url}'. "
                f"Please provide the FULL absolute path (e.g., /path/to/uploads/image.jpg), "
                f"not just the filename. Check the user's message for the complete path in format: "
                f"[附件: filename (文件路径: /full/path)]"
            )
            logger.error(error_msg)
            return error_msg

        if os.path.exists(image_path_or_url):  # Check if the file exists locally
            logger.info(f"Reading local image file: {image_path_or_url}")

            # 读取文件
            with open(image_path_or_url, "rb") as image_file:
                image_bytes = image_file.read()

            file_size = len(image_bytes)
            logger.info(f"Image file size: {file_size} bytes")

            # 如果图片过大，自动调整大小
            if file_size > MAX_IMAGE_SIZE:
                logger.info(f"Image exceeds max size, will resize automatically")
                image_bytes, mime_type = resize_image_if_needed(image_bytes, MAX_IMAGE_SIZE)
            else:
                mime_type = guess_mime_media_type_from_extension(image_path_or_url)

            # 编码为 base64
            image_data = base64.b64encode(image_bytes).decode("utf-8")
            messages_for_llm[0]["content"][0]["image_url"]["url"] = (
                f"data:{mime_type};base64,{image_data}"
            )
            logger.info(f"Image encoded, base64 length: {len(image_data)}, mime_type: {mime_type}")

        elif image_path_or_url.startswith(("http://", "https://")):
            logger.info(f"Downloading image from URL: {image_path_or_url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(image_path_or_url) as resp:
                    if resp.status == 200:
                        image_bytes = await resp.read()
                        logger.info(f"Downloaded image size: {len(image_bytes)} bytes")

                        # 如果图片过大，自动调整大小
                        if len(image_bytes) > MAX_IMAGE_SIZE:
                            logger.info(f"Downloaded image exceeds max size, will resize automatically")
                            image_bytes, mime_type = resize_image_if_needed(image_bytes, MAX_IMAGE_SIZE)
                        else:
                            mime_type = resp.headers.get("Content-Type", "image/png")

                        image_data = base64.b64encode(image_bytes).decode("utf-8")
                        messages_for_llm[0]["content"][0]["image_url"]["url"] = (
                            f"data:{mime_type};base64,{image_data}"
                        )
                        logger.info(f"Image encoded, base64 length: {len(image_data)}, mime_type: {mime_type}")
                    else:
                        error_msg = f"Failed to fetch image from URL (status {resp.status}): {image_path_or_url}"
                        logger.error(error_msg)
                        return error_msg

        elif "home/user" in image_path_or_url:
            return "The visual_question_answering tool cannot access to sandbox file, please use the local path provided by original instruction"
        else:
            # File doesn't exist and it's not a URL
            if not image_path_or_url.startswith(('http://', 'https://', 'data:')):
                error_msg = (
                    f"Error: Image file not found at path '{image_path_or_url}'. "
                    f"Please verify the file path is correct and the file exists. "
                    f"The path should be the absolute path returned from the upload endpoint."
                )
                logger.error(error_msg)
                return error_msg

            logger.warning(f"Using image path/URL as-is: {image_path_or_url}")
            messages_for_llm[0]["content"][0]["image_url"]["url"] = image_path_or_url

        payload = {"model": VISION_MODEL_NAME, "messages": messages_for_llm}

        logger.info(f"Sending request to {VISION_BASE_URL} with model {VISION_MODEL_NAME}")
        response = requests.post(VISION_BASE_URL, json=payload, headers=headers, timeout=120)

        logger.info(f"Response status code: {response.status_code}")

        if response.status_code != 200:
            error_msg = f"API Error ({response.status_code}): {response.text}"
            logger.error(error_msg)
            return error_msg

    except Exception as e:
        error_msg = f"Error: {e}"
        logger.error(error_msg, exc_info=True)
        return error_msg

    try:
        result = response.json()
        content = result["choices"][0]["message"]["content"]

        # 处理 Gemini 2.5 Pro 的响应格式：content 可能是字典 {'text': '...'}
        if isinstance(content, dict) and "text" in content:
            answer = content["text"]
        else:
            answer = content

        logger.info(f"Successfully got answer, length: {len(answer)}")
        return answer

    except (AttributeError, IndexError, KeyError) as e:
        error_msg = f"Failed to parse response: {e}, response: {response.json()}"
        logger.error(error_msg)
        return error_msg


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
