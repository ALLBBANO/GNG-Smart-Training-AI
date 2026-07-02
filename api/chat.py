from http.server import BaseHTTPRequestHandler
import json, os, random, anthropic

# ── 직무 정보 ──────────────────────────────────────────────────────────────────
JOB_INFO = {
    "cashier":   {"name": "캐셔",         "place": "계산대"},
    "vegetable": {"name": "야채/과일",    "place": "신선식품 코너"},
    "seafood":   {"name": "수산",         "place": "수산물 코너"},
    "meat":      {"name": "정육",         "place": "정육 코너"},
    "cs":        {"name": "고객상담실",   "place": "고객상담실"},
    "vip":       {"name": "VIP 라운지",  "place": "VIP 라운지"},
    "rental":    {"name": "유모차/휠체어","place": "대여 서비스 데스크"},
    "general":   {"name": "일반 응대",    "place": "매장 안내 데스크"},
}

# ── 직무별 시나리오 ────────────────────────────────────────────────────────────
JOB_SITUATIONS = {
    "cashier": {
        1: ["영수증 재발급 요청", "포인트 적립 방법 문의", "상품권 사용 방법 문의", "할인쿠폰 적용 방법 문의", "결제 수단 변경 문의"],
        2: ["영수증 금액이 가격표랑 다르다고 항의", "카드가 이중결제 됐다고 주장", "쿠폰이 적용 안 됐다고 항의", "포인트가 안 쌓였다고 항의", "거스름돈이 잘못됐다고 항의"],
        3: ["계산이 틀렸다며 환불 강하게 요구", "카드 취소하고 현금으로 환불 요구", "영수증 없이 환불 요구", "행사 할인 적용 안 됐다며 강하게 항의"],
        4: ["카드 정보 유출됐다며 매장 탓", "이중결제로 큰돈 손해봤다며 보상 요구", "직원이 거스름돈 빼돌렸다고 주장", "영수증 조작 의심하며 책임자 요구"],
        5: ["카드사에 신고하겠다며 협박", "직원 촬영하며 SNS에 올리겠다고 협박", "경찰 부르겠다며 소란", "본사 고발하겠다며 집단 보상 요구"],
    },
    "vegetable": {
        1: ["특정 과일 입고 여부 문의", "유기농 상품 위치 문의", "과일 고르는 법 문의", "산지 및 원산지 문의", "보관 방법 문의"],
        2: ["산 딸기에 곰팡이가 있다고 항의", "가격표랑 실제 가격이 다르다고 항의", "유통기한이 며칠 안 남은 채소 발견", "포장이 터진 채로 판매됐다고 항의"],
        3: ["상한 과일 먹고 탈이 났다고 주장", "광고보다 품질이 나쁘다며 항의", "다른 마트가 더 싸다며 항의", "행사 상품 물량이 없다며 강하게 항의"],
        4: ["상한 과일로 아이가 아팠다며 보상 요구", "원산지 표기 잘못됐다며 법적 대응 언급", "알레르기 반응 났다며 책임 추궁", "전부 상했다며 전액 환불 요구"],
        5: ["식품위생법 위반 신고하겠다며 협박", "상한 과일 사진 SNS에 올리겠다며 협박", "방송국에 제보하겠다며 과도한 보상 요구", "집단 소송 언급하며 매장 앞 소란"],
    },
    "seafood": {
        1: ["생선 손질 방법 문의", "오늘 들어온 신선한 생선 추천 요청", "조개 보관 방법 문의", "제철 수산물 문의", "회 포장 방법 문의"],
        2: ["생선에서 냄새가 심하게 난다고 항의", "새우에 이물질이 있다고 항의", "가격표와 실제 가격이 다르다고 항의", "손질 잘못됐다고 항의"],
        3: ["상한 생선 먹고 배탈났다고 주장", "비린내 심하다며 환불 요구", "원산지가 다르다며 강하게 항의", "오늘 산 게가 죽어있다며 항의"],
        4: ["생선 먹고 가족 식중독 걸렸다며 보상 요구", "원산지 허위표기로 신고하겠다고 협박", "활어가 죽어있었다며 큰 보상 요구", "납품 비리 의심하며 책임자 요구"],
        5: ["식중독 입원했다며 거액 보상 요구", "보건소 신고하겠다며 영업 방해", "방송 제보로 매장 폐쇄시키겠다고 협박", "집단 소송 언급하며 과도한 합의금 요구"],
    },
    "meat": {
        1: ["삼겹살 두께 조절 요청", "부위별 요리법 문의", "오늘 들어온 신선한 고기 추천 요청", "1인분 적정 양 문의", "숙성육 차이 문의"],
        2: ["고기 색이 이상하다고 항의", "포장 무게가 표기랑 다르다고 항의", "등급 표시가 이상하다고 항의", "원하는 부위로 교체 요청"],
        3: ["상한 고기 먹고 탈이 났다고 주장", "등급 속여서 팔았다며 항의", "유통기한 지난 고기 판매됐다며 항의", "비싸게 잘못 계산됐다며 환불 요구"],
        4: ["상한 고기로 온 가족 식중독 걸렸다며 보상 요구", "등급 허위표시로 신고하겠다고 협박", "대부분 상했다며 전액 환불 요구", "납품 비리 의심하며 책임자 호출"],
        5: ["식중독 병원 입원했다며 거액 보상 요구", "식품위생 당국 신고하겠다며 영업 방해", "방송국 제보로 매장 폐쇄시키겠다고 협박", "법적 소송 언급하며 과도한 합의금 요구"],
    },
    "cs": {
        1: ["멤버십 포인트 조회 요청", "주차 무료 시간 문의", "분실물 접수 문의", "행사 기간 및 내용 문의", "영업 시간 문의"],
        2: ["포인트 소멸됐다고 복구 요청", "주차 요금 과다 청구 항의", "온라인 주문 배송 지연 항의", "교환/환불 절차 불만"],
        3: ["직원 불친절 민원 강하게 제기", "환불 규정이 불합리하다며 항의", "멤버십 등급 강등됐다며 항의", "약속된 서비스 못 받았다며 강하게 항의"],
        4: ["직원 해고 요구하며 강하게 항의", "법적 대응 언급하며 보상 요구", "개인정보 유출 의심하며 책임 추궁", "담당자 바꾸라며 계속 요구"],
        5: ["소비자원 신고하겠다며 협박", "SNS로 매장 망하게 하겠다고 협박", "집단 민원 조직하겠다고 협박", "언론 제보하겠다며 과도한 보상 요구"],
    },
    "vip": {
        1: ["VIP 라운지 이용 횟수 및 동반 입장 인원 문의", "발레파킹 이용 방법 문의", "VIP 전용 행사 초청 여부 문의", "퍼스널 쇼퍼 서비스 예약 방법 문의", "라운지 음료/다과 메뉴 문의"],
        2: ["발레파킹 대기가 너무 길다고 항의", "이번 달 라운지 이용 횟수가 다 찼다고 항의", "VIP인데 라운지 입장이 거절됐다고 항의", "명절 선물 품질이 작년보다 떨어졌다고 항의", "포인트가 예상보다 적게 쌓였다고 항의"],
        3: ["일반 고객과 같은 라운지를 쓴다며 강하게 항의", "라운지 직원 응대가 불친절했다며 항의", "VIP 전용 행사에 초청받지 못했다며 항의", "등급 대비 혜택이 너무 적다며 강하게 항의", "라운지 대기줄이 너무 길다며 강하게 항의"],
        4: ["VIP 등급 강등됐다며 강력 항의 및 보상 요구", "타 백화점 VIP 서비스와 비교하며 혜택 개선 압박", "발레파킹 차량에 스크래치 났다며 보상 요구", "퍼스널 쇼퍼 서비스 수준이 너무 낮다며 책임자 요구"],
        5: ["VIP 탈퇴 선언하며 주변 VIP 회원 이탈 협박", "SNS에 VIP 서비스 실태 폭로하겠다고 협박", "본사 임원에게 직접 민원 넣겠다고 협박", "소비자원에 VIP 등급 조작 신고하겠다고 협박"],
    },
    "rental": {
        1: ["유모차 대여 방법 문의", "휠체어 크기 및 종류 문의", "대여 가능 시간 문의", "보증금 반환 방법 문의", "대여 가능 여부 확인"],
        2: ["반납 기한 초과 요금 이의 제기", "대여한 유모차 바퀴가 불량이라고 항의", "보증금이 반환이 안 됐다고 항의", "대여증 분실했다고 당황하며 문의"],
        3: ["유모차 불량으로 아이가 다칠 뻔 했다고 항의", "반납했는데 요금이 계속 청구된다고 강하게 항의", "휠체어 고장으로 어르신이 불편했다며 항의", "대여 가능하다고 했는데 막상 없었다며 항의"],
        4: ["유모차 결함으로 아이가 다쳤다며 보상 요구", "보증금 안 돌려준다며 법적 대응 언급", "안전 불량 제품 대여했다며 책임자 요구", "휠체어 고장으로 어르신 낙상했다며 보상 요구"],
        5: ["아이 부상으로 거액 보상 요구하며 소란", "소비자원 신고하겠다며 협박", "안전 불량 제품 SNS에 공론화하겠다고 협박", "집단 소송 언급하며 과도한 합의 요구"],
    },
    "general": {
        1: ["화장실 위치 문의", "층별 매장 안내 요청", "셔틀버스 시간 문의", "분실물 보관 위치 문의", "행사장 위치 문의"],
        2: ["안내받은 매장 위치가 달랐다고 항의", "주차 정산 오류 항의", "엘리베이터 고장으로 불편 항의", "안내판이 잘못됐다고 항의"],
        3: ["직원이 불친절했다며 강하게 항의", "매장이 너무 복잡해서 길 잃었다며 항의", "안내 방송이 잘못됐다며 항의", "장애인 편의시설이 부족하다며 항의"],
        4: ["매장 내 사고로 부상 주장하며 보상 요구", "안전시설 미비로 법적 대응 언급", "아이가 매장 시설에 다쳤다며 보상 요구", "직원 폭언 주장하며 책임자 요구"],
        5: ["매장 사고로 거액 보상 요구하며 소란", "안전 불량으로 관할 기관 신고 협박", "SNS 공론화로 매장 이미지 망치겠다고 협박", "집단 민원으로 영업 방해 협박"],
    },
}

