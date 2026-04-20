"""
Claude API 封装 - 含 Prompt Caching 和重试机制
"""
import json
import os
from typing import Any

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from loguru import logger


class ClaudeClient:
    """封装 Claude API 调用，内置 Prompt Caching 和指数退避重试"""

    def __init__(self, model: str = "claude-opus-4-6", max_tokens: int = 4096):
        # 支持自定义 Base URL（代理地址）和 ANTHROPIC_AUTH_TOKEN 变量名
        api_key = (
            os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("ANTHROPIC_AUTH_TOKEN")
        )
        base_url = os.getenv("ANTHROPIC_BASE_URL")  # 如 https://xchai.xyz

        self.client = anthropic.Anthropic(
            api_key=api_key,
            **({"base_url": base_url} if base_url else {}),
        )
        self.model = model
        self.max_tokens = max_tokens

    @retry(
        retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIStatusError)),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def call(
        self,
        system_prompt: str,
        user_content: str,
        expect_json: bool = True,
    ) -> dict[str, Any] | str:
        """
        调用 Claude API。

        Prompt Caching 策略：
        - system_prompt 加 cache_control，所有 chunk 共享 → 缓存命中率最高
        - user_content（context_header + chunk 文本）每次不同 → 不缓存
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},  # 启用 Prompt Caching
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": user_content,
                }
            ],
        )

        # 记录缓存命中情况
        usage = response.usage
        logger.debug(
            f"Token 使用 | 输入: {usage.input_tokens} | "
            f"缓存创建: {getattr(usage, 'cache_creation_input_tokens', 0)} | "
            f"缓存命中: {getattr(usage, 'cache_read_input_tokens', 0)} | "
            f"输出: {usage.output_tokens}"
        )

        text = next((b.text for b in response.content if b.type == "text"), "")

        if not expect_json:
            return text

        # 提取 JSON（Claude 有时会在 JSON 前后加说明文字）
        return self._extract_json(text)

    def _extract_json(self, text: str) -> dict[str, Any]:
        """从响应文本中提取 JSON 对象"""
        text = text.strip()
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # 查找第一个 { 到最后一个 }
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        logger.warning(f"无法解析 JSON，返回原始文本: {text[:200]}")
        return {"raw": text}
