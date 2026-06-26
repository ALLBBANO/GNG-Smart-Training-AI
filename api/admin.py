from http.server import BaseHTTPRequestHandler
import json, os
from urllib.parse import urlparse, parse_qs
from supabase import create_client

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "gng2024!")

def get_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        action = params.get("action", [""])[0]

        # 인증 체크
        cookie = self.headers.get("Cookie", "")
        if "gst_admin=verified" not in cookie:
            self._respond(401, {"error": "인증 필요"})
            return

        sb = get_supabase()

        if action == "overview":
            self._get_overview(sb, params)
        elif action == "sessions":
            self._get_sessions(sb, params)
        elif action == "employee":
            name = params.get("name", [""])[0]
            self._get_employee(sb, name)
        elif action == "stats":
            self._get_stats(sb)
        else:
            self._respond(400, {"error": "잘못된 요청"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        action = body.get("action", "")

        if action == "login":
            pw = body.get("password", "")
            if pw == ADMIN_PASSWORD:
                resp_body = json.dumps({"ok": True}, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Set-Cookie", "gst_admin=verified; Path=/; HttpOnly; Max-Age=28800; SameSite=Strict")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(resp_body)
            else:
                self._respond(401, {"ok": False, "error": "비밀번호가 틀렸습니다."})
            return

        if action == "logout":
            resp_body = json.dumps({"ok": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Set-Cookie", "gst_admin=; Path=/; HttpOnly; Max-Age=0")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(resp_body)
            return

        self._respond(400, {"error": "잘못된 요청"})

    def _get_overview(self, sb, params):
        try:
            days = params.get("days", ["30"])[0]
            result = sb.table("gst_sessions")\
                .select("id, employee_name, job_type, difficulty, score, grade, created_at")\
                .not_.is_("completed_at", "null")\
                .order("created_at", desc=True)\
                .limit(500)\
                .execute()
            rows = result.data or []

            total = len(rows)
            avg_score = round(sum(r["score"] or 0 for r in rows) / total, 1) if total else 0
            a_count = sum(1 for r in rows if r["grade"] == "A")
            employees = len(set(r["employee_name"] for r in rows))

            by_job = {}
            for r in rows:
                j = r["job_type"]
                if j not in by_job:
                    by_job[j] = {"total": 0, "scores": [], "a": 0, "b": 0, "c": 0}
                by_job[j]["total"] += 1
                by_job[j]["scores"].append(r["score"] or 0)
                g = r.get("grade", "C")
                if g in ("A","B","C"):
                    by_job[j][g.lower()] += 1

            by_job_list = [
                {
                    "job_type": k,
                    "total": v["total"],
                    "avg_score": round(sum(v["scores"]) / len(v["scores"]), 1) if v["scores"] else 0,
                    "a_count": v["a"], "b_count": v["b"], "c_count": v["c"],
                }
                for k, v in by_job.items()
            ]

            self._respond(200, {
                "total": total,
                "avg_score": avg_score,
                "a_rate": round(a_count / total * 100, 1) if total else 0,
                "employees": employees,
                "by_job": by_job_list,
                "recent": rows[:10],
            })
        except Exception as e:
            print(f"overview error: {e}", flush=True)
            self._respond(500, {"error": str(e)})

    def _get_sessions(self, sb, params):
        try:
            job   = params.get("job", [""])[0]
            grade = params.get("grade", [""])[0]
            name  = params.get("name", [""])[0]

            q = sb.table("gst_sessions")\
                .select("id, employee_name, job_type, difficulty, score, grade, feedback, created_at")\
                .not_.is_("completed_at", "null")\
                .order("created_at", desc=True)\
                .limit(100)

            if job:   q = q.eq("job_type", job)
            if grade: q = q.eq("grade", grade)
            if name:  q = q.ilike("employee_name", f"%{name}%")

            result = q.execute()
            self._respond(200, {"sessions": result.data or []})
        except Exception as e:
            self._respond(500, {"error": str(e)})

    def _get_employee(self, sb, name):
        try:
            result = sb.table("gst_sessions")\
                .select("*")\
                .ilike("employee_name", f"%{name}%")\
                .not_.is_("completed_at", "null")\
                .order("created_at", desc=True)\
                .limit(50)\
                .execute()
            self._respond(200, {"sessions": result.data or []})
        except Exception as e:
            self._respond(500, {"error": str(e)})

    def _get_stats(self, sb):
        try:
            result = sb.table("gst_sessions")\
                .select("difficulty, score, grade")\
                .not_.is_("completed_at", "null")\
                .execute()
            rows = result.data or []

            by_diff = {}
            for r in rows:
                d = str(r["difficulty"])
                if d not in by_diff:
                    by_diff[d] = []
                by_diff[d].append(r["score"] or 0)

            diff_stats = {
                k: round(sum(v)/len(v), 1) for k, v in by_diff.items()
            }

            self._respond(200, {"by_difficulty": diff_stats, "total": len(rows)})
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
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        pass
