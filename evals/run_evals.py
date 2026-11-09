"""Run each eval in a fresh snapshot; writes evidence, does not auto-grade answer quality."""
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent import run_agent
from providers import Provider
from scenarios import ScenarioTools


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--provider', choices=['openai', 'gemini', 'removed-provider', 'openrouter'], default=os.getenv('PROVIDER', 'openai'))
    parser.add_argument('--model', default=os.getenv('MODEL'))
    parser.add_argument('--case', help='Ví dụ E2; bỏ trống để chạy cả bộ')
    parser.add_argument('--output', default='eval_results.json')
    args = parser.parse_args()
    cases = json.loads((Path(__file__).parent / 'cases.json').read_text())
    selected = [case for case in cases if not args.case or case['id'] == args.case.upper()]
    if not selected:
        parser.error('Không tìm thấy case')
    if not args.model:
        parser.error('Thiếu --model hoặc MODEL')
    results = []
    for case in selected:
        print('Đang chạy', case['id'], flush=True)
        try:
            result = run_agent(case['question'], Provider(args.provider, args.model), ScenarioTools(case.get('scenario', 'normal'), case.get('fail', False)), max_steps=8)
        except (ValueError, RuntimeError, NotImplementedError) as exc:
            result = {'status': 'error', 'answer': '', 'trace': [], 'usage': [], 'error': str(exc)}
        if result['status'] != 'completed':
            print(f"  {case['id']}: {result['status']} — {result.get('error', 'chưa hoàn tất')}", file=sys.stderr)
        results.append({'id': case['id'], 'question': case['question'], 'expected': case['expected'], 'scenario': case.get('scenario', 'normal'), 'provider': args.provider, 'model': args.model, 'result': result, 'manual_score': None})
    Path(args.output).write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
    print(f'Đã lưu {args.output}. Chỉ tự chấm case đã hoàn tất theo RUBRIC.md; chất lượng câu trả lời chưa được chấm tự động.')
    return 1 if any(x['result']['status'] != 'completed' for x in results) else 0

if __name__ == '__main__':
    sys.exit(main())
