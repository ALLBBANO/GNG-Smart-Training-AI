from http.server import BaseHTTPRequestHandler
import json, os, random, anthropic

# ── 직무 정보 ──────────────────────────────────────────────────────────────────
JOB_INFO = {
    "cashier":   {"name": "캐셔",        "place": "계산대"},
    "vegetable": {"name": "야채/과일",   "place": "신선식품 코너"},
    "seafood":   {"name": "수산",        "place": "수산물 코너"},
    "meat":      {"name": "정육",        "place": "정육 코너"},
    "cs":        {"name": "고객상담실",  "place": "고객상담실"},
    "vip":       {"name": "VIP 라운지", "place": "VIP 라운지"},
    "rental":    {"name": "유모차/휠체어","place": "대여 서비스 데스크"},
    "general":   {"name": "일반 응대",   "place": "매장 안내 데스크"},
}

# ── 직무별 시나리오 (난이도 × 직무) ────────────────────────────────────────────
JOB_SITUATIONS = {
    "cashier": {
        1: ["영수증을 받지 못했다고 재발급 요청", "포인트 적립 방법 문의", "상품권 사용 방법 문의", "할인쿠폰 적용 방법 문의"],
        2: ["영수증 금액이 가격표랑 다르다고 항의", "카드 결제가 두 번 됐다고 주장", "쿠폰이 적용 안 됐다고 항의", "포인트가 안 쌓였다고 항의"],
        3: ["계산이 잘못됐다며 환불 요구", "카드 취소 후 현금 환불 요구", "영수증 없이 환불 요구", "행사가 적용 안 됐다며 강하게 항의"],
        4: ["카드 정보 유출됐다며 매장 탓", "이중결제로 큰 금액 손해봤다며 보상 요구", "직원이 거스름돈 빼돌렸다고 주장", "영수증 조작 의심하며 책임자 요구"],
        5: ["카드사에 신고하겠다며 협박", "SNS에 올리겠다며 직원 촬영", "경찰 부르겠다며 소란", "본사 고발하겠다며 집단 보상 요구"],
    },
    "vegetable": {
        1: ["특정 과일 입고 여부 문의", "유기농 상품 위치 문의", "과일 고르는 방법 문의", "산지 및 원산지 문의"],
        2: ["산 딸기에 곰팡이가 있다고 항의", "가격표랑 실제 가격이 다르다고 항의", "유통기한이 며칠 안 남은 상품 발견", "포장이 터진 채로 판매됐다고 항의"],
        3: ["상한 과일 먹고 탈이 났다고 주장", "광고한 것보다 품질이 나쁘다며 항의", "같은 상품이 다른 곳이 더 싸다며 항의", "행사 상품 물량이 없다며 강하게 항의"],
        4: ["상한 과일로 아이가 아팠다며 보상 요구", "원산지 표기가 잘못됐다며 법적 대응 언급", "알레르기 반응 일어났다며 책임 추궁", "대량 구매했는데 대부분 상했다며 전액 환불 요구"],
        5: ["식품위생법 위반으로 신고하겠다며 협박", "SNS에 상한 과일 사진 올리겠다며 협박", "방송국에 제보하겠다며 과도한 보상 요구", "집단 소송 언급하며 매장 앞에서 소란"],
    },
    "seafood": {
        1: ["생선 손질 방법 문의", "오늘 입고된 신선한 생선 추천 요청", "조개 보관 방법 문의", "제철 수산물 문의"],
        2: ["생선에서 냄새가 난다고 항의", "새우에 이물질이 있다고 항의", "가격표와 실제 가격이 다르다고 항의", "손질 요청했는데 잘못됐다고 항의"],
        3: ["상한 생선 먹고 배탈났다고 주장", "비린내가 너무 심하다며 환불 요구", "원산지가 다르다며 강하게 항의", "오늘 산 게가 죽어있다며 항의"],
        4: ["생선 먹고 가족이 식중독 걸렸다며 보상 요구", "원산지 허위표기로 신고하겠다고 협박", "활어가 죽어있었다며 큰 보상 요구", "납품업체까지 문제삼으며 책임자 요구"],
        5: ["식중독으로 입원했다며 거액 보상 요구", "보건소 신고하겠다며 매장 영업 방해", "방송 제보로 매장 폐쇄시키겠다고 협박", "집단 소송 언급하며 과도한 합의금 요구"],
    },
    "meat": {
        1: ["삼겹살 두께 조절 요청", "부위별 요리법 문의", "오늘 입고된 신선한 고기 추천", "1인분 적정 양 문의"],
        2: ["고기 색이 이상하다고 항의", "포장 무게가 표기랑 다르다고 항의", "등급 표시가 이상하다고 항의", "원하는 부위로 교체 요청"],
        3: ["상한 고기 먹고 탈이 났다고 주장", "등급 속여서 팔았다며 항의", "유통기한 지난 고기 판매됐다며 항의", "비싸게 잘못 계산됐다며 환불 요구"],
        4: ["상한 고기로 온 가족이 식중독 걸렸다며 보상 요구", "등급 허위표시로 신고하겠다고 협박", "대량 구매했는데 절반이 상했다며 전액 환불 요구", "납품 비리 의심하며 책임자 호출"],
        5: ["식중독으로 병원 입원했다며 거액 보상 요구", "식품위생 당국 신고하겠다며 영업 방해", "방송국 제보로 매장 폐쇄시키겠다고 협박", "법적 소송 언급하며 과도한 합의금 요구"],
    },
    "cs": {
        1: ["멤버십 포인트 조회 요청", "주차 무료 시간 문의", "분실물 접수 문의", "행사 기간 및 내용 문의"],
        2: ["포인트 소멸됐다고 복구 요청", "주차 요금 과다 청구 항의", "온라인 주문 배송 지연 항의", "교환/환불 절차 불만"],
        3: ["직원 불친절 민원 강하게 제기", "환불 규정이 불합리하다며 항의", "멤버십 등급 강등됐다며 항의", "약속된 서비스 못 받았다며 강하게 항의"],
        4: ["직원 해고 요구하며 강하게 항의", "법적 대응 언급하며 보상 요구", "VIP 혜택 제대로 못 받았다며 강력 항의", "개인정보 유출 의심하며 책임 추궁"],
        5: ["소비자원 신고하겠다며 협박", "SNS 바이럴로 매장 망하게 하겠다고 협박", "집단 민원 조직하겠다고 협박", "언론 제보하겠다며 과도한 보상 요구"],
    },
    "vip": {
        1: ["VIP 전용 주차 위치 문의", "VIP 라운지 이용 시간 문의", "VIP 전용 행사 안내 요청", "픽업 서비스 예약 방법 문의"],
        2: ["VIP 할인이 적용 안 됐다고 항의", "예약한 픽업 서비스가 늦었다고 항의", "VIP 라운지 서비스 품질 불만", "전용 주차 자리가 없었다고 항의"],
        3: ["일반 고객과 같은 대우 받았다며 강하게 항의", "VIP 혜택이 줄었다며 항의", "직원 태도가 불친절했다며 강하게 항의", "예약 서비스가 취소됐는데 연락 없었다며 항의"],
        4: ["VIP 등급 강등에 강력 항의하며 보상 요구", "타 백화점 VIP 서비스와 비교하며 압박", "VIP 전용 상품 품질 문제로 보상 요구", "특별 대우 요구하며 책임자 면담 요구"],
        5: ["VIP 탈퇴 선언하며 주변 VIP 회원 이탈 협박", "언론에 VIP 서비스 실태 제보하겠다고 협박", "본사 회장에게 직접 민원 넣겠다고 협박", "SNS에 VIP 서비스 폭로하겠다고 협박"],
    },
    "rental": {
        1: ["유모차 대여 방법 문의", "휠체어 크기 및 종류 문의", "대여 가능 시간 문의", "보증금 반환 방법 문의"],
        2: ["반납 기한 초과 요금 이의 제기", "대여한 유모차 바퀴가 불량이라고 항의", "보증금 반환이 안 됐다고 항의", "대여증을 분실했다고 당황하며 문의"],
        3: ["유모차 불량으로 아이가 다칠 뻔 했다고 항의", "반납했는데 요금이 계속 청구된다고 강하게 항의", "휠체어 고장으로 어르신이 불편했다며 항의", "대여 가능하다고 했는데 실제로 없었다며 항의"],
        4: ["유모차 결함으로 아이가 다쳤다며 보상 요구", "보증금을 돌려주지 않는다며 법적 대응 언급", "안전 불량 제품 대여했다며 책임자 요구", "휠체어 고장으로 어르신 낙상했다며 보상 요구"],
        5: ["아이 부상으로 거액 보상 요구하며 소란", "소비자원 신고하겠다며 협박", "안전 불량 제품 SNS에 공론화하겠다고 협박", "집단 소송 언급하며 과도한 합의 요구"],
    },
    "general": {
        1: ["화장실 위치 문의", "층별 매장 안내 요청", "셔틀버스 시간 문의", "분실물 보관 위치 문의"],
        2: ["안내 받은 매장 위치가 달랐다고 항의", "주차 정산 오류 항의", "엘리베이터 고장으로 불편 항의", "매장 내 흡연 목격 신고"],
        3: ["직원이 불친절했다며 강하게 항의", "매장이 너무 복잡해서 길 잃었다며 항의", "안내 방송이 잘못됐다며 항의", "휠체어 경사로가 없다며 불편 호소"],
        4: ["매장 내 사고로 부상 주장하며 보상 요구", "안전시설 미비로 법적 대응 언급", "아이가 매장 내 시설에 다쳤다며 보상 요구", "직원 폭언 주장하며 책임자 요구"],
        5: ["매장 내 사고로 거액 보상 요구하며 소란", "안전 불량으로 관할 기관 신고 협박", "SNS 공론화로 매장 이미지 망치겠다고 협박", "집단 민원으로 영업 방해 협박"],
    },
}

