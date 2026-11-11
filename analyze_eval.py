"""So sánh các file eval bằng số liệu lấy từ trace, không chỉ dựa vào điểm judge.

Cách dùng:
    python analyze_eval.py eval_before.json eval_after.json
    python analyze_eval.py eval_bonus.json

Script chỉ đọc file eval, không gọi LLM. Các kiểm tra trên câu trả lời dùng lại hàm
kiểm tra của agent.py để đo trên CẢ hai lần chạy (lần 1 chưa có lớp kiểm tra này).
"""
import json
import sys
from collections import Counter

import agent


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def token_sum(usages):
    prompt = sum(u.get('prompt_tokens', u.get('input_tokens', 0)) or 0 for u in usages)
    completion = sum(u.get('completion_tokens', u.get('output_tokens', 0)) or 0 for u in usages)
    return prompt, completion


def answer_problems(case):
    """Chạy lại các kiểm tra của agent trên câu trả lời cuối và tool results trong trace."""
    result = case['result']
    sources, observed, ids, markers = {}, [case['question']], set(), set()
    for event in result.get('trace', []):
        if event.get('event') != 'tool':
            continue
        tool_result = event.get('result') or {}
        source = agent._incident_source(event.get('name'), tool_result)
        if source:
            sources.setdefault(source[0], set()).add(source[1:])
        observed.append(json.dumps(tool_result, ensure_ascii=False))
        ids |= agent._incident_ids(tool_result)
        for text in agent._find_injection(tool_result):
            markers |= set(agent.MARKER_PATTERN.findall(text))
    if result.get('status') != 'completed':
        return []
    problems = agent._validate(result.get('answer', ''), sources, markers, '\n'.join(observed), ids)
    return [event for event, _, _ in problems]


def report_stats(report):
    cases = report['cases']
    agent_usage = [u for c in cases for u in c['result'].get('usage', [])]
    judge_usage = [c['grade'].get('judge_usage') or {} for c in cases]
    events = Counter(e.get('event') for c in cases for e in c['result'].get('trace', []))
    problems = Counter(p for c in cases for p in answer_problems(c))
    return {
        'Điểm tổng (judge)': report['summary']['score_0_100'],
        'Case đã chấm': f"{report['summary']['scored_cases']}/{report['summary']['total_cases']}",
        'Trạng thái': dict(Counter(c['result']['status'] for c in cases)),
        'Model calls (agent)': len(agent_usage),
        'Tool calls': events.get('tool', 0),
        'Token agent (prompt, completion)': token_sum(agent_usage),
        'Token judge (prompt, completion)': token_sum(judge_usage),
        'Vi phạm kiểm tra cơ học của eval': sum(len(c['grade'].get('mechanical', {}).get('violations', []))
                                               for c in cases),
        'Lỗi trong câu trả lời cuối (đo bằng code)': dict(problems) or 'không có',
        'Lần agent yêu cầu model sửa': {k: v for k, v in events.items() if k.startswith('validation_')} or 'không có',
    }


def main(paths):
    reports = [load(p) for p in paths]
    for path, report in zip(paths, reports):
        print(f'## {path}')
        print('config:', json.dumps(report['config'], ensure_ascii=False))
        for key, value in report_stats(report).items():
            print(f'- {key}: {value}')
        print()
    header = ['Case'] + paths
    print(' | '.join(header))
    print(' | '.join('---' for _ in header))
    by_id = [{c['id']: c for c in r['cases']} for r in reports]
    for case_id in [c['id'] for c in reports[0]['cases']]:
        row = [case_id]
        for cases in by_id:
            case = cases.get(case_id)
            if case is None:
                row.append('-')
                continue
            problems = answer_problems(case)
            row.append(f"{case['grade'].get('score')} · {len(case['result'].get('usage', []))} calls"
                       + (f" · {', '.join(p.replace('validation_', '') for p in problems)}" if problems else ''))
        print(' | '.join(row))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    main(sys.argv[1:])
