"""OpenAI互換APIクライアント。

モデル・エンドポイント・コンテキスト長を DrafterConfig から受け取り、
チャット補完を呼び出す。
"""

from __future__ import annotations

import openai

from drafter.common.config import LLMConfig


class ReviewClient:
    """OpenAI互換APIへのチャットクライアント。"""

    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._client = openai.OpenAI(
            base_url=config.endpoint,
            api_key=config.api_key or "no-key",
        )

    def chat(self, messages: list[dict[str, str]]) -> str:
        """チャット補完を実行してレスポンステキストを返す。

        Args:
            messages: OpenAI messages 形式のリスト。

        Returns:
            モデルの応答テキスト。
        """
        response = self._client.chat.completions.create(
            model=self._config.model,
            messages=messages,  # type: ignore[arg-type]
        )
        content = response.choices[0].message.content
        return content if content is not None else ""
