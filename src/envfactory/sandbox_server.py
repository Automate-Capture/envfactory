"""In-process Flask sandbox serving a stateful task-management API."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from flask import Flask, jsonify, request as flask_request


def _create_app() -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True

    store: dict[str, dict[str, Any]] = {"projects": {}, "tasks": {}}

    @app.route("/projects", methods=["POST"])
    def create_project():
        data = flask_request.get_json(silent=True) or {}
        pid = str(uuid.uuid4())[:8]
        project = {"id": pid, "name": data.get("name", "Untitled"), "tasks": []}
        store["projects"][pid] = project
        return jsonify(project), 201

    @app.route("/projects/<project_id>/tasks", methods=["POST"])
    def create_task(project_id: str):
        if project_id not in store["projects"]:
            return jsonify({"error": "project not found"}), 404
        data = flask_request.get_json(silent=True) or {}
        tid = str(uuid.uuid4())[:8]
        task = {
            "id": tid,
            "task_id": tid,
            "project_id": project_id,
            "title": data.get("title", "Untitled Task"),
            "status": data.get("status", "open"),
        }
        store["tasks"][tid] = task
        store["projects"][project_id]["tasks"].append(tid)
        return jsonify(task), 201

    @app.route("/projects/<project_id>/tasks", methods=["GET"])
    def list_tasks(project_id: str):
        if project_id not in store["projects"]:
            return jsonify({"error": "project not found"}), 404
        task_ids = store["projects"][project_id]["tasks"]
        tasks = [store["tasks"][tid] for tid in task_ids if tid in store["tasks"]]
        return jsonify(tasks), 200

    @app.route("/tasks/<task_id>", methods=["GET"])
    def get_task(task_id: str):
        if task_id not in store["tasks"]:
            return jsonify({"error": "task not found"}), 404
        return jsonify(store["tasks"][task_id]), 200

    @app.route("/tasks/<task_id>", methods=["DELETE"])
    def delete_task(task_id: str):
        if task_id not in store["tasks"]:
            return jsonify({"error": "task not found"}), 404
        task = store["tasks"].pop(task_id)
        pid = task.get("project_id")
        if pid and pid in store["projects"]:
            tasks_list = store["projects"][pid]["tasks"]
            if task_id in tasks_list:
                tasks_list.remove(task_id)
        return jsonify({"deleted": True, "id": task_id}), 200

    return app


class SandboxServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self._host = host
        self._port = port
        self._app = _create_app()
        self._thread: threading.Thread | None = None
        self._server: Any = None
        self._actual_port: int | None = None

    def start(self) -> str:
        from werkzeug.serving import make_server
        self._server = make_server(self._host, self._port, self._app)
        self._actual_port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        time.sleep(0.1)
        return f"http://{self._host}:{self._actual_port}"

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server = None
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
