from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from functools import wraps
import datetime

app = Flask(__name__)
CORS(app)

# Demo data (in-memory for now)
users = [
    {"id": 1, "name": "Admin User", "email": "admin@quickdesk.com", "role": "Admin", "password": "Admin@123", "last_active": "2025-08-01 10:00"},
    {"id": 2, "name": "Support Agent", "email": "agent@quickdesk.com", "role": "Agent", "password": "Agent@123", "last_active": "2025-08-01 09:30"},
    {"id": 3, "name": "Regular User", "email": "user@quickdesk.com", "role": "User", "password": "User@123", "last_active": "2025-08-01 08:45"},
]

tickets = [
    {"id": 101, "title": "Cannot login to portal", "status": "Open", "priority": "High", "created": "2025-08-01", "createdBy": "Regular User", "description": "User is unable to login to the portal. Error message: 'Invalid credentials'.", "timeline": [
        {"event": "Created", "time": "2025-08-01 09:00"},
        {"event": "Assigned to Support Agent", "time": "2025-08-01 09:10"},
        {"event": "Status changed to Open", "time": "2025-08-01 09:12"},
    ], "comments": [
        {"user": "Support Agent", "text": "I am looking into this.", "time": "2025-08-01 09:15"},
        {"user": "Admin User", "text": "Please provide a screenshot.", "time": "2025-08-01 09:16"},
    ], "attachments": [
        {"name": "screenshot1.png", "url": "#"},
        {"name": "error_log.txt", "url": "#"},
    ]},
    {"id": 102, "title": "Feature request: Dark mode", "status": "Pending", "priority": "Low", "created": "2025-07-30", "createdBy": "Regular User", "description": "User requests a dark mode option.", "timeline": [], "comments": [], "attachments": []},
    {"id": 103, "title": "Bug: Email notifications not sent", "status": "Closed", "priority": "Medium", "created": "2025-07-29", "createdBy": "Regular User", "description": "Email notifications are not being sent.", "timeline": [], "comments": [], "attachments": []},
    {"id": 104, "title": "Unable to reset password", "status": "Open", "priority": "High", "created": "2025-07-28", "createdBy": "Regular User", "description": "Password reset link not working.", "timeline": [], "comments": [], "attachments": []},
    {"id": 105, "title": "UI glitch on dashboard", "status": "Pending", "priority": "Low", "created": "2025-07-27", "createdBy": "Regular User", "description": "Dashboard UI glitch on mobile.", "timeline": [], "comments": [], "attachments": []},
]

logs = [
    {"message": "User Admin User logged in", "level": "info", "timestamp": "2025-08-01 10:00:00"},
    {"message": "Ticket #101 created by Regular User", "level": "info", "timestamp": "2025-08-01 09:00:00"},
    {"message": "Ticket #101 assigned to Support Agent", "level": "info", "timestamp": "2025-08-01 09:10:00"},
    {"message": "Warning: High CPU usage detected", "level": "warning", "timestamp": "2025-08-01 08:30:00"},
    {"message": "New user registered: Test User", "level": "info", "timestamp": "2025-07-31 14:15:00"},
    {"message": "Error: Database connection failed", "level": "error", "timestamp": "2025-07-31 13:45:00"},
]

# Authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = request.headers.get('Authorization')
        if not auth or auth != 'Bearer AdminToken':
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

# Helper function to get current timestamp
def current_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Users API
@app.route("/api/users", methods=["GET"])
@admin_required
def get_users():
    # Pagination parameters
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    
    # Filtering
    search = request.args.get('search', '').lower()
    filtered_users = [u for u in users if search in u['name'].lower() or search in u['email'].lower()]
    
    # Pagination
    start = (page - 1) * per_page
    end = start + per_page
    paginated_users = filtered_users[start:end]
    
    return jsonify({
        "data": paginated_users,
        "total": len(filtered_users),
        "page": page,
        "per_page": per_page,
        "total_pages": (len(filtered_users) + per_page - 1) // per_page
    })

@app.route("/api/users", methods=["POST"])
@admin_required
def add_user():
    data = request.json
    if not data.get('name') or not data.get('email') or not data.get('role'):
        return jsonify({"error": "Missing required fields"}), 400
    
    # Check if email already exists
    if any(u['email'] == data['email'] for u in users):
        return jsonify({"error": "Email already exists"}), 400
    
    new_id = max(u["id"] for u in users) + 1 if users else 1
    user = {
        "id": new_id,
        "name": data["name"],
        "email": data["email"],
        "role": data["role"],
        "password": data.get("password", "defaultPassword"),
        "last_active": current_timestamp()
    }
    users.append(user)
    
    # Add to logs
    logs.append({
        "message": f"New user created: {user['name']} ({user['email']})",
        "level": "info",
        "timestamp": current_timestamp()
    })
    
    return jsonify(user), 201

