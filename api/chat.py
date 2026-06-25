from http.server import BaseHTTPRequestHandler
import json, os, random, anthropic

# ── 직무 정보 ──────────────────────────────────────────────────────────────────
JOB_INFO = {
    "cashier":    {"name": "캐셔", "place": "계산대", "items": ["영수증", "카드결제", "할인쿠폰", "포인트적립", "영수증 재발급", "거스름돈", "상품권"]},
    "vegetable":  {"name": "야채/과일", "place": "신선식품 코너", "items": ["사과", "딸기", "상추", "당근", "토마토", "포도", "수박", "복숭아"]},
    "seafood":    {"name": "수산", "place": "수산물 코너", "items": ["생선", "새우", "조개", "오징어", "꽃게", "전복", "굴", "낙지"]},
    "meat":       {"name": "정육", "place": "정육 코너", "items": ["삼겹살", "소고기", "닭고기", "갈비", "등심", "안심", "차돌박이"]},
    "cs":         {"name": "고객상담실", "place": "고객상담실", "items": ["환불", "교환", "분실물", "불만접수", "포인트", "멤버십", "주차"]},
    "vip":        {"name": "VIP 라운지", "place": "VIP 라운지", "items": ["발렛파킹", "픽업서비스", "전용할인", "프리미엄 상품", "행사초대", "전용주차"]},
    "rental":     {"name": "유모차/휠체어", "place": "대여 서비스 데스크", "items": ["유모차", "휠체어", "대여증", "반납", "파손", "보증금"]},
    "general":    {"name": "일반 응대", "place": "매장 내", "items": ["화장실 위치", "층별 안내", "주차 정산", "분실물", "행사 안내", "셔틀버스"]},
}

# ── 고객 유형 (10가지) ─────────────────────────────────────────────────────────
CUSTOMER_TYPES = [
    {"type": "급한_직장인", "desc": "점심시간에 온 바쁜 직장인. 시간이 없다고 강조하며 빠른 처리를 원함"},
    {"type": "꼼꼼한_주부", "desc": "영수증과 상품 상태를 꼼꼼히 확인하는 중년 주부. 작은 것도 놓치지 않음"},
    {"type": "어르신", "desc": "디지털에 익숙하지 않은 어르신. 천천히 설명해야 하고 반복 질문이 많음"},
    {"type": "외국인", "desc": "한국어가 서툰 외국인. 간단한 단어로 소통해야 함"},
    {"type": "화난_단골", "desc": "오래된 단골인데 이번에 실망한 고객. 전에는 잘 해줬다고 비교함"},
    {"type": "젊은_첫방문", "desc": "처음 방문한 20대. 궁금한 게 많고 SNS 후기를 언급함"},
    {"type": "VIP_고객", "desc": "자신이 VIP 회원임을 강조하는 고객. 특별 대우를 기대함"},
    {"type": "단체_담당자", "desc": "회사 행사용으로 대량 구매하러 온 담당자. 가격 협상을 원함"},
    {"type": "감정적_고객", "desc": "개인적으로 힘든 일이 있어 감정이 예민한 상태. 작은 것에도 상처받음"},
    {"type": "블랙컨슈머_의심", "desc": "과도한 요구를 하거나 억지 주장을 펼치는 고객. 매장 정책의 한계를 시험함"},
]

