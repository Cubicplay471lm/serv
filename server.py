from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import json
import os
import time
from datetime import datetime
import uvicorn
import bcrypt

app = FastAPI(title="Karasik Talk Server", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== СТАТИКА =====
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/admin")
async def admin_page():
    return FileResponse("static/admin.html")

# ===== МОДЕЛИ =====
class Passport(BaseModel):
    fullName: str
    role: str = "Обычный карасик"
    birthDate: str = ""

class LoginRequest(BaseModel):
    login: str
    password: str

class RegisterRequest(BaseModel):
    login: str
    password: str
    fullName: str
    role: str = "Обычный карасик"
    birthDate: str = ""

class CreateChatRequest(BaseModel):
    name: str
    member: str
    from_user: str

class SendMessageRequest(BaseModel):
    text: str
    from_user: str

class AddBalanceRequest(BaseModel):
    login: str
    amount: int

class TransferRequest(BaseModel):
    from_user: str
    to: str
    amount: int

class PostRequest(BaseModel):
    text: str
    author: str

class CommentRequest(BaseModel):
    text: str
    author: str

class AnnouncementRequest(BaseModel):
    title: str
    text: str

class AdminLoginRequest(BaseModel):
    password: str

# ===== БАЗА ДАННЫХ =====
class Database:
    def __init__(self, path="karasik_data.json"):
        self.path = path
        self.data = self._load()
    
    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        # Создаём базу с хэшем админ-пароля
        admin_hash = bcrypt.hashpw("рыбнадзор".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        return {
            "users": {},
            "chats": {},
            "posts": {},
            "transactions": {},
            "announcements": {},
            "admin": {
                "password": admin_hash
            }
        }
    
    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def get_admin_password(self):
        return self.data.get("admin", {}).get("password", "")
    
    def get_user(self, login: str):
        return self.data["users"].get(login)
    
    def get_all_users(self):
        return self.data["users"]
    
    def create_user(self, login: str, user_data: dict):
        self.data["users"][login] = user_data
        self._save()
    
    def update_user(self, login: str, user_data: dict):
        self.data["users"][login] = user_data
        self._save()
    
    def delete_user(self, login: str):
        if login in self.data["users"]:
            del self.data["users"][login]
            self._save()
    
    def get_chat(self, chat_id: str):
        return self.data["chats"].get(chat_id)
    
    def get_all_chats(self):
        return self.data["chats"]
    
    def create_chat(self, chat_id: str, chat_data: dict):
        self.data["chats"][chat_id] = chat_data
        self._save()
    
    def update_chat(self, chat_id: str, chat_data: dict):
        self.data["chats"][chat_id] = chat_data
        self._save()
    
    def delete_chat(self, chat_id: str):
        if chat_id in self.data["chats"]:
            del self.data["chats"][chat_id]
            self._save()
    
    def get_posts(self):
        return self.data.get("posts", {})
    
    def create_post(self, post_id: str, post_data: dict):
        if "posts" not in self.data:
            self.data["posts"] = {}
        self.data["posts"][post_id] = post_data
        self._save()
    
    def update_post(self, post_id: str, post_data: dict):
        if "posts" in self.data:
            self.data["posts"][post_id] = post_data
            self._save()
    
    def delete_post(self, post_id: str):
        if "posts" in self.data and post_id in self.data["posts"]:
            del self.data["posts"][post_id]
            self._save()
    
    def get_transactions(self):
        return self.data.get("transactions", {})
    
    def create_transaction(self, tx_id: str, tx_data: dict):
        if "transactions" not in self.data:
            self.data["transactions"] = {}
        self.data["transactions"][tx_id] = tx_data
        self._save()
    
    def get_announcements(self):
        return self.data.get("announcements", {})
    
    def create_announcement(self, ann_id: str, ann_data: dict):
        if "announcements" not in self.data:
            self.data["announcements"] = {}
        self.data["announcements"][ann_id] = ann_data
        self._save()
    
    def delete_announcement(self, ann_id: str):
        if "announcements" in self.data and ann_id in self.data["announcements"]:
            del self.data["announcements"][ann_id]
            self._save()
    
    def clear_all(self):
        # Сохраняем админ-пароль
        admin_hash = self.data.get("admin", {}).get("password", "")
        self.data = {
            "users": {},
            "chats": {},
            "posts": {},
            "transactions": {},
            "announcements": {},
            "admin": {"password": admin_hash}
        }
        self._save()

db = Database("karasik_data.json")

# ===== ХЭШИРОВАНИЕ =====
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))

# ===== АДМИН ЛОГИН (С ХЭШОМ) =====
@app.post("/api/admin/login")
async def admin_login(data: AdminLoginRequest):
    admin_hash = db.get_admin_password()
    if not admin_hash:
        # Если нет хэша — создаём
        new_hash = hash_password("рыбнадзор")
        db.data["admin"] = {"password": new_hash}
        db._save()
        admin_hash = new_hash
    
    if verify_password(data.password, admin_hash):
        return {"status": "success", "message": "Добро пожаловать, админ!"}
    else:
        raise HTTPException(status_code=401, detail="Неверный пароль")

