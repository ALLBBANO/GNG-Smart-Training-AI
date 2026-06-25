from http.server import BaseHTTPRequestHandler
import json, os, anthropic
from supabase import create_client

def get_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)

EVAL_CRITERIA = """
당신은 백화점 고객응대 교육 전문가입니다. 아래 대화를 평가해주세요.

## 평가 기준 (100점 만점)
1. 고객 공감 및 경청 (30점): 고객 감정을 인정하고 경청하는 태도
2. 문제 해결 능력 (30점): 적절하고 현실적인 해결책 제시
3. 매장 정책 준수 (20점): 규정 내에서 처리, 무리한 요구 정중히 거절
4. 전문성 및 태도 (20점): 정중하고 침착한 언어 사용, 감정적 대응 자제

## 응답 형식 (반드시 이 형식으로만)
등급: [A/B/C]
점수: [0-100 숫자만]
피드백: [3~5문장으로 구체적 피드백. 잘한 점과 개선점 모두 포함]
"""

def rule_evaluate(messages: list, difficulty: int) -> dict:
    """규칙 기반 1차 평가"""
    if not messages:
        return {"score": 0, "grade": "C", "feedback": "대화 기록이 없습니다."}
    
    staff_msgs = [m["content"] for m in messages if m["role"] == "user"]
    if not staff_msgs:
        return {"score": 0, "grade": "C", "feedback": "직원 응답이 없습니다."}
    
    score = 50  # 기본 점수
    
    # 공감 표현 체크
    empathy_words = ["죄송", "불편", "이해", "공감", "안타깝", "걱정", "힘드셨", "불쾌"]
    empathy_count = sum(1 for msg in staff_msgs for w in empathy_words if w in msg)
    score += min(empathy_count * 5, 20)
    
    # 해결책 제시 체크
    solution_words = ["확인", "처리", "도와", "해결", "조치", "안내", "대신", "바꿔"]
    solution_count = sum(1 for msg in staff_msgs for w in solution_words if w in msg)
    score += min(solution_count * 4, 15)
    
    # 정중한 언어 체크
    polite_words = ["고객님", "말씀", "주시면", "드리겠", "부탁", "감사"]
    polite_count = sum(1 for msg in staff_msgs for w in polite_words if w in msg)
    score += min(polite_count * 3, 15)
    
    # 부정적 표현 감점
    negative_words = ["안돼요", "못해요", "규정상", "어쩔 수 없", "몰라요"]
    negative_count = sum(1 for msg in staff_msgs for w in negative_words if w in msg)
    score -= negative_count * 5
    
    # 난이도 보정
    score += (difficulty - 1) * 2
    score = max(0, min(100, score))
    
    grade = "A" if score >= 85 else ("B" if score >= 70 else "C")
    
    feedbacks = {
        "A": "전반적으로 훌륭한 응대였습니다. 고객 공감과 문제 해결이 균형 있게 이루어졌습니다.",
        "B": "기본적인 응대는 잘 되었으나, 고객 감정에 더 공감하는 표현이 필요합니다.",
        "C": "응대 기술을 더 연습해야 합니다. 공감 표현과 구체적인 해결책 제시를 강화하세요.",
    }
    
    return {"score": score, "grade": grade, "feedback": feedbacks[grade]}


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        
        session_id = body.get("session_id", "")
        job_type   = body.get("job_type", "general")
        difficulty = int(body.get("difficulty", 1))
        messages   = body.get("messages", [])
        scenario   = body.get("scenario", {})
        
        # Claude API로 정밀 평가
        try:
            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            
            conv_text = "\n".join([
                f"{'고객(AI)' if m['role']=='assistant' else '직원(피훈련자)'}: {m['content']}"
                for m in messages
            ])
            
            scenario_text = f"""
직무: {job_type}
난이도: Level {difficulty}
시나리오: {scenario.get('situation', '')}
고객유형: {scenario.get('customer_type', '')}
"""
            
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=500,
                system=EVAL_CRITERIA,
                messages=[{
                    "role": "user",
                    "content": f"시나리오 정보:\n{scenario_text}\n\n대화 내용:\n{conv_text}"
                }]
            )
            
            eval_text = response.content[0].text
            
            # 파싱
            import re
            grade_m = re.search(r"등급:\s*([ABC])", eval_text)
            score_m = re.search(r"점수:\s*(\d+)", eval_text)
            feed_m  = re.search(r"피드백:\s*([\s\S]+?)$", eval_text)
            
            grade    = grade_m.group(1) if grade_m else "C"
            score    = int(score_m.group(1)) if score_m else 60
            feedback = feed_m.group(1).strip() if feed_m else eval_text
            
        except Exception as e:
            print(f"AI eval error: {e}", flush=True)
            result = rule_evaluate(messages, difficulty)
            grade, score, feedback = result["grade"], result["score"], result["feedback"]
        
        # DB 저장
        try:
            sb = get_supabase()
            sb.table("gst_sessions").update({
                "score": score,
                "grade": grade,
                "feedback": feedback,
                "messages": messages,
                "scenario_context": scenario,
                "completed_at": "now()",
            }).eq("id", session_id).execute()
        except Exception as e:
            print(f"DB update error: {e}", flush=True)
        
        self._respond(200, {"grade": grade, "score": score, "feedback": feedback})
    
    def _respond(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def log_message(self, format, *args):
        pass