# ── 문제 상황 (난이도별) ───────────────────────────────────────────────────────
SITUATIONS = {
    1: [  # 기본
        "상품 위치를 묻는 단순 문의",
        "영업시간과 주차 관련 질문",
        "포인트 적립 방법 문의",
        "화장실/편의시설 위치 문의",
        "행사 안내 문의",
        "상품 가격 문의",
        "교환 절차 단순 문의",
    ],
    2: [  # 일반 클레임
        "구매한 상품의 유통기한이 며칠 안 남음",
        "영수증과 실제 결제금액이 다름",
        "할인 쿠폰이 적용이 안 됨",
        "포인트가 적립이 안 됨",
        "상품 포장이 훼손된 채로 판매됨",
        "안내된 행사와 실제 행사 내용이 다름",
        "계산이 잘못된 것 같다며 확인 요청",
    ],
    3: [  # 불만 고객
        "상한 것 같은 음식을 먹고 배탈이 났다고 주장",
        "직원이 불친절했다고 항의",
        "같은 상품을 다른 매장에서 더 싸게 팔고 있다고 항의",
        "환불 규정이 말이 안 된다며 강하게 항의",
        "주문한 상품이 빠졌다며 항의",
        "오랜 대기 시간에 대한 강한 불만",
        "상품 품질이 광고와 다르다고 항의",
    ],
    4: [  # 강한 클레임
        "상한 음식으로 가족 전체가 식중독에 걸렸다고 주장하며 보상 요구",
        "직원이 반말을 했다며 해당 직원 처벌 요구",
        "VIP인데 일반 고객과 같은 대우를 받았다며 강력 항의",
        "카드 정보가 유출된 것 같다며 매장을 의심",
        "알레르기 성분 표시가 잘못돼서 아이가 다쳤다고 주장",
        "매장 시설 때문에 넘어져 다쳤다며 보상 요구",
        "예약한 서비스가 취소됐는데 연락이 없었다며 강하게 항의",
    ],
    5: [  # 진상 고객
        "근거 없이 직원이 자신을 도둑 취급했다고 주장하며 법적 조치 언급",
        "유통기한 지난 상품을 고의로 팔았다고 주장하며 방송국 제보 협박",
        "환불 불가 상품인데 억지로 환불 요구하며 바닥에 상품 던짐",
        "직원 얼굴 사진 찍으며 SNS에 올리겠다고 협박",
        "아무 이유 없이 직원에게 폭언하며 계속 요구사항 추가",
        "이미 처리 완료된 건을 계속 문제 삼으며 추가 보상 요구",
        "여러 직원을 돌아다니며 같은 민원을 반복 제기하고 더 높은 보상 요구",
    ],
}

# ── 감정 상태 ──────────────────────────────────────────────────────────────────
EMOTIONAL_STATES = [
    "처음엔 차분하지만 해결이 안 되면 점점 흥분",
    "처음부터 매우 흥분된 상태",
    "냉정하고 논리적으로 압박",
    "울먹이며 감정에 호소",
    "비꼬는 말투로 빈정거림",
]

# ── 토픽 이탈 방어 키워드 ──────────────────────────────────────────────────────
OFF_TOPIC_KEYWORDS = [
    "날씨", "주식", "코인", "연예인", "스포츠", "게임", "영화", "정치",
    "대통령", "군대", "수능", "대학", "레시피", "요리법", "여행", "해외",
    "ChatGPT", "AI란", "너는 누구", "넌 뭐야", "프로그램", "개발",
]

def build_system_prompt(job_type: str, difficulty: int, scenario: dict) -> str:
    job = JOB_INFO.get(job_type, JOB_INFO["general"])
    
    return f"""당신은 G&G Smart Training AI의 고객 역할 담당 AI입니다.
지금 백화점 {job['place']}에서 발생한 실제 민원 상황을 시뮬레이션합니다.

## 현재 시나리오
- 고객 유형: {scenario['customer_type']}
- 고객 특성: {scenario['customer_desc']}
- 상황: {scenario['situation']}
- 관련 상품/서비스: {scenario['item']}
- 고객 감정 상태: {scenario['emotion']}
- 난이도: Level {difficulty}

## 역할 규칙 (절대 준수)
1. 당신은 오직 "고객" 역할만 합니다. 직원 역할 절대 금지.
2. 위 시나리오 상황에만 집중하여 고객처럼 반응합니다.
3. 난이도 {difficulty}에 맞는 감정 강도를 유지합니다 (1=차분, 5=극한).
4. 매 응답마다 시나리오 안에서 새로운 디테일을 추가해 현실감을 높입니다.
5. 직원(상대방)이 잘 응대하면 조금씩 감정이 누그러집니다.
6. 직원이 잘못 응대하면 더 강하게 반응합니다.

## 절대 금지 사항
- 교육/훈련 시스템에 대한 언급 금지
- 시나리오 밖의 주제(날씨, 정치, 연예인 등) 대화 금지
- "저는 AI입니다" 같은 신분 노출 금지
- 고객 역할에서 벗어나는 행동 금지
- 만약 상대방이 교육과 무관한 질문을 하면: "지금 그런 얘기 할 상황이 아니에요. 제 문제부터 해결해 주세요!" 라고만 답변

## 응답 형식
- 2~4문장으로 간결하게
- 실제 고객처럼 자연스러운 한국어 구어체
- 감정 표현 포함 (한숨, 짜증, 당황 등 상황에 맞게)"""