# ── 고객 유형 (나이 특정) ──────────────────────────────────────────────────────
CUSTOMER_TYPES = [
    {"type": "급한 직장인(30대)", "desc": "점심시간에 온 바쁜 30대 직장인. 말이 빠르고 짧게 끊어서 말함. 시간 없다는 말을 자주 함"},
    {"type": "꼼꼼한 주부(40대)", "desc": "영수증과 상품을 꼼꼼히 따지는 40대 주부. 논리적으로 조목조목 따짐"},
    {"type": "어르신(70대)", "desc": "70대 어르신. 말이 느리고 같은 말 반복. 귀가 좀 어두워서 크게 말해야 함. '아이고~', '글쎄~' 같은 표현 자주 씀"},
    {"type": "외국인(영어권)", "desc": "한국어가 서툰 영어권 외국인. 한영 혼용해서 말함. '이거 얼마야?', 'Too expensive!', '깎아줘', 'possible?' 같은 식으로 말함"},
    {"type": "화난 단골(50대)", "desc": "10년 넘게 온 50대 단골. '내가 여기를 몇 년을 왔는데' 같은 말 자주 함. 예전이랑 비교하며 실망 표현"},
    {"type": "젊은 첫방문(20대)", "desc": "처음 방문한 20대. '진짜요?', '헐', '어떻게 해요?' 같은 젊은 말투. SNS 후기 언급하거나 사진 찍겠다고 함"},
    {"type": "VIP 고객(40~50대)", "desc": "자신이 VIP임을 강조하는 40~50대. 말투가 권위적이고 특별 대우 당연시함. '내가 누군지 알아?' 뉘앙스"},
    {"type": "단체 구매 담당자(30~40대)", "desc": "회사 행사용 대량 구매 담당자. 협상 위주로 말함. 숫자에 민감하고 견적/할인 요구"},
    {"type": "감정적 고객(30대)", "desc": "개인적으로 힘든 일이 있어 예민한 30대. 작은 것에도 상처받음. 울먹이거나 목소리 떨림"},
    {"type": "억지 부리는 고객(40대)", "desc": "말이 안 되는 요구를 논리처럼 포장하는 40대. 끝까지 자기가 맞다고 우김. 매장 정책의 허점을 파고듦"},
]