# ── 고객 유형 ──────────────────────────────────────────────────────────────────
CUSTOMER_TYPES = [
    {"type": "급한 직장인(30대)", "desc": "점심시간에 온 바쁜 30대 직장인. 말이 빠르고 짧게 끊어서 말함. '빨리요', '시간 없어요' 자주 씀"},
    {"type": "꼼꼼한 주부(40대)", "desc": "영수증과 상품을 꼼꼼히 따지는 40대 주부. 논리적으로 조목조목 따지며 근거를 요구함"},
    {"type": "어르신(70대)", "desc": "70대 어르신. 말이 느리고 같은 말 반복. '아이고~', '글쎄~' 같은 표현 자주 씀. 천천히 설명 필요"},
    {"type": "외국인(영어권)", "desc": "한국어가 서툰 영어권 외국인. 한영 혼용. '이거 얼마야?', 'Too expensive!', 'possible?' 같은 식으로 말함"},
    {"type": "화난 단골(50대)", "desc": "10년 넘게 온 50대 단골. '내가 여기를 몇 년을 왔는데' 자주 말함. 예전과 비교하며 실망 표현"},
    {"type": "젊은 첫방문(20대)", "desc": "처음 방문한 20대. '진짜요?', '헐', '어떻게 해요?' 같은 말투. SNS 후기 언급함"},
    {"type": "VIP 고객(50대)", "desc": "자신이 VIP임을 강조하는 50대. 말투가 권위적이고 특별 대우를 당연시함. 다른 VIP 혜택과 비교함"},
    {"type": "합리적 소비자(30~40대)", "desc": "가격 대비 가치를 따지는 30~40대. 논리적으로 근거 들며 주장. 규정과 법을 잘 알고 있음"},
    {"type": "감정적 고객(30대)", "desc": "개인적으로 힘든 일이 있어 예민한 30대. 작은 것에도 상처받음. 목소리가 떨리거나 울먹임"},
    {"type": "억지 부리는 고객(40대)", "desc": "말이 안 되는 요구를 논리처럼 포장하는 40대. 끝까지 자기가 맞다고 우김. 규정 허점을 파고듦"},
]