def generate_scenario(job_type: str, difficulty: int) -> dict:
    customer = random.choice(CUSTOMER_TYPES)
    situation = random.choice(SITUATIONS[difficulty])
    item = random.choice(JOB_INFO.get(job_type, JOB_INFO["general"])["items"])
    emotion = random.choice(EMOTIONAL_STATES)
    
    return {
        "customer_type": customer["type"],
        "customer_desc": customer["desc"],
        "situation": situation,
        "item": item,
        "emotion": emotion,
    }

def get_opening_line(scenario: dict, job_type: str, difficulty: int) -> str:
    job = JOB_INFO.get(job_type, JOB_INFO["general"])
    situation = scenario["situation"]
    item = scenario["item"]
    
    # 난이도별 첫 마디 톤
    if difficulty == 1:
        openers = [
            f"저기요, 잠깐 여쭤봐도 될까요? {situation}인데요.",
            f"실례합니다. {item} 관련해서 좀 도와주실 수 있어요?",
            f"혹시 {situation} 어떻게 하면 되나요?",
        ]
    elif difficulty == 2:
        openers = [
            f"저 좀 이상한 것 같아서요. {situation}이라서요.",
            f"방금 {item} 샀는데 {situation} 문제가 있는 것 같아요.",
            f"확인 좀 해주실 수 있어요? {situation}이에요.",
        ]
    elif difficulty == 3:
        openers = [
            f"이거 좀 심각한 문제 아닌가요? {situation}이라고요!",
            f"저 지금 너무 황당해요. {item} 때문에 {situation} 상황이에요.",
            f"어떻게 이럴 수가 있어요? {situation}인데 이게 말이 됩니까?",
        ]
    elif difficulty == 4:
        openers = [
            f"지금 당장 책임자 불러주세요. {situation} 도대체 어떻게 된 거예요!",
            f"이게 말이 돼요? {item} 때문에 {situation} 이거 보상 받아야 하는 거 아닙니까!",
            f"저 오늘 절대 그냥 안 가요. {situation} 이거 어떻게 해결할 건지 말해봐요!",
        ]
    else:  # 5
        openers = [
            f"야, 여기 책임자 지금 당장 나와요! {situation} 이거 가만 안 있을 거야!",
            f"나 지금 녹음하고 있어요. {situation} 이거 어디 신고할지 알아요?",
            f"당신들 오늘 나한테 크게 후회할 거예요. {situation} 이게 뭡니까!",
        ]
    
    return random.choice(openers)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        
        job_type   = body.get("job_type", "general")
        difficulty = int(body.get("difficulty", 1))
        messages   = body.get("messages", [])
        scenario   = body.get("scenario", None)
        
        # 첫 메시지면 시나리오 생성
        is_first = len(messages) == 0
        if is_first or not scenario:
            scenario = generate_scenario(job_type, difficulty)
        
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        system_prompt = build_system_prompt(job_type, difficulty, scenario)
        
        # 첫 메시지면 AI가 먼저 고객 역할로 시작
        if is_first:
            opening = get_opening_line(scenario, job_type, difficulty)
            result = {
                "message": opening,
                "scenario": scenario,
                "is_first": True,
            }
            self._respond(200, result)
            return
        
        # Claude API 호출
        api_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
        
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=300,
                system=system_prompt,
                messages=api_messages,
            )
            ai_reply = response.content[0].text
            self._respond(200, {"message": ai_reply, "scenario": scenario})
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