# ── 감정 상태 ──────────────────────────────────────────────────────────────────
EMOTIONAL_STATES = [
    "처음엔 차분하지만 해결 안 되면 점점 흥분",
    "처음부터 흥분된 상태로 목소리가 높음",
    "냉정하고 논리적으로 압박하는 스타일",
    "울먹이거나 감정에 호소하는 스타일",
    "비꼬는 말투로 빈정거리는 스타일",
]

def build_system_prompt(job_type: str, difficulty: int, scenario: dict) -> str:
    job = JOB_INFO.get(job_type, JOB_INFO["general"])
    customer_type = scenario['customer_type']
    is_foreigner = "외국인" in customer_type

    foreigner_guide = """
## 외국인 말투 가이드 (필수)
- 한국어와 영어를 섞어서 말함
- 예: "이거 얼마야?", "Too expensive!", "조금 깎아줘, please", "환불 possible?", "why? 왜 안 돼?"
- 문법이 약간 틀려도 됨. 짧고 직접적으로 말함
- 한국어 단어 사이에 영어 단어 자연스럽게 섞기
""" if is_foreigner else ""

    return f"""당신은 G&G Smart Training AI의 고객 역할 AI입니다.
지금 {job['place']}에서 실제 민원 상황을 시뮬레이션합니다.

## 현재 시나리오
- 고객 유형: {scenario['customer_type']}
- 고객 특성: {scenario['customer_desc']}
- 상황: {scenario['situation']}
- 고객 감정: {scenario['emotion']}
- 난이도: Level {difficulty} (1=차분, 5=극한)

## 말투 규칙 (매우 중요)
- 고객 유형 특성에 맞는 실제 말투로 말할 것
- 어르신: "아이고~", "글쎄~", 느리고 반복적
- 젊은 20대: "진짜요?", "헐", "어떻게 해요?" 등 젊은 말투
- 급한 직장인: 짧고 빠르게, "빨리빨리" 뉘앙스
- 단골 50대: "내가 여기를 몇 년을 왔는데~"
- 억지 고객: 말이 안 되는 걸 논리처럼 포장
{foreigner_guide}
## 역할 규칙
1. 오직 고객 역할만 함. 직원 역할 절대 금지.
2. 시나리오 상황에만 집중하여 고객처럼 반응.
3. 잘 응대하면 감정이 누그러지고, 못 응대하면 더 강하게 반응.
4. 매 응답마다 시나리오 안에서 새로운 디테일 추가해 현실감 높이기.
5. 대화가 5~6회 진행되어 마무리될 상황이면 자연스럽게 마무리 방향으로.

## 절대 금지
- 교육/훈련 시스템 언급 금지
- AI 신분 노출 금지
- 시나리오 밖 주제(날씨, 정치, 연예인 등) 대화 금지
- 교육 무관한 질문엔: "지금 그런 얘기 할 상황이 아니에요. 제 문제부터 해결해 주세요!"

## 응답 형식
- 2~4문장, 실제 고객처럼 자연스러운 구어체
- 고객 유형 말투 특성 반드시 반영
- 감정 표현 포함 (한숨, 짜증, 당황 등)"""