EMOTIONAL_STATES = [
    "처음엔 차분하지만 해결 안 되면 점점 흥분",
    "처음부터 흥분된 상태로 목소리가 높음",
    "냉정하고 논리적으로 압박하는 스타일",
    "울먹이거나 감정에 호소하는 스타일",
    "비꼬는 말투로 빈정거리는 스타일",
]

# 직무별 어울리는 고객유형 인덱스
# 0:급한직장인 1:꼼꼼한주부 2:어르신 3:외국인 4:화난단골 5:젊은첫방문 6:VIP고객 7:합리적소비자 8:감정적고객 9:억지고객
JOB_CUSTOMER_MAP = {
    "cashier":   [0,1,2,3,4,5,7,8,9],
    "vegetable": [1,2,3,4,5,7,8,9],
    "seafood":   [1,2,4,7,8,9],
    "meat":      [1,2,4,7,8,9],
    "cs":        [0,1,2,4,5,7,8,9],
    "vip":       [1,4,6,7,8,9],
    "rental":    [1,2,5,8,9],
    "general":   [0,1,2,3,4,5,7,8,9],
}

def generate_scenario(job_type: str, difficulty: int) -> dict:
    allowed = JOB_CUSTOMER_MAP.get(job_type, list(range(len(CUSTOMER_TYPES))))
    customer = CUSTOMER_TYPES[random.choice(allowed)]
    situations = JOB_SITUATIONS.get(job_type, JOB_SITUATIONS["general"])
    situation = random.choice(situations[difficulty])
    emotion = random.choice(EMOTIONAL_STATES)
    return {
        "customer_type": customer["type"],
        "customer_desc": customer["desc"],
        "situation": situation,
        "emotion": emotion,
    }

