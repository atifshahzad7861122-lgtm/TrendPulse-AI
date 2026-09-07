"""Extensible hook pipeline for crawl lifecycle events."""

from typing import Any, Awaitable, Callable, Dict, List, Optional

from app.crawling.models import CrawlRequest, CrawlResponse, UniversalCrawlResult
from app.core.logging import logger

# Hook type aliases
BeforeRequestHook = Callable[[CrawlRequest], Awaitable[Optional[CrawlRequest]]]
AfterRequestHook = Callable[[CrawlRequest, CrawlResponse], Awaitable[Optional[CrawlResponse]]]
OnChallengeHook = Callable[[CrawlRequest, CrawlResponse, str], Awaitable[None]]
OnErrorHook = Callable[[CrawlRequest, Exception], Awaitable[None]]
OnResultHook = Callable[[UniversalCrawlResult], Awaitable[Optional[UniversalCrawlResult]]]


class CrawlHookPipeline:
    """
    Manages registration and ordered async execution of lifecycle hooks during crawling.
    """

    def __init__(self):
        self._before_request_hooks: List[BeforeRequestHook] = []
        self._after_request_hooks: List[AfterRequestHook] = []
        self._on_challenge_hooks: List[OnChallengeHook] = []
        self._on_error_hooks: List[OnErrorHook] = []
        self._on_result_hooks: List[OnResultHook] = []

    def register_before_request(self, hook: BeforeRequestHook) -> None:
        self._before_request_hooks.append(hook)

    def register_after_request(self, hook: AfterRequestHook) -> None:
        self._after_request_hooks.append(hook)

    def register_on_challenge(self, hook: OnChallengeHook) -> None:
        self._on_challenge_hooks.append(hook)

    def register_on_error(self, hook: OnErrorHook) -> None:
        self._on_error_hooks.append(hook)

    def register_on_result(self, hook: OnResultHook) -> None:
        self._on_result_hooks.append(hook)

    async def execute_before_request(self, request: CrawlRequest) -> CrawlRequest:
        curr = request
        for hook in self._before_request_hooks:
            try:
                res = await hook(curr)
                if res is not None:
                    curr = res
            except Exception as e:
                logger.warning(f"Error in before_request hook: {e}")
        return curr

    async def execute_after_request(self, request: CrawlRequest, response: CrawlResponse) -> CrawlResponse:
        curr = response
        for hook in self._after_request_hooks:
            try:
                res = await hook(request, curr)
                if res is not None:
                    curr = res
            except Exception as e:
                logger.warning(f"Error in after_request hook: {e}")
        return curr

    async def execute_on_challenge(self, request: CrawlRequest, response: CrawlResponse, reason: str) -> None:
        for hook in self._on_challenge_hooks:
            try:
                await hook(request, response, reason)
            except Exception as e:
                logger.warning(f"Error in on_challenge hook: {e}")

    async def execute_on_error(self, request: CrawlRequest, exc: Exception) -> None:
        for hook in self._on_error_hooks:
            try:
                await hook(request, exc)
            except Exception as e:
                logger.warning(f"Error in on_error hook: {e}")

    async def execute_on_result(self, result: UniversalCrawlResult) -> UniversalCrawlResult:
        curr = result
        for hook in self._on_result_hooks:
            try:
                res = await hook(curr)
                if res is not None:
                    curr = res
            except Exception as e:
                logger.warning(f"Error in on_result hook: {e}")
        return curr