# ===== API =====
@app.post("/api/register")
async def api_register(data: RegisterRequest):
    if db.get_user(data.login):
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    user_data = {
        "password": hash_password(data.password),
        "passport": {"fullName": data.fullName, "role": data.role, "birthDate": data.birthDate},
        "createdAt": datetime.now().isoformat(),
        "chats": [],
        "balance": 0,
        "online": False,
        "lastSeen": 0
    }
    db.create_user(data.login, user_data)
    return {"status": "success"}

@app.post("/api/login")
async def api_login(data: LoginRequest):
    user = db.get_user(data.login)
    if not user:
        raise HTTPException(status_code=400, detail="Пользователь не найден")
    if not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=400, detail="Неверный пароль")
    user["online"] = True
    user["lastSeen"] = int(time.time() * 1000)
    db.update_user(data.login, user)
    user_response = {k: v for k, v in user.items() if k != "password"}
    user_response["login"] = data.login
    return {"status": "success", "user": user_response}

@app.get("/api/users")
async def api_get_users():
    users = db.get_all_users()
    for login in users:
        if "password" in users[login]:
            users[login]["password"] = "***"
    return {"users": users}

@app.get("/api/users/{login}")
async def api_get_user(login: str):
    user = db.get_user(login)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user_response = {k: v for k, v in user.items() if k != "password"}
    user_response["login"] = login
    return {"user": user_response}

@app.delete("/api/users/{login}")
async def api_delete_user(login: str):
    if not db.get_user(login):
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    db.delete_user(login)
    return {"status": "success"}

@app.put("/api/users/{login}/passport")
async def update_passport(login: str, passport: dict):
    user = db.get_user(login)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user["passport"] = passport
    db.update_user(login, user)
    return {"status": "success"}

@app.post("/api/admin/balance")
async def api_add_balance(data: AddBalanceRequest):
    user = db.get_user(data.login)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user["balance"] = (user.get("balance") or 0) + data.amount
    db.update_user(data.login, user)
    return {"status": "success", "new_balance": user["balance"]}

@app.post("/api/transfer")
async def api_make_transfer(data: TransferRequest):
    if data.from_user == data.to:
        raise HTTPException(status_code=400, detail="Нельзя перевести самому себе")
    sender = db.get_user(data.from_user)
    if not sender:
        raise HTTPException(status_code=404, detail="Отправитель не найден")
    receiver = db.get_user(data.to)
    if not receiver:
        raise HTTPException(status_code=404, detail="Получатель не найден")
    if (sender.get("balance") or 0) < data.amount:
        raise HTTPException(status_code=400, detail="Недостаточно средств")
    sender["balance"] = (sender.get("balance") or 0) - data.amount
    receiver["balance"] = (receiver.get("balance") or 0) + data.amount
    db.update_user(data.from_user, sender)
    db.update_user(data.to, receiver)
    tx_id = str(int(time.time() * 1000))
    tx_data = {
        "from": data.from_user,
        "to": data.to,
        "amount": data.amount,
        "timestamp": int(time.time() * 1000)
    }
    db.create_transaction(tx_id, tx_data)
    return {"status": "success", "transaction": tx_data}

@app.get("/api/transactions")
async def api_get_transactions():
    return {"transactions": db.get_transactions()}

# ===== ЧАТЫ =====
@app.post("/api/chats")
async def api_create_chat(data: CreateChatRequest):
    if not db.get_user(data.member):
        raise HTTPException(status_code=400, detail="Пользователь не найден")
    chat_id = str(int(time.time() * 1000))
    chat_data = {
        "name": data.name,
        "members": [data.from_user, data.member],
        "createdBy": data.from_user,
        "createdAt": datetime.now().isoformat(),
        "messages": {}
    }
    db.create_chat(chat_id, chat_data)
    for m in chat_data["members"]:
        user = db.get_user(m)
        if user:
            if "chats" not in user:
                user["chats"] = []
            if chat_id not in user["chats"]:
                user["chats"].append(chat_id)
            db.update_user(m, user)
    return {"status": "success", "chatId": chat_id, "chat": chat_data}

@app.get("/api/chats")
async def api_get_chats():
    return {"chats": db.get_all_chats()}

@app.get("/api/chats/{chat_id}")
async def api_get_chat(chat_id: str):
    chat = db.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    return {"chat": chat}

@app.post("/api/chats/{chat_id}/join")
async def api_join_chat(chat_id: str, login: str):
    chat = db.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    if login in chat["members"]:
        raise HTTPException(status_code=400, detail="Уже в чате")
    chat["members"].append(login)
    db.update_chat(chat_id, chat)
    user = db.get_user(login)
    if user:
        if "chats" not in user:
            user["chats"] = []
        if chat_id not in user["chats"]:
            user["chats"].append(chat_id)
        db.update_user(login, user)
    return {"status": "success"}