def build_system_prompt(job_type: str, difficulty: int, scenario: dict) -> str:
    job = JOB_INFO.get(job_type, JOB_INFO["general"])
    is_foreigner = "외국인" in scenario['customer_type']

    foreigner_guide = """
## 외국인 말투 필수 적용
- 한국어와 영어를 자연스럽게 섞어서 말할 것
- 예시: "이거 얼마야?", "Too expensive!", "깎아줘 please", "환불 possible?", "why 안 돼요?"
- 문법이 약간 틀려도 됨. 짧고 직접적으로 말할 것
""" if is_foreigner else ""

    return f"""당신은 백화점 {job['place']}을 방문한 실제 고객입니다.
지금 직원(상대방)에게 말을 걸고 있는 상황입니다.

## 나는 누구인가
- 고객 유형: {scenario['customer_type']}
- 내 특성: {scenario['customer_desc']}
- 내가 겪은 상황: {scenario['situation']}
- 현재 감정: {scenario['emotion']}
- 강도: Level {difficulty} (1=차분한 문의, 5=극도로 격앙)
{foreigner_guide}
## 말투 규칙 (반드시 지킬 것)
- 내 유형에 맞는 실제 말투로만 말할 것
- 어르신이면: "아이고~", "글쎄~", 느리고 반복적으로
- 20대 첫방문이면: "헐", "진짜요?", 가볍고 놀라는 말투로
- 급한 직장인이면: 짧고 빠르게, 시간 압박 표현으로
- 화난 단골이면: "내가 여기를 몇 년을 왔는데~" 표현으로
- 억지 고객이면: 말이 안 되는 걸 논리인 척 포장해서
- VIP 고객이면: 권위적이고 당연히 특별 대우받아야 한다는 태도로

## 대화 방식
1. 오직 고객으로서만 말할 것. 직원 역할 절대 금지.
2. 상대방이 잘 응대하면 감정이 조금씩 누그러짐.
3. 상대방이 잘못 응대하거나 무시하면 더 강하게 반응.
4. 매 응답마다 구체적인 디테일 추가해서 현실감 높이기.
5. 대화가 5~6회 진행되면 자연스럽게 마무리 방향으로.

## 절대 금지
- *(행동 묘사)* 같은 별표 표현 절대 금지
- 교육/훈련/AI 언급 금지
- 날씨, 정치, 연예인 등 상관없는 주제 대화 금지
- 관계없는 질문엔: "지금 그런 얘기 할 상황이 아니에요. 제 문제부터 해결해 주세요!"

## 응답 길이
- 반드시 2~3문장 이내로 짧게
- 길게 쓰지 말 것. 핵심만 간결하게."""


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))

        job_type   = body.get("job_type", "general")
        difficulty = int(body.get("difficulty", 1))
        messages   = body.get("messages", [])
        scenario   = body.get("scenario", None)

        is_first = len(messages) == 0
        if is_first or not scenario:
            scenario = generate_scenario(job_type, difficulty)

        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        system_prompt = build_system_prompt(job_type, difficulty, scenario)

        if is_first:
            first_prompt = f"""지금 처음으로 직원에게 말을 거는 순간입니다.

상황: {scenario['situation']}
내 유형: {scenario['customer_type']}
내 특성: {scenario['customer_desc']}
현재 감정: {scenario['emotion']}
난이도: Level {difficulty}

규칙:
- 시나리오 내용을 그대로 읽지 말 것. 실제 고객처럼 자연스럽게 말할 것.
- 내 유형 말투 특성 반드시 반영할 것.
- 2~3문장 이내로 짧고 임팩트 있게.
- 별표 액션 표현 절대 금지.
- 상황 설명이 아닌 실제 대화체로."""
            try:
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=200,
                    system=system_prompt,
                    messages=[{"role": "user", "content": first_prompt}],
                )
                opening = response.content[0].text
            except Exception as e:
                print(f"first msg error: {e}", flush=True)
                opening = "저기요, 잠깐 좀 도와주실 수 있어요?"
            self._respond(200, {"message": opening, "scenario": scenario, "is_first": True})
            return

        api_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=400,
                system=system_prompt,
                messages=api_messages,
            )
            self._respond(200, {"message": response.content[0].text, "scenario": scenario})
        except Exception as e:
            self._respond(500, {"error": str(e)})

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