def generate_scenario(job_type: str, difficulty: int) -> dict:
    customer = random.choice(CUSTOMER_TYPES)
    situations = JOB_SITUATIONS.get(job_type, JOB_SITUATIONS["general"])
    situation = random.choice(situations[difficulty])
    emotion = random.choice(EMOTIONAL_STATES)
    return {
        "customer_type": customer["type"],
        "customer_desc": customer["desc"],
        "situation": situation,
        "emotion": emotion,
    }

def get_opening_line(scenario: dict, job_type: str, difficulty: int) -> str:
    situation = scenario["situation"]
    customer_type = scenario["customer_type"]
    is_foreigner = "외국인" in customer_type
    is_elder = "70대" in customer_type
    is_young = "20대" in customer_type
    is_busy = "직장인" in customer_type

    if is_foreigner:
        openers = {
            1: [f"저기요, 이거 {situation}... how do I say... 도와줘요?", f"Excuse me, {situation} 어떻게 해요?"],
            2: [f"여기요! {situation}인데, this is wrong 아니에요?", f"{situation}... 이거 왜 이래요? Can you check?"],
            3: [f"이거 너무해요! {situation}! This is unacceptable!", f"왜요?! {situation}! I want refund!"],
            4: [f"당장 manager 불러요! {situation} 이게 말이 돼요?!", f"This is crazy! {situation}! 보상해줘요 now!"],
            5: [f"I'll call the police! {situation}! 당신들 책임져요!", f"This is fraud! {situation}! 다 SNS에 올릴 거야!"],
        }
    elif is_elder:
        openers = {
            1: [f"아이고~ 저기 좀 여쭤봐도 되겠어요? {situation}인데 글쎄...", f"여기 직원이에요? 아이고~ {situation} 어떻게 하는 거예요?"],
            2: [f"아이고~ 이거 좀 봐요. {situation}이라는데 글쎄 이게 맞는 거예요?", f"저기~ 아까부터 {situation}인데 이게 어떻게 된 거예요?"],
            3: [f"아이고 이런! {situation}이라고요! 이게 말이 됩니까?", f"글쎄 {situation}이라는데 어떻게 이럴 수가 있어요!"],
            4: [f"아이고! {situation}! 책임자 나와요 책임자!", f"이게 무슨 일이에요! {situation}! 당장 해결해줘요!"],
            5: [f"아이고 세상에! {situation}! 내가 그냥 안 넘어갈 거예요!", f"글쎄 {situation}이라고요! 당장 책임자 불러요!"],
        }
    elif is_young:
        openers = {
            1: [f"저기요~ {situation}인데 어떻게 해요?", f"헐, {situation}이에요? 어떻게 하면 돼요?"],
            2: [f"저기요, 진짜요? {situation}이라는데 이거 맞아요?", f"헐 이거 {situation}인데 어떻게 해요?"],
            3: [f"진짜요?! {situation}이라고요! 이거 너무한 거 아니에요?", f"헐 {situation}이에요?! 이게 말이 돼요?"],
            4: [f"아 진짜요?! {situation}! 이거 SNS에 올려도 돼요?", f"완전 황당한데요?! {situation}! 책임자 불러주세요!"],
            5: [f"진짜 실화예요?! {situation}! 인스타에 바로 올릴 거예요!", f"아 이거 {situation}! 후기 엄청 쓸 거예요 진짜로!"],
        }
    elif is_busy:
        openers = {
            1: [f"빨리요, {situation} 어떻게 해요?", f"시간 없어요. {situation} 바로 해결해줘요."],
            2: [f"지금 바쁜데, {situation} 빨리 확인해줘요.", f"점심시간인데 {situation}이에요. 빨리 해결해줘요."],
            3: [f"아 진짜! {situation}이에요! 빨리 해결해줘요!", f"시간 없는데 {situation}이라니! 빨리 처리해주세요!"],
            4: [f"지금 당장 {situation} 해결해요! 기다릴 시간 없어요!", f"바쁜 사람 붙잡고! {situation}! 빨리 책임자 불러요!"],
            5: [f"당장 {situation} 해결 안 하면 가만 안 있을 거예요!", f"{situation}! 지금 당장 처리해요! 못 기다려요!"],
        }
    else:
        openers = {
            1: [f"저기 잠깐요, {situation}인데 도움받을 수 있을까요?", f"실례합니다. {situation}이라서요."],
            2: [f"좀 이상한 것 같아서요. {situation}이에요.", f"확인 좀 해주실 수 있어요? {situation}이에요."],
            3: [f"이거 심각한 문제 아닌가요? {situation}이라고요!", f"어떻게 이럴 수가 있어요? {situation}인데 말이 됩니까?"],
            4: [f"지금 당장 책임자 불러주세요. {situation} 어떻게 된 거예요!", f"이게 말이 돼요? {situation} 보상 받아야 하는 거 아닙니까!"],
            5: [f"야, 책임자 지금 당장 나와요! {situation} 가만 안 있을 거야!", f"나 지금 녹음하고 있어요. {situation} 어디 신고할지 알아요?"],
        }

    return random.choice(openers.get(difficulty, openers[1]))


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

        # 첫 메시지 포함 모두 Claude API로 생성
        if is_first:
            first_prompt = f"""지금 당신이 처음으로 직원에게 말을 거는 상황입니다.
고객 유형: {scenario['customer_type']}
고객 특성: {scenario['customer_desc']}
상황: {scenario['situation']}
감정 상태: {scenario['emotion']}
난이도: Level {difficulty}

위 설정에 맞게 처음 말을 거는 첫 마디를 자연스럽게 해주세요.
- 시나리오 내용을 그대로 읽지 말고 실제 고객처럼 자연스럽게
- 고객 유형의 말투 특성 반드시 반영
- 1~3문장으로 짧고 임팩트 있게
- 상황 설명이 아닌 실제 대화로"""
            try:
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=150,
                    system=system_prompt,
                    messages=[{"role": "user", "content": first_prompt}],
                )
                opening = response.content[0].text
            except Exception as e:
                opening = get_opening_line(scenario, job_type, difficulty)
            self._respond(200, {"message": opening, "scenario": scenario, "is_first": True})
            return

        api_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=300,
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
