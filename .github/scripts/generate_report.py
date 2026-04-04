#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any


def load_json_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [x for x in parsed if isinstance(x, dict)]
        if isinstance(parsed, dict):
            return [parsed]
    except json.JSONDecodeError:
        pass

    records: list[dict[str, Any]] = []
    decoder = json.JSONDecoder()
    idx = 0
    raw_len = len(raw)
    while idx < raw_len:
        while idx < raw_len and raw[idx].isspace():
            idx += 1
        if idx >= raw_len:
            break
        try:
            item, next_idx = decoder.raw_decode(raw, idx)
            if isinstance(item, dict):
                records.append(item)
            idx = next_idx
        except json.JSONDecodeError:
            break
    return records


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def pick_top_star(stars: list[dict[str, Any]], updated: list[dict[str, Any]]) -> dict[str, Any]:
    if stars:
        return max(stars, key=lambda x: safe_int(x.get("stars")))
    if updated:
        return updated[0]
    return {}


def infer_hot_track_semantic(corpus: list[str]) -> str:
    default_track = "多智能体协作与自动化"
    if not corpus:
        return default_track
    try:
        from sentence_transformers import SentenceTransformer, util  # type: ignore
    except Exception:
        return default_track

    try:
        model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        anchors = {
            "多智能体协作与自动化": "multi-agent orchestration autonomous workflow automation",
            "AI 编码与开发效率": "coding assistant code generation developer tools",
            "RAG 与企业知识应用": "retrieval augmented generation enterprise knowledge base assistant",
            "Agent 基础设施平台": "agent platform runtime observability deployment infrastructure",
        }
        docs_emb = model.encode(corpus, convert_to_tensor=True, normalize_embeddings=True)
        anchor_labels = list(anchors.keys())
        anchor_texts = list(anchors.values())
        anchor_emb = model.encode(anchor_texts, convert_to_tensor=True, normalize_embeddings=True)
        sims = util.cos_sim(docs_emb, anchor_emb)
        votes = {label: 0 for label in anchor_labels}
        for row in sims:
            idx = int(row.argmax().item())
            votes[anchor_labels[idx]] += 1
        return max(votes.items(), key=lambda x: x[1])[0]
    except Exception:
        return default_track


def make_report(date: str, stars: list[dict[str, Any]], updated: list[dict[str, Any]], hf: list[dict[str, Any]]) -> str:
    top_star = pick_top_star(stars, updated)
    top_star_name = top_star.get("full_name") or top_star.get("name") or "N/A"
    top_star_desc = (top_star.get("desc") or "").strip()
    top_star_stars = safe_int(top_star.get("stars"))

    top_hf = max(hf, key=lambda x: safe_int(x.get("likes"))) if hf else {}
    top_hf_name = top_hf.get("id") or "N/A"

    corpus = []
    for row in stars + updated:
        text = " ".join(
            [
                str(row.get("name") or ""),
                str(row.get("full_name") or ""),
                str(row.get("desc") or ""),
            ]
        ).strip()
        if text:
            corpus.append(text)
    hot_track = infer_hot_track_semantic(corpus)

    opportunity_map = {
        "多智能体协作与自动化": "做“低代码任务编排+可观测”工具，帮助团队把分散流程变成可复用自动化流水线。",
        "AI 编码与开发效率": "做“垂直场景代码 Agent”，面向测试、运维、数据工程提供一键落地能力。",
        "RAG 与企业知识应用": "做“知识库接入与质量评估”层，解决企业上线后准确率与可追溯性痛点。",
        "Agent 基础设施平台": "做“模型路由+成本治理”平台，帮企业在效果与成本之间自动最优调度。",
    }
    insight_map = {
        "多智能体协作与自动化": "建议跟踪“任务完成率、回滚率、人工接管率”三指标，评估真实自动化价值。",
        "AI 编码与开发效率": "建议跟踪“端到端交付时长缩短率”和“缺陷逃逸率”，衡量生产力与质量平衡。",
        "RAG 与企业知识应用": "建议跟踪“检索命中率、答案可引用率、幻觉率”，量化知识系统可信度。",
        "Agent 基础设施平台": "建议跟踪“单位任务成本、时延分位数、成功率”，构建可运营的Agent SLA。",
    }

    star_line = f"今日之星：{top_star_name}（⭐{top_star_stars}）。"
    if top_star_desc:
        star_line += f" 项目描述：{top_star_desc}"
    else:
        star_line += " 项目描述：暂无公开描述。"

    lines = [
        f"今日AI Agent速览（{date}）",
        "",
        star_line,
        f"热门赛道：{hot_track}，从榜单信号看，市场在追求“可执行、可集成、可规模化”的真实生产力工具。",
        f"创业机会：{opportunity_map.get(hot_track, opportunity_map['多智能体协作与自动化'])}",
        f"科研与量化洞察：{insight_map.get(hot_track, insight_map['多智能体协作与自动化'])} 另，HuggingFace热度模型为 {top_hf_name}。",
    ]
    return "\n".join(lines).strip() + "\n"


def make_fallback(date: str, stars: list[dict[str, Any]], updated: list[dict[str, Any]], hf: list[dict[str, Any]]) -> str:
    top_star = pick_top_star(stars, updated)
    top_star_name = top_star.get("full_name") or top_star.get("name") or "N/A"
    top_active = updated[0] if updated else top_star
    top_updated_name = top_active.get("full_name") or top_active.get("name") or "N/A"
    top_hf_name = (max(hf, key=lambda x: safe_int(x.get("likes"))).get("id") if hf else "N/A")
    lines = [
        f"今日AI Agent速览（{date}，降级模式）",
        "",
        f"- GitHub 热门：{top_star_name}",
        f"- GitHub 活跃：{top_updated_name}",
        f"- HuggingFace 热门：{top_hf_name}",
        "",
        "说明：本次语义模型不可用，已使用本地统计摘要生成简版报告。",
    ]
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate daily AI agent report with local NLP.")
    parser.add_argument("--date", required=True)
    parser.add_argument("--stars", required=True)
    parser.add_argument("--updated", required=True)
    parser.add_argument("--hf", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    stars = load_json_records(Path(args.stars))
    updated = load_json_records(Path(args.updated))
    hf = load_json_records(Path(args.hf))

    try:
        report = make_report(args.date, stars, updated, hf)
    except Exception:
        report = make_fallback(args.date, stars, updated, hf)

    Path(args.output).write_text(report, encoding="utf-8")
    print(f"✅ Report generated: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
