"""Small local application used only by the examples, with per-test state."""

import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit

NAV = '<nav><a href="/">Home</a> <a href="/contact">Contact</a> <a href="/tasks">Tasks</a></nav>'
PAGES = {
    "/": "<h1>Example application</h1><p>Learn to test with Playwright.</p>",
    "/contact": """
        <h1>Contact</h1>
        <form id="contact">
          <label>Name <input name="name" required></label>
          <label>Email <input name="email" type="email" required></label>
          <label>Subject <select name="subject">
            <option>Support</option><option>Sales</option>
          </select></label>
          <label><input type="checkbox" required> I accept the terms</label>
          <button>Send</button>
        </form>
        <p role="status"></p>
        <script>
          document.querySelector('form').addEventListener('submit', event => {
            event.preventDefault();
            document.querySelector('[role=status]').textContent =
              'Message sent by ' + new FormData(event.target).get('name');
          });
        </script>
    """,
    "/tasks": """
        <h1>Tasks</h1><ul aria-label="Task list"></ul>
        <script>
          fetch('/api/tasks').then(response => response.json()).then(tasks => {
            const list = document.querySelector('ul');
            for (const task of tasks) {
              const item = document.createElement('li');
              item.textContent = task.title;
              list.append(item);
            }
          });
        </script>
    """,
}


class DemoHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def send_json(self, status, body):
        self.send_body(status, json.dumps(body).encode(), "application/json")

    def send_body(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in PAGES:
            html = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Playwright Demo</title>'
            self.send_body(
                200, (html + NAV + PAGES[path] + "</html>").encode(), "text/html"
            )
        elif path == "/api/tasks":
            self.send_json(200, list(self.server.tasks.values()))
        elif path.startswith("/api/tasks/"):
            task = self.server.tasks.get(path.removeprefix("/api/tasks/"))
            (
                self.send_json(200, task)
                if task
                else self.send_json(404, {"error": "not_found"})
            )
        else:
            self.send_json(404, {"error": "not_found"})

    def do_POST(self):
        if urlsplit(self.path).path != "/api/tasks":
            self.send_json(404, {"error": "not_found"})
            return
        try:
            data = json.loads(
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
            )
        except (ValueError, UnicodeDecodeError):
            self.send_json(400, {"error": "invalid_json"})
            return
        title = data.get("title") if isinstance(data, dict) else None
        if not isinstance(title, str) or not title.strip():
            self.send_json(422, {"error": "title_required"})
            return
        task_id = str(self.server.next_id)
        self.server.next_id += 1
        task = {"id": task_id, "title": title.strip()}
        self.server.tasks[task_id] = task
        self.send_json(201, task)

    def do_DELETE(self):
        path = urlsplit(self.path).path
        task_id = (
            path.removeprefix("/api/tasks/") if path.startswith("/api/tasks/") else None
        )
        if self.server.tasks.pop(task_id, None) is None:
            self.send_json(404, {"error": "not_found"})
        else:
            self.send_body(204, b"", "application/json")


if __name__ == "__main__":
    import argparse
    from http.server import ThreadingHTTPServer

    parser = argparse.ArgumentParser(
        description="Serve the Playwright demo for CLI exploration"
    )
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), DemoHandler)
    server.tasks = {}
    server.next_id = 1
    print(f"Demo: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