@app.route("/api/users/<int:user_id>", methods=["PUT"])
@admin_required
def edit_user(user_id):
    data = request.json
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Check if email is being changed to an existing one
    if 'email' in data and data['email'] != user['email']:
        if any(u['email'] == data['email'] for u in users):
            return jsonify({"error": "Email already exists"}), 400
    
    user.update({k: v for k, v in data.items() if k in user})
    user['last_active'] = current_timestamp()
    
    logs.append({
        "message": f"User updated: {user['name']} ({user['email']})",
        "level": "info",
        "timestamp": current_timestamp()
    })
    
    return jsonify(user)

@app.route("/api/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    global users
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    users = [u for u in users if u["id"] != user_id]
    
    logs.append({
        "message": f"User deleted: {user['name']} ({user['email']})",
        "level": "warning",
        "timestamp": current_timestamp()
    })
    
    return '', 204

@app.route("/api/users/bulk-delete", methods=["POST"])
@admin_required
def bulk_delete_users():
    data = request.json
    if not data or not isinstance(data.get('ids'), list):
        return jsonify({"error": "Invalid request"}), 400
    
    global users
    deleted_users = [u for u in users if u["id"] in data['ids']]
    users = [u for u in users if u["id"] not in data['ids']]
    
    for user in deleted_users:
        logs.append({
            "message": f"User deleted (bulk): {user['name']} ({user['email']})",
            "level": "warning",
            "timestamp": current_timestamp()
        })
    
    return jsonify({"deleted": len(deleted_users)}), 200

# Tickets API
@app.route("/api/tickets", methods=["GET"])
@admin_required
def get_tickets():
    # Pagination parameters
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    
    # Filtering
    search = request.args.get('search', '').lower()
    status_filter = request.args.get('status', '').lower()
    
    filtered_tickets = [
        t for t in tickets 
        if (search in t['title'].lower() or 
            (t.get('description') and search in t['description'].lower())) and
           (not status_filter or t['status'].lower() == status_filter)
    ]
    
    # Pagination
    start = (page - 1) * per_page
    end = start + per_page
    paginated_tickets = filtered_tickets[start:end]
    
    return jsonify({
        "data": paginated_tickets,
        "total": len(filtered_tickets),
        "page": page,
        "per_page": per_page,
        "total_pages": (len(filtered_tickets) + per_page - 1) // per_page
    })

@app.route("/api/tickets/<int:ticket_id>", methods=["GET"])
@admin_required
def get_ticket(ticket_id):
    ticket = next((t for t in tickets if t["id"] == ticket_id), None)
    if ticket:
        return jsonify(ticket)
    return jsonify({"error": "Ticket not found"}), 404

@app.route("/api/tickets/<int:ticket_id>", methods=["PUT"])
@admin_required
def edit_ticket(ticket_id):
    data = request.json
    ticket = next((t for t in tickets if t["id"] == ticket_id), None)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404
    
    ticket.update({k: v for k, v in data.items() if k in ticket})
    
    logs.append({
        "message": f"Ticket updated: #{ticket['id']} {ticket['title']}",
        "level": "info",
        "timestamp": current_timestamp()
    })
    
    return jsonify(ticket)

@app.route("/api/tickets/<int:ticket_id>", methods=["DELETE"])
@admin_required
def delete_ticket(ticket_id):
    global tickets
    ticket = next((t for t in tickets if t["id"] == ticket_id), None)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404
    
    tickets = [t for t in tickets if t["id"] != ticket_id]
    
    logs.append({
        "message": f"Ticket deleted: #{ticket['id']} {ticket['title']}",
        "level": "warning",
        "timestamp": current_timestamp()
    })
    
    return '', 204

# Logs API
@app.route("/api/logs", methods=["GET"])
@admin_required
def get_logs():
    # Filtering
    level_filter = request.args.get('level', '').lower()
    filtered_logs = [l for l in logs if not level_filter or l['level'] == level_filter]
    
    # Limit to last 100 logs
    limited_logs = filtered_logs[-100:]
    
    return jsonify(limited_logs)

@app.route("/api/logs", methods=["DELETE"])
@admin_required
def clear_logs():
    global logs
    logs = []
    return '', 204

# Stats API
@app.route("/api/stats", methods=["GET"])
@admin_required
def get_stats():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    return jsonify({
        "total_users": len(users),
        "active_tickets": len([t for t in tickets if t['status'] in ['Open', 'Pending']]),
        "new_tickets_today": len([t for t in tickets if t['created'] == today]),
        "avg_response_time": "2h 15m"
    })

if __name__ == "__main__":
    app.run(debug=True)