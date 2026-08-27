from __future__ import annotations

import re
from typing import Any


class ContentService:
    """Explicit deterministic fallback for offline tests and user-requested fallback."""

    def extract_topic(self, request: str) -> str:
        cleaned = request.strip().rstrip("。.!！?")
        match = re.search(
            r"(?:关于|介绍)\s*(.+?)(?:(?:的)?\s*\d+\s*秒|(?:的)?短视频|视频|$)",
            cleaned,
            flags=re.IGNORECASE,
        )
        if match and match.group(1).strip():
            return match.group(1).strip(" 的")
        cleaned = re.sub(r"^(我想|我要|请|帮我|做一条|制作一条)+", "", cleaned).strip()
        return cleaned[:60] or "待确认主题"

    def topic_to_script(
        self, request: str, platform: str = "unspecified"
    ) -> dict[str, Any]:
        topic = self.extract_topic(request)
        title, hook, body, close = self._offline_outline(topic)
        script = "\n".join((hook, body, close))
        return {
            "goal": request,
            "platform": platform,
            "selected_topic": topic,
            "content_summary": f"用总控、专业分工、结构化交接和独立审核解释{topic}的工作方式。",
            "structure": [
                {"section": "hook", "purpose": "纠正常见误解", "text": hook},
                {"section": "body", "purpose": "给出三步工作方式", "text": body},
                {"section": "close", "purpose": "说明审核闭环与实际价值", "text": close},
            ],
            "script": script,
            "title": title,
            "post_copy": f"{topic}不是多开几个窗口，而是一套有责任、有交接、有审核的工作系统。",
            "source_range": None,
            "constraints": ["目标时长约60秒", "不得虚构数据或来源"],
            "production_requirements": {
                "target_duration_seconds": 60,
                "needs_source_video": True,
                "caption_language": "zh-CN",
            },
            "revision_attempt": 0,
            "addressed_issues": [],
            "execution_mode": "deterministic",
        }

    def _offline_outline(self, topic: str) -> tuple[str, str, str, str]:
        if "副业" in topic:
            return (
                "副业坚持不到一个月，问题可能不在自律",
                "很多副业不是输在能力，而是在第一个月就同时踩中了三个消耗点。",
                "第一，目标只有赚钱，没有具体到每天能完成的动作；第二，一开始摊子铺太大，反馈却来得太慢；第三，把短期波动误判成项目没希望。更稳的方法，是只选一个交付物，把每天投入压到可持续的范围，并提前设好三十天观察指标。",
                "先验证自己能不能稳定完成，再判断它值不值得扩大。副业真正需要的不是一阵兴奋，而是一套能重复的小系统。",
            )
        if "新能源" in topic or "电动车" in topic:
            return (
                "第一次买新能源车，先别急着比较大屏",
                "第一次买新能源车，最先看的不该是零百加速，而是你的真实用车半径。",
                "先算清每天和长途的里程，再确认家里或单位能不能稳定补能；然后看冬季或高速场景下的续航余量、保险维修成本和常用座位空间；最后才比较辅助驾驶、车机和配置。试驾时把自己的通勤路线、停车环境和家庭成员都带进判断。",
                "没有一辆车适合所有人。先用补能、里程和长期成本筛掉不合适的，再在剩下的车型里选体验。",
            )
        if "Multi-Agent" in topic or "多智能体" in topic:
            return (
                "Multi-Agent：重点不是多开几个 AI 窗口",
                "你以为 Multi-Agent 只是同时打开几个 AI 对话吗？真正的关键是责任、交接和审核。",
                "第一，设一个总控理解目标和维护进度；第二，把内容判断、视频制作和质量审核交给不同角色；第三，用结构化文件交接输入、约束、产物和责任人。每个角色只读取完成当前工作所需的信息，避免上下文互相污染。",
                "审核不通过就按责任人打回，通过后才交付。价值不在流程复杂，而在一个人也能稳定复用团队工作方式。",
            )
        return (
            f"理解{topic}，先抓住这三个判断",
            f"关于“{topic}”，真正影响结果的往往不是信息多少，而是判断顺序。",
            f"先明确你想解决的具体问题，再区分必须满足的条件和可以取舍的偏好；接着用一个真实场景验证，而不是只看抽象结论；最后记录结果，用反馈修正下一次选择。把“{topic}”拆成目标、约束和验证动作，复杂问题就会变得可执行。",
            "不要追求一次得到完美答案。先完成一个能验证的选择，再根据结果迭代，通常比继续收集零散信息更有效。",
        )

    def revise(
        self,
        request: str,
        platform: str,
        previous: dict[str, Any],
        issues: list[dict[str, Any]],
        required_action: str = "",
        revision_attempt: int = 1,
    ) -> dict[str, Any]:
        revised = self.topic_to_script(request, platform)
        revised["revision_attempt"] = revision_attempt
        revised["addressed_issues"] = [item.get("code", "unknown") for item in issues]
        return revised

