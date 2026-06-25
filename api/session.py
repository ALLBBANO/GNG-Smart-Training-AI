from http.server import BaseHTTPRequestHandler
import json, os, uuid
from supabase import create_client

def get_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        
        employee_name = body.get("employee_name", "").strip()
        job_type      = body.get("job_type", "")
        difficulty    = int(body.get("difficulty", 1))
        
        if not employee_name or not job_type:
            self._respond(400, {"error": "이름과 직무를 입력해주세요."})
            return
        
        session_id = str(uuid.uuid4())
        
        try:
            sb = get_supabase()
            sb.table("gst_sessions").insert({
                "id": session_id,
                "employee_name": employee_name,
                "job_type": job_type,
                "difficulty": difficulty,
                "messages": [],
                "scenario_context": {},
            }).execute()
        except Exception as e:
            print(f"DB insert error: {e}", flush=True)
        
        self._respond(200, {"session_id": session_id})
    
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