@app.post("/api/chats/{chat_id}/messages")
async def api_send_message(chat_id: str, data: SendMessageRequest):
    chat = db.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    msg_id = str(int(time.time() * 1000))
    message = {
        "from": data.from_user,
        "text": data.text,
        "timestamp": int(time.time() * 1000)
    }
    if "messages" not in chat:
        chat["messages"] = {}
    chat["messages"][msg_id] = message
    db.update_chat(chat_id, chat)
    return {"status": "success", "messageId": msg_id}

@app.delete("/api/chats/{chat_id}")
async def api_delete_chat(chat_id: str):
    chat = db.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    db.delete_chat(chat_id)
    return {"status": "success"}

# ===== ПОСТЫ =====
@app.post("/api/posts")
async def api_create_post(data: PostRequest):
    user = db.get_user(data.author)
    if not user or not user.get("passport"):
        raise HTTPException(status_code=403, detail="У вас нет паспорта")
    post_id = str(int(time.time() * 1000))
    post_data = {
        "author": data.author,
        "text": data.text,
        "timestamp": int(time.time() * 1000),
        "likes": 0,
        "likedBy": {},
        "comments": {}
    }
    db.create_post(post_id, post_data)
    return {"status": "success", "postId": post_id}

@app.get("/api/posts")
async def api_get_posts():
    return {"posts": db.get_posts()}

@app.put("/api/posts/{post_id}/like")
async def api_like_post(post_id: str, login: str):
    posts = db.get_posts()
    if post_id not in posts:
        raise HTTPException(status_code=404, detail="Пост не найден")
    post = posts[post_id]
    liked_by = post.get("likedBy", {})
    likes = post.get("likes", 0)
    if login in liked_by:
        del liked_by[login]
        likes -= 1
    else:
        liked_by[login] = True
        likes += 1
    post["likes"] = likes
    post["likedBy"] = liked_by
    db.update_post(post_id, post)
    return {"status": "success", "likes": likes}

@app.post("/api/posts/{post_id}/comments")
async def api_add_comment(post_id: str, data: CommentRequest):
    user = db.get_user(data.author)
    if not user or not user.get("passport"):
        raise HTTPException(status_code=403, detail="У вас нет паспорта")
    posts = db.get_posts()
    if post_id not in posts:
        raise HTTPException(status_code=404, detail="Пост не найден")
    post = posts[post_id]
    if "comments" not in post:
        post["comments"] = {}
    comment_id = str(int(time.time() * 1000))
    post["comments"][comment_id] = {
        "author": data.author,
        "text": data.text,
        "timestamp": int(time.time() * 1000)
    }
    db.update_post(post_id, post)
    return {"status": "success", "commentId": comment_id}

# ===== ОБЪЯВЛЕНИЯ =====
@app.post("/api/announcements")
async def api_create_announcement(data: AnnouncementRequest):
    ann_id = str(int(time.time() * 1000))
    ann_data = {
        "title": data.title,
        "text": data.text,
        "date": datetime.now().strftime("%d.%m.%Y"),
        "active": True
    }
    db.create_announcement(ann_id, ann_data)
    return {"status": "success", "announcementId": ann_id}

@app.get("/api/announcements")
async def api_get_announcements():
    return {"announcements": db.get_announcements()}

@app.delete("/api/announcements/{ann_id}")
async def api_delete_announcement(ann_id: str):
    db.delete_announcement(ann_id)
    return {"status": "success"}

@app.put("/api/announcements/{ann_id}/toggle")
async def api_toggle_announcement(ann_id: str):
    announcements = db.get_announcements()
    if ann_id not in announcements:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    announcements[ann_id]["active"] = not announcements[ann_id].get("active", True)
    db.create_announcement(ann_id, announcements[ann_id])
    return {"status": "success"}

@app.post("/api/admin/login")
async def admin_login(data: AdminLoginRequest):
    admin_hash = db.get_admin_password()
    if not admin_hash:
        new_hash = hash_password("рыбнадзор")
        db.data["admin"] = {"password": new_hash}
        db._save()
        admin_hash = new_hash
    
    if verify_password(data.password, admin_hash):
        return {"status": "success", "message": "Добро пожаловать, админ!"}
    else:
        raise HTTPException(status_code=401, detail="Неверный пароль")

# ===== АДМИН =====
@app.get("/api/admin/all")
async def api_get_all():
    return {
        "users": db.get_all_users(),
        "chats": db.get_all_chats(),
        "posts": db.get_posts(),
        "transactions": db.get_transactions(),
        "announcements": db.get_announcements()
    }

@app.post("/api/admin/clear")
async def api_clear_all():
    db.clear_all()
    return {"status": "success"}

if __name__ == "__main__":
    print("🐟 Karasik Talk Server запущен!")
    print("📋 Главная: http://localhost:8000")
    print("👑 Админка: http://localhost:8000/admin")
    print("🔑 Пароль админа: рыбнадзор (хэшируется в базе)")
    uvicorn.run(app, host="0.0.0.0", port=9781)